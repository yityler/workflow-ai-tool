"""
page_generator.py — B2B storefront generator prototype (token-optimized).

The product: an enterprise (e.g. a retailer using Smart Stickies RFID) uploads its catalog
and brand; the AI generates its in-store screens — product pages and the self-checkout page.

THE COST PROBLEM this file solves:
A naive build asks the LLM to write one full HTML page PER PRODUCT. A real retailer has
thousands of SKUs, so that's thousands of calls, each with ~1,500+ output tokens. This
prototype shows the optimized architecture instead:

  1. TEMPLATE-ONCE   — the LLM designs ONE page template (a compact JSON spec, not HTML).
                       Every product page is then rendered by plain Python: zero tokens each.
  2. STRUCTURED SPEC — the LLM returns a small validated JSON layout (Instructor/Pydantic),
                       ~5-10x fewer output tokens than full HTML, and machine-checkable.
  3. CATALOG SLICING — when the LLM needs product context, send only the fields required,
                       never the whole catalog.
  4. DIFF EDITS      — "make the header bolder" sends ONLY that section's JSON, not the page.
  5. TEMPLATE CACHE  — same brand + page type = reuse the saved template. Zero tokens.
  6. MODEL ROUTING   — small edits go to the cheapest model; full designs to the strongest.

Run:  python page_generator.py   → http://127.0.0.1:7861
"""

import json
import os
import time
import hashlib

import gradio as gr
import litellm
from pydantic import BaseModel

import token_optimizer as topt

litellm.suppress_debug_info = True
litellm.drop_params = True

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(HERE, "templates")
os.makedirs(TEMPLATE_DIR, exist_ok=True)

TRACKER = topt.SavingsTracker()

# What a naive per-product HTML generation would roughly cost (used for the savings math).
NAIVE_IN_PER_PAGE, NAIVE_OUT_PER_PAGE = 300, 1500


# ============================================================================
# Catalog
# ============================================================================
def load_catalog():
    with open(os.path.join(HERE, "catalog.json"), encoding="utf-8") as f:
        return json.load(f)


# Pre-made sample catalogs (option 1) + AI-generated catalogs (option 2).
# One bundled sample as a zero-token fallback/demo; the primary path is the
# AI-generated catalog invented from the business description.
CATALOG_FILES = {
    "Stationery sample": "catalog.json",
}
AI_CATALOG_CHOICE = "AI-generated for this brand"
CATALOG_DIR = os.path.join(HERE, "catalogs")
os.makedirs(CATALOG_DIR, exist_ok=True)


class Product(BaseModel):
    sku: str
    name: str
    category: str
    price: float
    description: str


class GeneratedCatalog(BaseModel):
    products: list[Product]

    def model_post_init(self, _):
        if not 6 <= len(self.products) <= 14:
            raise ValueError("return between 6 and 14 products")
        if any(p.price <= 0 for p in self.products):
            raise ValueError("all prices must be positive")


def generate_catalog(brand, key, description=""):
    """The AI invents a catalog that FITS this business (from its description, or the
    brand name if none). Structured + validated + disk-cached per brand+description."""
    sig = (brand.lower() + "|" + (description or "")[:200]).encode()
    path = os.path.join(CATALOG_DIR, hashlib.md5(sig).hexdigest()[:10] + ".json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f), 0, 0, True
    what = (f"What they sell: {description.strip()}" if (description or "").strip()
            else "Infer what this business sells from its name.")
    prompt = (f"Invent a realistic product catalog for '{brand}', a retail store using Smart "
              f"Stickies RFID instant checkout. {what} "
              "Return 10 products across 3-5 categories: short specific product names, one-line "
              "factual descriptions (plain and concrete, no marketing fluff), realistic prices "
              "in Singapore dollars, and unique SKUs like XX-001.")
    cat, in_tok, out_tok = _call_structured("design", key, prompt, GeneratedCatalog)
    data = {"enterprise": brand, "currency": "SGD", "gst_rate": 0.09,
            "products": [p.model_dump() for p in cat.products]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data, in_tok, out_tok, False


def resolve_catalog(choice, brand, key, description=""):
    """Returns (catalog_dict, cache_tag, in_tokens, out_tokens, report_note)."""
    if choice == AI_CATALOG_CHOICE:
        data, i, o, cached = generate_catalog(brand, key, description)
        note = ("- AI catalog: cache hit — 0 tokens" if cached
                else f"- AI catalog: {i}+{o} tokens (one-time, then cached)")
        return data, "ai", i, o, note
    fname = CATALOG_FILES.get(choice, "catalog.json")
    with open(os.path.join(HERE, fname), encoding="utf-8") as f:
        return json.load(f), fname, 0, 0, f"- Catalog: {choice} (file, 0 tokens)"


# ============================================================================
# Design-knowledge RAG: the "how to design well" content lives in a curated
# knowledge base (design_knowledge.txt, sourced from human designers — Rams,
# Vignelli, Robin Williams, Itten, Baymard research). At design time we retrieve
# only the chunks relevant to the page being built; the prompt itself carries
# only company-specific information. This is both better design AND fewer
# tokens than stuffing all design guidance into every prompt.
# ============================================================================
import re as _re

LAST_RETRIEVAL = {}  # info about the most recent knowledge retrieval (for the report)

_DESIGN_QUERIES = {
    "home": ("storefront browsing layout visual hierarchy focal point whitespace grid "
             "rhythm asymmetry memorable specificity avoid generic ai copy voice typeface font personality scan front-load kiosk"),
    "product": ("product page layout visual hierarchy focal point price call to action "
                "specificity voice copy human writing scan front-load typeface font personality typography kiosk"),
    "checkout": ("checkout payment trust order summary total call to action reassurance "
                 "color psychology specificity voice copy writing happy talk typeface font trust kiosk simplicity"),
}

_PAGE_DESCRIPTIONS = {
    "home": "the storefront home screen, where customers browse the product range",
    "product": "a product detail screen, where a customer inspects one item",
    "checkout": "the self-checkout payment screen, the final and most trust-sensitive moment",
}


def _design_chunks():
    with open(os.path.join(HERE, "design_knowledge.txt"), encoding="utf-8") as f:
        text = f.read()
    # One chunk per TOPIC block.
    blocks = [b.strip() for b in _re.split(r"\n\s*\n", text) if b.strip().startswith("TOPIC:")]
    return blocks


def retrieve_design_knowledge(page_type, k=7):
    """BM25-retrieve the k most relevant design-knowledge chunks for this page type."""
    from rank_bm25 import BM25Okapi
    chunks = _design_chunks()
    tok = lambda s: _re.findall(r"[a-z0-9']+", s.lower())
    bm = BM25Okapi([tok(c) for c in chunks])
    query = _DESIGN_QUERIES.get(page_type, _DESIGN_QUERIES["product"])
    scores = bm.get_scores(tok(query))
    order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)[:k]
    picked = [chunks[i] for i in order]
    LAST_RETRIEVAL[page_type] = {
        "used": len(picked), "total": len(chunks),
        "tokens": topt.count_tokens("\n\n".join(picked)),
        "total_tokens": topt.count_tokens("\n\n".join(chunks)),
    }
    return picked


def slice_catalog(products, fields=("name", "price", "category")):
    """OPTIMIZATION 3: send only the fields a task needs, never full records."""
    return [{k: p[k] for k in fields if k in p} for p in products]


# ============================================================================
# Layout spec (structured output — OPTIMIZATION 2)
# ============================================================================
# The `type` field is a closed vocabulary (Literal): the model CANNOT return a section
# the renderer doesn't understand — schema-constrained, no prose-begging needed.
# The model makes bounded DESIGN decisions (theme, microcopy, order); the renderer owns
# the CSS, built on researched rules (8-pt grid, 3-size type scale, 60-30-10 color).
from typing import Literal

SectionType = Literal["hero", "product_grid", "product_details", "price", "cta", "promo",
                      "info", "footer"]

# Palette derivation from the single brand color (HSL tonal-scale method):
# keep the brand HUE, move lightness + saturation to build tints (backgrounds) and
# shades (text). Even the "greys" carry a whisper of the brand hue — hue-tinted
# neutrals are what make a page feel art-directed instead of assembled.
# The model's theme choice shifts the neutral mood: warm leans the neutrals toward
# stone, cool toward slate, light stays on the brand hue itself.
import colorsys


def _hsl_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"


def make_theme(brand_hex, mood="light"):
    """Derive the full neutral palette from the one brand color."""
    hx = brand_hex.lstrip("#")
    try:
        r, g, b = int(hx[0:2], 16) / 255, int(hx[2:4], 16) / 255, int(hx[4:6], 16) / 255
        h, l, s = colorsys.rgb_to_hls(r, g, b)
    except (ValueError, IndexError):
        h, l, s = 0.6, 0.4, 0.4  # fallback: slate blue
    # Mood shifts the neutral hue halfway toward warm stone (45°) or cool slate (215°).
    if mood == "warm":
        h = (h + ((45 / 360) - h) * 0.5) % 1.0
    elif mood == "cool":
        h = (h + ((215 / 360) - h) * 0.5) % 1.0
    s = min(s, 0.45)  # cap so neutrals stay neutral
    return {
        "bg":      _hsl_hex(h, s * 0.35, 0.975),  # tint: high lightness, low saturation
        "surface": _hsl_hex(h, s * 0.30, 0.995),
        "text":    _hsl_hex(h, s * 0.55, 0.14),   # shade: dark, slightly desaturated — never pure black
        "muted":   _hsl_hex(h, s * 0.35, 0.42),
        "faint":   _hsl_hex(h, s * 0.30, 0.62),
        "line":    _hsl_hex(h, s * 0.35, 0.90),
    }


# Typeface personalities (researched pairings, loaded from Google Fonts). The model
# picks the one that matches the brand's name and story — a distinctive display face
# is the single loudest "designed by a human" signal vs. the generic system font.
FONTS = {
    "elegant":  {"head": "'Playfair Display', Georgia, serif", "body": "'Lato', sans-serif",
                 "url": "family=Playfair+Display:wght@600;700&family=Lato:wght@400;700"},
    "friendly": {"head": "'Nunito', sans-serif", "body": "'Nunito Sans', sans-serif",
                 "url": "family=Nunito:wght@700;800&family=Nunito+Sans:wght@400;600"},
    "bold":     {"head": "'Bebas Neue', sans-serif", "body": "'Open Sans', sans-serif",
                 "url": "family=Bebas+Neue&family=Open+Sans:wght@400;600"},
    "modern":   {"head": "'Space Grotesk', sans-serif", "body": "'Work Sans', sans-serif",
                 "url": "family=Space+Grotesk:wght@500;700&family=Work+Sans:wght@400;600"},
    "classic":  {"head": "'Lora', Georgia, serif", "body": "'Source Sans 3', sans-serif",
                 "url": "family=Lora:wght@600;700&family=Source+Sans+3:wght@400;600"},
    # Script/cursive: artisanal and personal — candle shops, bakeries, florists.
    # Headings only; always paired with a plain sans body for legibility.
    "handmade": {"head": "'Dancing Script', cursive", "body": "'Karla', sans-serif",
                 "url": "family=Dancing+Script:wght@600;700&family=Karla:wght@400;600"},
}


class Section(BaseModel):
    type: SectionType  # what the renderer does with it (fixed vocabulary)
    id: str            # unique name for edits, e.g. "hero_top"
    heading: str       # customer-facing heading, 5 words max
    body: str = ""     # optional supporting line, 12 words max
    style: str = ""    # short design note (used as a hint, renderer owns the CSS)


class PageTemplate(BaseModel):
    page_type: str                            # "product" or "checkout"
    theme: Literal["light", "warm", "cool"]   # bounded choice among safe palettes
    # Typeface personality matched to the brand (default keeps old cached templates loadable).
    font: Literal["elegant", "friendly", "bold", "modern", "classic", "handmade"] = "modern"
    tagline: str                              # 6 words max, warm
    cta_label: str                            # verb-first, 3 words max, e.g. "Pay now"
    sections: list[Section]

    def model_post_init(self, _):
        # Required sections are enforced here — validation failure makes Instructor
        # retry automatically with the error, so the prompt never has to plead.
        types = [s.type for s in self.sections]
        if self.page_type == "product":
            missing = {"product_details", "price", "cta"} - set(types)
            if missing:
                raise ValueError(f"product page template is missing sections: {missing}")
        if self.page_type == "home":
            missing = {"hero", "product_grid"} - set(types)
            if missing:
                raise ValueError(f"home page template is missing sections: {missing}")
        if types.count("promo") > 1:
            # Von Restorff effect: a highlight only stands out if it is rare.
            raise ValueError("at most ONE promo section is allowed")
        if len(self.sections) > 6:
            # Miller's law: past ~6 blocks a kiosk screen stops being scannable.
            raise ValueError("use at most 6 sections")


# ============================================================================
# Client-brief inputs (merged from Ozzy's input system): richer company brief,
# uploaded reference documents (RAG), and FLUX product-image generation.
# ============================================================================
INDUSTRIES = ["", "Fashion & Apparel", "Consumer Electronics", "Home & Garden",
              "Health & Beauty", "Sports & Outdoors", "Food & Beverage",
              "Industrial / B2B", "Automotive", "Toys & Games", "Stationery & Office"]
AUDIENCES = ["", "General Consumer", "Young Adults (18-30)", "Professionals / Enterprise",
             "Parents & Families", "Enthusiasts / Hobbyists", "Seniors"]
TONES = ["", "Professional", "Conversational", "Enthusiastic", "Technical / precise",
         "Luxury / aspirational", "Friendly"]
STYLE_PREFS = ["", "Clean, minimal, premium", "Dense, feature-rich", "Modern",
               "Technical / spec-heavy", "Luxury", "Warm and cozy"]

LAST_TAG = {"value": ""}  # template-cache tag of the most recent generation (for edits)


def _extract_file_text(files):
    """Read uploaded reference documents (.txt / .md / .pdf)."""
    texts = []
    for f in files or []:
        path = f if isinstance(f, str) else getattr(f, "name", "")
        low = (path or "").lower()
        try:
            if low.endswith((".txt", ".md")):
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    texts.append(fh.read())
            elif low.endswith(".pdf"):
                from pypdf import PdfReader
                texts.append("\n".join((p.extract_text() or "") for p in PdfReader(path).pages))
        except Exception:
            pass
    return "\n\n".join(t for t in texts if t.strip())


def retrieve_doc_context(product_files, theme_files, query, max_tokens=800):
    """RAG over the client's uploaded documents: BM25-pick the chunks most relevant
    to this store, capped by a token budget (input-side discipline)."""
    text = _extract_file_text(list(product_files or []) + list(theme_files or []))
    if not text.strip():
        return "", None
    from rank_bm25 import BM25Okapi
    paras = [p.strip() for p in _re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    for p in paras:
        words = p.split()
        if len(words) <= 120:
            chunks.append(p)
        else:
            for i in range(0, len(words), 100):
                chunks.append(" ".join(words[i:i + 100]))
    tok = lambda s: _re.findall(r"[a-z0-9']+", s.lower())
    bm = BM25Okapi([tok(c) for c in chunks])
    scores = bm.get_scores(tok(query or "brand product design style"))
    order = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    picked, used = [], 0
    for i in order[:8]:
        t = topt.count_tokens(chunks[i])
        if used + t > max_tokens:
            continue
        picked.append(chunks[i])
        used += t
    total = topt.count_tokens(text)
    note = f"- Document RAG: sent {used:,} of {total:,} tokens from uploaded files"
    return "\n\n".join(picked), note


def generate_product_image(description, hf_token):
    """FLUX product photo via Hugging Face (auto-routed provider). 0 LLM tokens."""
    from huggingface_hub import InferenceClient
    client = InferenceClient(provider="auto", api_key=hf_token)
    img = client.text_to_image(
        prompt=("Professional product photography: " + description +
                ". Clean studio background, realistic lighting and shadows, premium "
                "commercial style, no text, no logos, no people."),
        model="black-forest-labs/FLUX.1-schnell")
    path = os.path.join(HERE, "generated_product_image.png")
    img.save(path)
    return path


def _img_data_uri(path):
    import base64
    import mimetypes
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()


# ============================================================================
# Model routing (OPTIMIZATION 6): cheap model for small jobs, strong for design
# ============================================================================
# Both routes use Mistral (one API key, free tier available). Prices are USD per 1M
# tokens (approximate — check Mistral's current pricing page before quoting numbers).
MODELS = {
    "design": {"model": "mistral/mistral-small-latest", "env": "MISTRAL_API_KEY",
               "price": (0.20, 0.60)},        # full template design
    "edit":   {"model": "mistral/ministral-8b-latest", "env": "MISTRAL_API_KEY",
               "price": (0.10, 0.10)},        # tiny diff edits routed to the cheaper model
}


def _call_structured(route, key, prompt, response_model):
    """Structured call with resilience: Mistral occasionally answers in prose instead
    of the required tool call (and the free tier throttles rapid calls), so we retry
    with a pause and fall back to JSON mode on the final attempt."""
    import time as _time
    import instructor
    last_err = None
    for mode in (instructor.Mode.TOOLS, instructor.Mode.TOOLS, instructor.Mode.JSON):
        try:
            client = instructor.from_litellm(litellm.completion, mode=mode)
            obj, resp = client.chat.completions.create_with_completion(
                response_model=response_model,
                messages=[{"role": "user", "content": prompt}],
                max_retries=2,
                model=MODELS[route]["model"],
                api_key=key,
            )
            u = resp.usage
            return obj, u.prompt_tokens, u.completion_tokens
        except Exception as e:
            last_err = e
            _time.sleep(1.5)  # breathe between attempts; also eases rate limits
    raise last_err


# ============================================================================
# 1 + 5: template-once with a disk cache
# ============================================================================
def _template_path(brand, color, page_type, tag=""):
    h = hashlib.md5(f"{brand}|{color}|{page_type}|{tag}".encode()).hexdigest()[:10]
    return os.path.join(TEMPLATE_DIR, f"{page_type}_{h}.json")


def get_template(brand, color, page_type, key, catalog, tag="", brief=None):
    """Return (template, in_tok, out_tok, from_cache)."""
    path = _template_path(brand, color, page_type, tag)
    if os.path.exists(path):                      # OPTIMIZATION 5: template cache
        with open(path, encoding="utf-8") as f:
            return PageTemplate(**json.load(f)), 0, 0, True

    # OPTIMIZATION 3: the design call sees category names only — not the whole catalog.
    categories = sorted({p["category"] for p in catalog["products"]})

    # RAG: retrieve the relevant design wisdom (from human designers) for this page type.
    knowledge = "\n\n".join(retrieve_design_knowledge(page_type))

    # Client brief (Ozzy's input system): only lines the client actually filled in.
    brief = brief or {}
    lines = []
    if brief.get("description"):
        lines.append(f"What they sell: {brief['description']}")
    if brief.get("industry"):
        lines.append(f"Industry: {brief['industry']}")
    if brief.get("audience"):
        lines.append(f"Target audience: {brief['audience']}")
    if brief.get("tone"):
        lines.append(f"Copy tone requested: {brief['tone']}")
    if brief.get("style_pref"):
        lines.append(f"Style preference: {brief['style_pref']}")
    if brief.get("extra"):
        lines.append(f"Extra notes: {brief['extra']}")
    brief_txt = ("\n" + "\n".join(lines)) if lines else ""
    docs_txt = (("\n\n=== CLIENT DOCUMENTS (retrieved from their uploaded files) ===\n"
                 + brief["docs"]) if brief.get("docs") else "")

    prompt = (
        "=== COMPANY BRIEF (specific to this client) ===\n"
        f"Client: '{brand}'. Brand accent color: {color}.{brief_txt}\n"
        f"Screen to design: {_PAGE_DESCRIPTIONS.get(page_type, page_type)} on their in-store "
        f"kiosks (large touchscreen, standing customers). The store uses Smart Stickies RFID "
        f"instant checkout: items are detected automatically the moment they are placed down — "
        f"no scanning, no queues. That effortlessness is the brand story to convey.\n"
        f"Their product categories: {', '.join(categories)}."
        f"{docs_txt}\n\n"
        "=== DESIGN KNOWLEDGE (retrieved from our design library — apply it) ===\n"
        f"{knowledge}\n\n"
        "=== OUTPUT ===\n"
        "Design the template now, applying the design knowledge above to this specific client. "
        "4-6 sections, ordered top to bottom. Choose the theme that best complements the brand "
        "accent color. Choose the font personality from what this business SELLS and who "
        "shops there — match the trade, not a generic mood. Examples: a candle, bakery, or "
        "florist shop = handmade (cursive script, artisanal); sports equipment or streetwear "
        "= bold (loud condensed display, energetic); a bank, pharmacy, or bookstore = classic "
        "(trustworthy serif); jewellery or premium goods = elegant (refined serif); toys, "
        "family, or everyday goods = friendly (warm rounded); gadgets or electronics = modern "
        "(clean geometric). Write all headings, body lines, tagline, and cta_label in the "
        "voice the knowledge describes."
    )
    tpl, in_tok, out_tok = _call_structured("design", key, prompt, PageTemplate)
    with open(path, "w", encoding="utf-8") as f:
        f.write(tpl.model_dump_json())
    return tpl, in_tok, out_tok, False


# ============================================================================
# Rendering — pure Python, ZERO tokens per page (OPTIMIZATION 1)
# ============================================================================
def _accent_text_color(hex_color):
    """WCAG contrast safety: white text on dark accents, near-black on light accents."""
    h = hex_color.lstrip("#")
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except (ValueError, IndexError):
        return "#ffffff"
    luminance = 0.299 * r + 0.587 * g + 0.114 * b  # perceived brightness, 0-255
    return "#ffffff" if luminance < 150 else "#111827"


def _footer_text(tpl):
    f = next((s for s in tpl.sections if s.type == "footer"), None)
    if not f:
        return ""
    return f.heading + (f" — {f.body}" if f.body else "")


def _page_shell(brand, color, tpl, body, footer_text=""):
    """Full-page kiosk screen: header bar, content bands, footer bar.
    Design system: 8-pt grid, 3-size type scale, 60-30-10 color, soft shadows,
    and a brand-matched Google Fonts pairing (display face on .disp elements)."""
    t = make_theme(color, tpl.theme)
    f = FONTS[tpl.font]
    return f"""
<style>
@import url('https://fonts.googleapis.com/css2?{f['url']}&display=swap');
.skf-{tpl.font} {{ font-family: {f['body']}; }}
.skf-{tpl.font} .disp {{ font-family: {f['head']}; }}
</style>
<div class="skf-{tpl.font}" style="font-family:{f['body']};background:{t['bg']};
            border-radius:16px;overflow:hidden;margin:24px 0;color:{t['text']};
            box-shadow:0 1px 2px rgba(0,0,0,.05),0 12px 32px rgba(0,0,0,.08)">
  <div style="background:{t['surface']};padding:20px 40px;display:flex;justify-content:space-between;
              align-items:baseline;border-bottom:1px solid {t['line']}">
    <span class="disp" style="font-size:22px;font-weight:800;color:{t['text']};letter-spacing:-.01em">{brand}</span>
    <span style="font-size:14px;color:{t['muted']}">{tpl.tagline}</span>
  </div>
  {body}
  <div style="background:{t['surface']};border-top:1px solid {t['line']};padding:16px 40px;
              text-align:center;font-size:13px;color:{t['faint']}">{footer_text or "Need help? Tap the help button and staff will come to you."}</div>
</div>"""


def _band(inner, pad="32px 40px", bg=""):
    return f"<div style='padding:{pad};{('background:' + bg + ';') if bg else ''}'>{inner}</div>"


def _cta_button(label, color, inline=False, margin="24px 0 0"):
    # Fitts's law + kiosk touch standards: the primary action is the largest, easiest
    # target on screen (min 56px tall), solid accent — the page's only loud element.
    width = ("display:inline-block;padding:18px 56px" if inline
             else "display:block;padding:18px")
    return (f"<div style='{width};background:{color};color:{_accent_text_color(color)};"
            f"text-align:center;border-radius:10px;font-size:18px;font-weight:600;"
            f"margin:{margin};min-height:56px;box-sizing:border-box;cursor:pointer'>{label}</div>")


def _hero_band(s, t, color, cta="", big=False):
    return f"""
<div style="padding:{'56px 40px 40px' if big else '36px 40px 8px'};text-align:left;
            background:linear-gradient(180deg,{color}14,{color}00)">
  <div class="disp" style="font-size:{'40px' if big else '28px'};font-weight:800;line-height:1.15;
              color:{t['text']};letter-spacing:-.02em">{s.heading}</div>
  {f"<div style='font-size:17px;color:{t['muted']};margin-top:12px;line-height:1.5'>{s.body}</div>" if s.body else ""}
  {cta}
</div>"""


def _promo_band(s, t, color):
    # Von Restorff effect: the single loud accent band — nothing else competes with it.
    txt = _accent_text_color(color)
    return f"""
<div style="background:{color};padding:20px 40px">
  <div style="font-size:16px;font-weight:700;color:{txt}">{s.heading}</div>
  {f"<div style='font-size:13px;color:{txt};opacity:.85;margin-top:2px'>{s.body}</div>" if s.body else ""}
</div>"""


def _info_band(s, t, pad="24px 40px"):
    return _band(
        f"<div style='font-size:15px;font-weight:600;color:{t['text']}'>{s.heading}</div>"
        + (f"<div style='font-size:14px;color:{t['muted']};margin-top:4px;line-height:1.5'>{s.body}</div>" if s.body else ""),
        pad=pad)


def render_home_page(tpl, brand, color, products):
    """The storefront browse screen: hero + category chips + product grid.
    Every product card is rendered in Python — zero tokens each."""
    t = make_theme(color, tpl.theme)
    categories = list(dict.fromkeys(p["category"] for p in products))
    body = ""
    for s in tpl.sections:
        if s.type == "hero":
            cta = f"<div style='margin-top:28px'>{_cta_button(tpl.cta_label, color, inline=True, margin='0')}</div>"
            body += _hero_band(s, t, color, cta=cta, big=True)
            chips = "".join(
                f"<span style='display:inline-block;background:{t['surface']};color:{t['muted']};"
                f"border:1px solid {t['line']};border-radius:999px;padding:10px 20px;margin:4px;"
                f"font-size:14px'>{c}</span>" for c in categories)
            body += f"<div style='padding:0 40px 16px'>{chips}</div>"
        elif s.type == "product_grid":
            cards = "".join(f"""
<div style="background:{t['surface']};border-radius:12px;padding:20px;
            box-shadow:0 1px 2px rgba(0,0,0,.05),0 6px 16px rgba(0,0,0,.05)">
  <div style="height:96px;border-radius:10px;background:{color}12;color:{color};display:flex;
              align-items:center;justify-content:center;font-size:36px;font-weight:700;
              margin-bottom:12px">{p['name'][0]}</div>
  <div style="font-size:15px;font-weight:700;color:{t['text']};line-height:1.3">{p['name']}</div>
  <div style="font-size:12px;color:{t['faint']};margin-top:2px">{p['category']}</div>
  <div style="font-size:17px;font-weight:800;color:{color};margin-top:8px">${p['price']:.2f}</div>
</div>""" for p in products)
            head = f"<div class='disp' style='font-size:20px;font-weight:700;color:{t['text']};margin-bottom:16px'>{s.heading}</div>"
            grid = f"<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px'>{cards}</div>"
            body += _band(head + grid)
        elif s.type == "promo":
            body += _promo_band(s, t, color)
        elif s.type == "info":
            body += _info_band(s, t, pad="8px 40px 24px")
    return _page_shell(brand, color, tpl, body, _footer_text(tpl))


def render_product_page(tpl, brand, color, product, image_uri=None):
    """Product detail screen: slim hero, two-column body (visual tile | details,
    price, CTA), then promo / info bands."""
    t = make_theme(color, tpl.theme)
    hero = next((s for s in tpl.sections if s.type == "hero"), None)
    promo = next((s for s in tpl.sections if s.type == "promo"), None)
    infos = [s for s in tpl.sections if s.type == "info"]

    body = _hero_band(hero, t, color) if hero else ""
    if image_uri:
        left = (f"<div style='flex:0 0 280px'><img src=\"{image_uri}\" alt=\"{product['name']}\" "
                f"style='width:280px;height:280px;object-fit:cover;border-radius:16px;"
                f"display:block'></div>")
    else:
        left = (f"<div style='flex:0 0 280px;height:280px;border-radius:16px;background:{color}12;"
                f"color:{color};display:flex;align-items:center;justify-content:center;"
                f"font-size:96px;font-weight:800'>{product['name'][0]}</div>")
    right = f"""
<div style="flex:1;min-width:280px">
  <div style="font-size:13px;color:{t['faint']};text-transform:uppercase;letter-spacing:.06em">{product['category']} · SKU {product['sku']}</div>
  <div class="disp" style="font-size:30px;font-weight:800;color:{t['text']};line-height:1.15;margin-top:8px">{product['name']}</div>
  <div style="font-size:16px;color:{t['muted']};line-height:1.6;margin-top:12px;max-width:34em">{product['description']}</div>
  <div style="display:flex;align-items:baseline;gap:10px;margin-top:24px">
    <span style="font-size:36px;font-weight:800;color:{color}">${product['price']:.2f}</span>
    <span style="font-size:13px;color:{t['faint']}">before 9% GST</span>
  </div>
  <div style="max-width:360px">{_cta_button(tpl.cta_label, color)}</div>
</div>"""
    body += _band(f"<div style='display:flex;gap:40px;flex-wrap:wrap'>{left}{right}</div>",
                  pad="24px 40px 40px")
    if promo:
        body += _promo_band(promo, t, color)
    for s in infos:
        body += _info_band(s, t)
    return _page_shell(brand, color, tpl, body, _footer_text(tpl))


def render_checkout_page(tpl, brand, color, cart_items, gst_rate):
    """Checkout screen per Baymard research: itemized summary on the left; payment
    panel on the right with muted math, ONE dominant total, one unmistakable CTA."""
    t = make_theme(color, tpl.theme)
    hero = next((s for s in tpl.sections if s.type == "hero"), None)
    subtotal = sum(p["price"] for p in cart_items)
    gst = subtotal * gst_rate
    card_css = (f"background:{t['surface']};border-radius:16px;padding:28px;"
                f"box-shadow:0 1px 2px rgba(0,0,0,.05),0 6px 16px rgba(0,0,0,.05)")

    rows = "".join(
        f"<tr><td style='padding:12px 0;font-size:15px;color:{t['text']};border-bottom:1px solid {t['line']}'>{p['name']}"
        f"<div style='font-size:12px;color:{t['faint']}'>{p['category']}</div></td>"
        f"<td style='padding:12px 0;text-align:right;font-size:15px;font-weight:600;color:{t['text']};"
        f"border-bottom:1px solid {t['line']};vertical-align:top'>${p['price']:.2f}</td></tr>"
        for p in cart_items)
    left = (f"<div style='flex:1.4;min-width:300px;{card_css}'>"
            f"<div style='font-size:13px;color:{t['faint']};text-transform:uppercase;"
            f"letter-spacing:.06em;margin-bottom:8px'>{len(cart_items)} items detected</div>"
            f"<table style='width:100%;border-collapse:collapse'>{rows}</table></div>")

    right = f"""
<div style="flex:1;min-width:280px;{card_css}">
  <div style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:6px">
    <span style="color:{t['muted']}">Subtotal</span><span style="color:{t['muted']}">${subtotal:.2f}</span></div>
  <div style="display:flex;justify-content:space-between;font-size:14px">
    <span style="color:{t['muted']}">GST (9%)</span><span style="color:{t['muted']}">${gst:.2f}</span></div>
  <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:16px;
              padding-top:16px;border-top:2px solid {t['text']}">
    <span style="font-size:16px;font-weight:600;color:{t['text']}">Total</span>
    <span style="font-size:32px;font-weight:800;color:{color}">${subtotal + gst:.2f}</span></div>
  {_cta_button(tpl.cta_label, color)}
  <div style="font-size:12px;color:{t['faint']};text-align:center;margin-top:12px">PayNow · NETS · Visa · Mastercard · Apple Pay · GrabPay</div>
</div>"""
    body = (_hero_band(hero, t, color) if hero else "")
    body += _band(f"<div style='display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start'>{left}{right}</div>",
                  pad="24px 40px 40px")
    promo = next((s for s in tpl.sections if s.type == "promo"), None)
    if promo:
        body += _promo_band(promo, t, color)
    return _page_shell(brand, color, tpl, body, _footer_text(tpl))


# ============================================================================
# 4: diff-based edits — send one section, not the page
# ============================================================================
def edit_section(tpl, section_id, instruction, key):
    """Returns (updated_template, in_tok, out_tok, tokens_saved_vs_whole_template)."""
    target = next((s for s in tpl.sections if s.id == section_id), None)
    if target is None:
        raise ValueError(f"No section '{section_id}'")
    prompt = (f"Apply this edit to the page section JSON and return the updated section.\n"
              f"Edit: {instruction}\nSection: {target.model_dump_json()}")
    new_sec, in_tok, out_tok = _call_structured("edit", key, prompt, Section)
    tpl.sections = [new_sec if s.id == section_id else s for s in tpl.sections]
    whole = topt.count_tokens(tpl.model_dump_json())
    sent = topt.count_tokens(target.model_dump_json())
    return tpl, in_tok, out_tok, max(whole - sent, 0)


# ============================================================================
# Demo pipeline (wired to the UI)
# ============================================================================
def generate_store(brand, color, description, industry, audience, tone, style_pref,
                   extra_notes, product_files, theme_files, api_key, hf_token,
                   catalog_choice, gen_image, n_products):
    key = (api_key or "").strip() or os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        return "", "Paste a Mistral API key first."
    brand = (brand or "Demo Mart").strip()
    color = (color or "#3B5998").strip()
    description = (description or "").strip()

    t0 = time.perf_counter()
    spent_in = spent_out = 0
    notes = []

    # Catalog: a pre-made sample file (0 tokens) or AI-generated to FIT this business.
    try:
        catalog, cat_tag, ci, co, cat_note = resolve_catalog(catalog_choice, brand, key,
                                                             description)
    except Exception as e:
        return "", f"Catalog error: {type(e).__name__}: {str(e)[:300]}"
    spent_in += ci
    spent_out += co
    notes.append(cat_note)
    products = catalog["products"][: int(n_products)]

    # Document RAG (from Ozzy's input system): uploaded client files -> relevant chunks only.
    docs, doc_note = retrieve_doc_context(product_files, theme_files, description or brand)
    if doc_note:
        notes.append(doc_note)

    brief = {"description": description, "industry": industry or "", "audience": audience or "",
             "tone": tone or "", "style_pref": style_pref or "",
             "extra": (extra_notes or "").strip(), "docs": docs}
    brief_sig = hashlib.md5(json.dumps(brief, sort_keys=True).encode()).hexdigest()[:8]
    tag = f"{cat_tag}|{brief_sig}"
    LAST_TAG["value"] = tag

    # ONE design call per page type (or zero, if cached from a previous run).
    try:
        home_tpl, i0, o0, cached0 = get_template(brand, color, "home", key, catalog, tag, brief)
        prod_tpl, i1, o1, cached1 = get_template(brand, color, "product", key, catalog, tag, brief)
        chk_tpl, i2, o2, cached2 = get_template(brand, color, "checkout", key, catalog, tag, brief)
    except Exception as e:
        msg = str(e)
        if "quota" in msg.lower() or "billing" in msg.lower() or "RateLimit" in type(e).__name__:
            return "", ("**API error: the account is out of quota or rate-limited.** "
                        "Check the provider's dashboard for credit/limits, wait a minute, "
                        "or switch the MODELS config to another provider.")
        return "", f"Generation error: {type(e).__name__}: {msg[:300]}"
    spent_in += i0 + i1 + i2
    spent_out += o0 + o1 + o2
    notes.append(f"- Home template: {'cache hit — 0 tokens' if cached0 else f'{i0}+{o0} tokens (one-time)'}")
    notes.append(f"- Product template: {'cache hit — 0 tokens' if cached1 else f'{i1}+{o1} tokens (one-time)'}")
    notes.append(f"- Checkout template: {'cache hit — 0 tokens' if cached2 else f'{i2}+{o2} tokens (one-time)'}")
    for ptype, r in LAST_RETRIEVAL.items():
        notes.append(f"- Design RAG ({ptype}): used {r['used']} of {r['total']} knowledge chunks "
                     f"(~{r['tokens']:,} of {r['total_tokens']:,} tokens sent)")
    LAST_RETRIEVAL.clear()

    # Product image (FLUX via Hugging Face) — optional, graceful on failure, 0 LLM tokens.
    image_uri = None
    hf = (hf_token or "").strip() or os.environ.get("HF_TOKEN", "")
    if gen_image and hf:
        try:
            img_path = generate_product_image(
                description or products[0]["description"], hf)
            image_uri = _img_data_uri(img_path)
            notes.append("- Product image: generated with FLUX (0 LLM tokens)")
        except Exception as e:
            notes.append(f"- Product image failed: {type(e).__name__}: {str(e)[:120]}")
    elif gen_image:
        notes.append("- Product image skipped: no Hugging Face token provided")

    # Every page rendered in Python — zero tokens each.
    html = render_home_page(home_tpl, brand, color, products)
    html += render_checkout_page(chk_tpl, brand, color, products[:3], catalog["gst_rate"])
    for idx, p in enumerate(products):
        html += render_product_page(prod_tpl, brand, color, p,
                                    image_uri if idx == 0 else None)

    elapsed = time.perf_counter() - t0
    pages = len(products) + 2

    # The savings math: optimized vs naive per-page generation.
    naive_in = NAIVE_IN_PER_PAGE * pages
    naive_out = NAIVE_OUT_PER_PAGE * pages
    in_price, out_price = MODELS["design"]["price"]
    naive_cost = naive_in / 1e6 * in_price + naive_out / 1e6 * out_price
    actual_cost = spent_in / 1e6 * in_price + spent_out / 1e6 * out_price
    saved_tokens = (naive_in + naive_out) - (spent_in + spent_out)
    TRACKER.add("template reuse", saved_tokens)
    TRACKER.calls += 1

    report = (
        f"**Generated {pages} pages in {elapsed:.1f}s**\n\n" + "\n".join(notes) +
        f"\n- All {pages} pages rendered from the template in Python: **0 tokens per page**\n\n"
        "| | Tokens in | Tokens out | Cost |\n|---|---:|---:|---:|\n"
        f"| Naive (one LLM call per page) | ~{naive_in:,} | ~{naive_out:,} | ~${naive_cost:.4f} |\n"
        f"| **This pipeline** | **{spent_in:,}** | **{spent_out:,}** | **${actual_cost:.4f}** |\n\n"
        f"**Saved ~{saved_tokens:,} tokens ({(saved_tokens / max(naive_in + naive_out, 1)) * 100:.0f}%)** — "
        "and the gap grows with catalog size: 10,000 SKUs is still ONE design call.\n\n"
        "**Session savings**\n" + TRACKER.report(in_price)
    )
    return html, report


def apply_edit(brand, color, api_key, catalog_choice, section_id, instruction):
    key = (api_key or "").strip() or os.environ.get("MISTRAL_API_KEY", "")
    if not key:
        return "", "Paste a Mistral API key first."
    if not (section_id or "").strip() or not (instruction or "").strip():
        return "", "Pick a section id and type an edit instruction."
    brand = (brand or "Demo Mart").strip()
    color = (color or "#3B5998").strip()
    tag = LAST_TAG["value"] or ("ai" if catalog_choice == AI_CATALOG_CHOICE
                                else CATALOG_FILES.get(catalog_choice, "catalog.json"))

    path = _template_path(brand, color, "product", tag)
    if not os.path.exists(path):
        return "", "Generate the store first, then edit."
    with open(path, encoding="utf-8") as f:
        tpl = PageTemplate(**json.load(f))
    try:
        tpl, in_tok, out_tok, saved = edit_section(tpl, section_id.strip(), instruction, key)
    except Exception as e:
        return "", f"Edit error: {e}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(tpl.model_dump_json())
    TRACKER.add("diff edits", saved)

    catalog, _, _, _, _ = resolve_catalog(catalog_choice, brand, key)
    html = render_product_page(tpl, brand, color, catalog["products"][0])
    report = (
        f"**Edit applied to section `{section_id}`** — sent only that section's JSON.\n\n"
        f"- Tokens spent: {in_tok} in / {out_tok} out\n"
        f"- Tokens avoided by not sending the whole template: **~{saved}**\n\n"
        "**Session savings**\n" + TRACKER.report(MODELS['edit']['price'][0])
    )
    return html, report


def list_sections(brand, color, catalog_choice):
    tag = LAST_TAG["value"] or ("ai" if catalog_choice == AI_CATALOG_CHOICE
                                else CATALOG_FILES.get(catalog_choice, "catalog.json"))
    path = _template_path((brand or "Demo Mart").strip(), (color or "#3B5998").strip(), "product", tag)
    if not os.path.exists(path):
        return "Generate the store first to see its sections."
    with open(path, encoding="utf-8") as f:
        tpl = PageTemplate(**json.load(f))
    return "\n".join(f"- `{s.id}` — {s.heading} ({s.style})" for s in tpl.sections)


def build_ui():
    with gr.Blocks(title="Storefront Generator") as demo:
        gr.Markdown("## AI storefront generator\n"
                    "Describe the business, upload any reference documents, and get a complete "
                    "branded storefront: browse, product, and checkout screens — plus a "
                    "generated product image.")
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Business")
                brand = gr.Textbox(label="Brand name", value="Demo Mart")
                color = gr.Textbox(label="Brand color (hex)", value="#3B5998")
                description = gr.Textbox(
                    label="Business / product description", lines=4,
                    placeholder="What does this store sell? Anything notable about it...")
                extra_notes = gr.Textbox(
                    label="Extra notes (optional)", lines=2,
                    placeholder="Competitors, differentiators, things to avoid...")
            with gr.Column(scale=1):
                gr.Markdown("### Style")
                industry = gr.Dropdown(INDUSTRIES, value="", label="Industry")
                audience = gr.Dropdown(AUDIENCES, value="", label="Target audience")
                tone = gr.Dropdown(TONES, value="", label="Copy tone")
                style_pref = gr.Dropdown(STYLE_PREFS, value="", label="Page style preference")
        gr.Markdown("### Reference documents (optional — the relevant parts are retrieved via RAG)")
        with gr.Row():
            product_files = gr.File(label="Product info", file_count="multiple",
                                    file_types=[".txt", ".md", ".pdf"])
            theme_files = gr.File(label="Brand / theme guidelines", file_count="multiple",
                                  file_types=[".txt", ".md", ".pdf"])
        with gr.Row():
            api_key = gr.Textbox(label="Mistral API key", type="password")
            hf_token = gr.Textbox(label="Hugging Face token (optional, for the product image)",
                                  type="password")
        with gr.Row():
            catalog_choice = gr.Dropdown([AI_CATALOG_CHOICE] + list(CATALOG_FILES.keys()),
                                         value=AI_CATALOG_CHOICE, label="Catalog")
            n_products = gr.Slider(1, 12, value=6, step=1, label="Products to generate pages for")
            gen_image = gr.Checkbox(label="Generate product image (FLUX)", value=True)
        gen_btn = gr.Button("Generate store", variant="primary")
        report = gr.Markdown()
        preview = gr.HTML(label="Generated pages")

        gr.Markdown("---\n### Edit a section (diff-based — sends one section, not the page)")
        sections_md = gr.Markdown()
        show_btn = gr.Button("Show template sections")
        with gr.Row():
            section_id = gr.Textbox(label="Section id")
            instruction = gr.Textbox(label="Edit instruction",
                                     placeholder="e.g. make the heading friendlier")
        edit_btn = gr.Button("Apply edit")

        gen_btn.click(generate_store,
                      [brand, color, description, industry, audience, tone, style_pref,
                       extra_notes, product_files, theme_files, api_key, hf_token,
                       catalog_choice, gen_image, n_products],
                      [preview, report])
        show_btn.click(list_sections, [brand, color, catalog_choice], sections_md)
        edit_btn.click(apply_edit,
                       [brand, color, api_key, catalog_choice, section_id, instruction],
                       [preview, report])
    return demo


if __name__ == "__main__":
    # Respect a PORT assigned by the environment (e.g. preview servers); default 7861.
    build_ui().launch(server_port=int(os.environ.get("PORT", 7861)))
