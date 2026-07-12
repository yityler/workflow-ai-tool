

import os
import re
import tempfile
import time

import litellm
from pydantic import BaseModel

from .input.input_ui import build_ui
from .input.input_build_prompt import build_prompt
from .input.input_rag import analyze_files
from .Tyler_Yi_Prototype_Folder import token_optimizer as topt
from .product_generation.concept import generate_concept
from .product_generation.image_gen_hf import generate_image as generate_image_hf
from .product_generation.cornerstone_page_generator import (
    get_template,
    export_cornerstone_layout,
    attach_product_image,
)
from .product_generation.cornerstone_renderer import write_preview
from .product_generation.preview_server import ensure_server

litellm.suppress_debug_info = True
litellm.drop_params = True

PREVIEW_DIR = os.path.join(tempfile.gettempdir(), "cornerstone_preview")

# One session-wide savings tracker + response cache, shared across every
# generate/edit call so the report shows cumulative savings.
TRACKER = topt.SavingsTracker()
CONCEPT_CACHE = topt.ResponseCache(threshold=0.94)


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
# Component routing for free-text change requests (no LLM spent on this)
# ============================================================

def pick_target_component(template, instruction):
    """Cheap keyword-overlap routing: picks the single component most likely
    referenced by the user's change request, so edit_component() only ever
    sends ONE component's JSON to the model instead of the whole page."""
    tokens = set(re.findall(r"[a-z0-9']+", (instruction or "").lower()))
    best_id, best_score = None, -1
    for c in template.components:
        haystack = f"{c.type} {c.id} {c.heading} {c.body}"
        htoks = set(re.findall(r"[a-z0-9']+", haystack.lower()))
        score = len(tokens & htoks)
        if c.type in tokens:
            score += 5
        if score > best_score:
            best_score, best_id = score, c.id
    return best_id


# ============================================================
# Preview link helper
# ============================================================

def _build_preview_link(template):
    path = write_preview(template, PREVIEW_DIR)
    base_url = ensure_server(PREVIEW_DIR)
    filename = os.path.basename(path)
    url = f"{base_url}/{filename}?t={int(time.time())}"
    return f'<a href="{url}" target="_blank" rel="noopener">Open live preview in browser ↗</a>'


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
        decision = check_image_needed(
            product_description=product_description,
            industry=industry,
            key_features=concept.get("key_features"),
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
        )
    except Exception as e:
        return prompt, "", "", f"Layout generation failed: {e}", None

    if cached:
        TRACKER.add("layout template cache", topt.count_tokens(template.model_dump_json()))

    if image_path:
        layout_json = attach_product_image(export_cornerstone_layout(template), image_path)
        # keep the in-memory template consistent with the JSON we just returned,
        # so a later "request changes" edit starts from the same state
        for c in template.components:
            if c.type == "product_visual":
                c.content = {**(c.content or {}), "image": image_path}
    else:
        layout_json = export_cornerstone_layout(template)

    preview_link_html = _build_preview_link(template)

    report_lines = [
        f"**Image decision:** {'generated' if (image_path and decision.needs_image) else ('reused upload' if image_path else 'skipped')} — {decision.reason}",
        f"**Layout template:** {'cache hit (0 tokens)' if cached else 'new AI generation'}",
        f"**RAG:** {len(uploaded_product_images)} product image(s), "
        f"{'text context found' if reference_notes else 'no text context found'} in uploaded files.",
        "",
        "**Session token savings (token_optimizer):**",
        TRACKER.report(),
    ]
    return prompt, layout_json, preview_link_html, "\n\n".join(report_lines), template


# ============================================================
# "Tell the AI about changes" — diff-based edit on the live template
# ============================================================

def apply_change_request(instruction, template):
    """
    Called by the "Apply Changes" button. Routes the free-text instruction to
    the single most relevant component (no LLM call spent on routing) and
    sends ONLY that component to the cheap edit model — the diff-edit pattern
    from cornerstone_layout_generator.py / page_generator.py, which is the
    single biggest per-edit token saving in this project.
    """
    if template is None:
        return "", "", "Generate a page first, then request changes to it.", None

    if not instruction or not instruction.strip():
        return (
            export_cornerstone_layout(template),
            _build_preview_link(template),
            "Enter a change request first.",
            template,
        )

    mistral_key = os.environ.get("MISTRAL_API_KEY", "")
    if not mistral_key:
        return (
            export_cornerstone_layout(template),
            _build_preview_link(template),
            "Missing MISTRAL_API_KEY — cannot apply the edit.",
            template,
        )

    target_id = pick_target_component(template, instruction)

    whole_tokens = topt.count_tokens(template.model_dump_json())
    try:
        updated = edit_component(template, target_id, instruction, mistral_key)
    except Exception as e:
        return (
            export_cornerstone_layout(template),
            _build_preview_link(template),
            f"Edit failed: {e}",
            template,
        )

    edited_component = next(c for c in updated.components if c.id == target_id)
    sent_tokens = topt.count_tokens(edited_component.model_dump_json())
    TRACKER.add("diff edits", max(whole_tokens - sent_tokens, 0))

    layout_json = export_cornerstone_layout(updated)
    preview_link_html = _build_preview_link(updated)

    report = (
        f"Applied your change to the **`{target_id}`** component only "
        f"(diff edit — sent {sent_tokens} tokens instead of the whole "
        f"{whole_tokens}-token page).\n\n"
        "**Session token savings (token_optimizer):**\n" + TRACKER.report()
    )
    return layout_json, preview_link_html, report, updated


if __name__ == "__main__":
    app = build_ui(
        generate_fn=generate_product_page,
        apply_change_fn=apply_change_request,
    )
    app.launch()
