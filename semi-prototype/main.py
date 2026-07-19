

import json
import os
import tempfile
import time
import uuid

import litellm
from pydantic import BaseModel

from .input.input_ui import build_ui, REORDER_BRIDGE_HEAD
from .input.input_build_prompt import build_prompt
from .input.input_rag import analyze_files
from .Tyler_Yi_Prototype_Folder import token_optimizer as topt
from .product_generation.concept import generate_concept
from .product_generation.image_gen_hf import generate_image as generate_image_hf
from .product_generation.cornerstone_page_generator import (
    get_template,
    export_cornerstone_layout,
)
from .product_generation.cornerstone_renderer import write_preview
from .product_generation.preview_server import ensure_server

litellm.suppress_debug_info = True
litellm.drop_params = True

PREVIEW_DIR = os.path.join(tempfile.gettempdir(), "cornerstone_preview")

TRACKER = topt.SavingsTracker()
CONCEPT_CACHE = topt.ResponseCache(threshold=0.94)


class Page:
    def __init__(self, template, page_id=None):
        self.template = template
        self.page_id = page_id or uuid.uuid4().hex[:12]


# ============================================================
# SLM check: does this page actually need a *generated* image?
# ============================================================

# Cheap/small model — same tier already used for lightweight edits elsewhere
# in the project (see cornerstone_layout_generator.MODELS["edit"]).
IMAGE_CHECK_MODEL = "mistral/ministral-8b-latest"


class ImageNeedDecision(BaseModel):
    needs_image: bool
    reason: str


def check_image_needed(product_description, industry, key_features=None):
    key = os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        return ImageNeedDecision(
            needs_image=True,
            reason="No MISTRAL_API_KEY configured; defaulting to image generation.",
        )

    import instructor

    client = instructor.from_litellm(litellm.completion)

    prompt = f"""
You are deciding whether a product page pipeline should spend time generating a
NEW hero/product image for this page, or whether that step is unnecessary.

Product description:
{product_description}

Industry: {industry or "unspecified"}
Key features: {", ".join(key_features) if key_features else "unspecified"}

Most physical/visual products benefit from one clear hero image. Only answer
that an image is NOT needed if the product is abstract or non-visual (e.g. a
pure software service, a subscription, a consulting offering) where a
generated image would add little value.

{topt.CONCISE_INSTRUCTION}
"""

    decision = client.chat.completions.create(
        response_model=ImageNeedDecision,
        messages=[{"role": "user", "content": prompt}],
        model=IMAGE_CHECK_MODEL,
        api_key=key,
        max_retries=2,
        max_tokens=150,  # output side is the expensive side — cap it
    )
    return decision


# ============================================================
# Cached, token-optimized concept generation
# ============================================================

def cached_generate_concept(product_description):
    """Wraps concept.generate_concept() with the token_optimizer's
    exact+semantic ResponseCache: identical (or near-identical) product
    descriptions skip the Gemini call entirely."""
    normalized = topt.normalize(product_description)
    before_tokens = topt.count_tokens(product_description)

    TRACKER.calls += 1
    cached, kind = CONCEPT_CACHE.get(normalized)
    if cached is not None:
        TRACKER.cache_hits += 1
        TRACKER.add("concept cache (" + kind + ")", cached["in_tok"] + cached["out_tok"])
        import json
        return json.loads(cached["answer"])

    concept = generate_concept(normalized)
    usage = concept.get("_token_usage", {})
    import json
    CONCEPT_CACHE.put(
        normalized,
        json.dumps(concept),
        in_tok=usage.get("prompt_tokens", before_tokens),
        out_tok=usage.get("response_tokens", 0),
    )
    return concept


# ============================================================
# Preview link helper
# ============================================================

def _build_preview_link(template, page_id):
    path = write_preview(template, PREVIEW_DIR, filename=f"page_{page_id}.html", page_id=page_id)
    base_url = ensure_server(PREVIEW_DIR)
    filename = os.path.basename(path)
    url = f"{base_url}/{filename}?t={int(time.time())}"
    return (
        f'<a href="{url}" target="_blank" rel="noopener">Open live preview in browser ↗</a>'
        f'<iframe src="{url}" title="Live preview" '
        f'style="width:100%;height:640px;border:1px solid #ddd;border-radius:8px;margin-top:10px;"></iframe>'
    )


def _layout_instructions(layout_style, spacing, tone, color_scheme):
    parts = []
    if layout_style:
        parts.append(f"Layout style: {layout_style}.")
    if spacing:
        parts.append(f"Spacing: {spacing}.")
    if tone:
        parts.append(f"Copy tone: {tone}.")
    if color_scheme:
        parts.append(f"Color scheme preference: {color_scheme}.")
    return " ".join(parts)


def _build_image_inventory(product_rag, theme_rag):
    """Combines the images pulled out of both RAG passes (product docs +
    brand/theme docs) into one captioned inventory the layout model can pick
    from via `image_ref`, instead of the pipeline only ever being able to
    hardcode a single hero image."""
    images = []
    for i, path in enumerate(product_rag["image_paths"], start=1):
        images.append({
            "id": f"product_image_{i}",
            "path": path,
            "caption": product_rag["image_captions"].get(path, ""),
            "source": "product upload",
        })
    for i, path in enumerate(theme_rag["image_paths"], start=1):
        images.append({
            "id": f"theme_image_{i}",
            "path": path,
            "caption": theme_rag["image_captions"].get(path, ""),
            "source": "brand/theme upload",
        })
    return images


def generate_product_page(
    product_description,
    industry,
    target_audience,
    page_theme,
    layout_style,
    spacing,
    tone,
    color_scheme,
    extra_notes,
    product_files,
    theme_files,
):
    """
    The single function the Gradio UI calls (wired in via build_ui(generate_fn=...)).
    Returns (prompt_preview, layout_json, preview_link_html, report, template)
    to fill the UI panes and the change-request state.
    """

    # 1. Human-readable prompt, mostly for the preview pane / logging.
    prompt, err = build_prompt(
        product_description=product_description,
        industry=industry,
        target_audience=target_audience,
        page_theme=page_theme,
        layout_style=layout_style,
        spacing=spacing,
        tone=tone,
        color_scheme=color_scheme,
        extra_notes=extra_notes,
        product_files=product_files,
        theme_files=theme_files,
    )
    if err:
        return f"error: {err}", "", "", "", None

    # 2. RAG over uploaded docs/images — text context (BM25 + token_optimizer
    #    chunk filtering) and vision captions for any uploaded images.
    product_rag = analyze_files(product_description, product_files)
    style_query = f"{page_theme} {tone} {color_scheme}"
    theme_rag = analyze_files(style_query, theme_files)

    reference_notes = "\n\n".join(
        filter(None, [product_rag["text_context"], theme_rag["text_context"]])
    )
    if reference_notes:
        TRACKER.add("RAG chunk filtering", product_rag["tokens"] + theme_rag["tokens"])

    uploaded_product_images = product_rag["image_paths"]
    available_images = _build_image_inventory(product_rag, theme_rag)

    # 3. Structured product concept (Gemini), cached via token_optimizer's
    #    ResponseCache so repeat/similar descriptions skip the LLM call.
    try:
        concept = cached_generate_concept(product_description)
    except Exception as e:
        return prompt, "", "", f"Concept generation failed: {e}", None

    concept.pop("_token_usage", None)
    concept.pop("image_prompt", None)

    # 4. SLM check: do we actually need to generate an image, or does the
    #    user's own upload already cover it?
    if uploaded_product_images:
        decision = ImageNeedDecision(
            needs_image=False,
            reason=(
                f"User already supplied {len(uploaded_product_images)} product image(s); "
                "reusing the first one instead of generating a new one."
            ),
        )
    else:
        try:
            decision = check_image_needed(
                product_description=product_description,
                industry=industry,
                key_features=concept.get("key_features"),
            )
        except Exception as e:
            decision = ImageNeedDecision(
                needs_image=True,
                reason=f"Image-need check failed ({e}); defaulting to image generation.",
            )

    image_path = None
    if decision.needs_image:
        try:
            image_path = generate_image_hf(
                product_description=product_description,
                industry=industry,
                target_audience=target_audience,
                page_theme=page_theme,
                layout_style=layout_style,
                spacing=spacing,
                tone=tone,
                color_scheme=color_scheme,
                extra_notes=extra_notes,
                product_files=product_files,
                theme_files=theme_files,
            )
        except Exception as e:
            image_path = None
            decision.reason += f" (image generation attempted but failed: {e})"
    elif uploaded_product_images:
        image_path = uploaded_product_images[0]

    # 5. Cornerstone layout JSON — same generator/schema used elsewhere in the
    #    project, now RAG-aware via reference_notes.
    mistral_key = os.environ.get("MISTRAL_API_KEY", "")
    if not mistral_key:
        return prompt, "", "", "Missing MISTRAL_API_KEY — cannot generate the page layout.", None

    product = {
        "name": concept.get("product_name", "Untitled Product"),
        "description": concept.get("core_concept", product_description),
        "category": concept.get("category", industry or ""),
        "features": concept.get("key_features", []),
    }
    layout_instr = _layout_instructions(layout_style, spacing, tone, color_scheme)

    try:
        template, cached = get_template(
            product=product,
            brand=concept.get("product_name", "Untitled Product"),
            brand_color="#2563EB",
            key=mistral_key,
            layout_instructions=layout_instr,
            reference_notes=reference_notes,
            available_images=available_images,
        )
    except Exception as e:
        return prompt, "", "", f"Layout generation failed: {e}", None

    if cached:
        TRACKER.add("layout template cache", topt.count_tokens(template.model_dump_json()))

    # The model may already have assigned one of the RAG images to the
    # product_visual component(s) via `image_ref` (resolved inside
    # get_template). Only fall back to the generated/uploaded hero image for
    # product_visual components that don't already have one, so we never
    # clobber a deliberate RAG image choice.
    images_used = sum(1 for c in template.components if (c.content or {}).get("image"))
    if image_path:
        for c in template.components:
            if c.type == "product_visual" and not (c.content or {}).get("image"):
                c.content = {**(c.content or {}), "image": image_path}
                images_used += 1
    layout_json = export_cornerstone_layout(template)

    page = Page(template)
    preview_link_html = _build_preview_link(template, page.page_id)

    report_lines = [
        f"**Image decision:** {'generated' if (image_path and decision.needs_image) else ('reused upload' if image_path else 'skipped')} — {decision.reason}",
        f"**Layout template:** {'cache hit (0 tokens)' if cached else 'new AI generation'}",
        f"**RAG:** {len(available_images)} reference image(s) available "
        f"({len(uploaded_product_images)} product, {len(available_images) - len(uploaded_product_images)} brand/theme); "
        f"{images_used} used on the page. "
        f"{'Text context found' if reference_notes else 'No text context found'} in uploaded files.",
        "",
        "**Session token savings (token_optimizer):**",
        TRACKER.report(),
    ]
    return prompt, layout_json, preview_link_html, "\n\n".join(report_lines), page


# ============================================================
# "Tell the AI about changes" — diff-based edit on the live template
# ============================================================

def apply_reorder(order_json, page):
    """
    Called whenever the user drags a section in the Live Preview to a new
    spot. `order_json` is a JSON-encoded list of component ids in their new
    order (produced client-side by the drag-and-drop script embedded in the
    rendered preview — see cornerstone_renderer.py). This just rewrites
    template.components to match; no LLM call, no tokens spent.
    """
    if page is None:
        return "", "", "Generate a page first, then drag its sections to reorder them.", None

    template = page.template

    try:
        new_order = json.loads(order_json) if order_json else []
    except (TypeError, ValueError):
        new_order = []

    if not new_order:
        return (
            export_cornerstone_layout(template),
            _build_preview_link(template, page.page_id),
            "No reorder detected.",
            page,
        )

    by_id = {c.id: c for c in template.components}
    reordered = [by_id[cid] for cid in new_order if cid in by_id]
    # Anything not present in new_order (e.g. a stale id from an older
    # render) is kept, appended in its original order, so a section can
    # never silently vanish from the page because of a drag event.
    seen = set(new_order)
    reordered += [c for c in template.components if c.id not in seen]
    template.components = reordered

    updated_page = Page(template, page_id=page.page_id)

    layout_json = export_cornerstone_layout(template)
    preview_link_html = _build_preview_link(template, updated_page.page_id)
    report = "Reordered sections via drag-and-drop: " + " → ".join(
        c.id for c in template.components
    )
    return layout_json, preview_link_html, report, updated_page


if __name__ == "__main__":
    app = build_ui(
        generate_fn=generate_product_page,
        reorder_fn=apply_reorder,
    )
    app.launch(head=REORDER_BRIDGE_HEAD)
