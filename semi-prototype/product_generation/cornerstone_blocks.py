"""
CTCM-style block library for Cornerstone product pages.

Ported from Judah's CTCM thingy
Each Cornerstone `Component` maps 1:1 onto one *section* here. A section's
`content` dict is expected to follow the schema documented per type below
(see also the layout-generation prompt in cornerstone_layout_generator.py,
which instructs the AI to populate `content` this way):

    hero            content: {image, cta_text, cta_url}
    product_visual  content: {image}                    (folds into hero if a
                                                          hero section exists)
    feature_grid    content: {items: [{title, body, image}]}
    benefits        content: {items: [{text, image}]}
    specifications  content: {items: [{key, value}]}
    comparison      content: {columns: [str], rows: [{label, values: [str]}]}
    testimonial     content: {items: [{quote, author, image}]}
    faq             content: {items: [{question, answer}]}
    cta             content: {cta_text, cta_url}
    footer          content: {text}

Any `image` field may be a local file path (already copied into the site's
assets/ folder by the caller) or an http(s) URL. Any section may also carry
`content["image_prompt"]` — a caller-populated field meaning "no image yet,
here's what to generate"; renderer functions here just render whatever
`image` value already exists by the time they run (image generation itself
happens in main.py, before rendering).
"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Callable


@dataclass
class BlockResult:
    """A block can contribute page sections and/or standalone files."""

    sections: dict[str, str] | None = None
    files: dict[str, str] | None = None


def slugify(value: str) -> str:
    chars = []
    for char in (value or "").lower().strip():
        if char.isalnum():
            chars.append(char)
        elif char in {" ", "-", "_"}:
            chars.append("-")
    slug = "".join(chars).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "section"


def _esc(value: Any) -> str:
    return escape(str(value)) if value is not None else ""


def _image_tag(src: str, alt: str, placeholder_class: str) -> str:
    src = (src or "").strip()
    if src:
        return f'<img src="{escape(src, quote=True)}" alt="{escape(alt, quote=True)}" loading="lazy">'
    return f'<div class="{placeholder_class}">Image</div>'


# ============================================================
# Required blocks: shell, styles, interactions
# ============================================================

def block_base_styles(context: dict[str, Any]) -> BlockResult:
    accent = context.get("accent_color") or "#2563eb"
    css = f"""
:root {{
  --ctcm-accent: {escape(str(accent))};
  --ctcm-ink: #17202a;
  --ctcm-muted: #657080;
  --ctcm-line: #d8dee7;
  --ctcm-surface: #ffffff;
  --ctcm-soft: #f6f8fb;
}}

* {{ box-sizing: border-box; }}

body {{
  margin: 0;
  color: var(--ctcm-ink);
  background: #f3f5f8;
  font-family: -apple-system, "Segoe UI", Arial, Helvetica, sans-serif;
  line-height: 1.55;
}}

.ctcm-page {{ max-width: 1080px; margin: 0 auto; padding: 0 18px 56px; }}

.ctcm-section {{
  margin-top: 22px;
  background: var(--ctcm-surface);
  border: 1px solid var(--ctcm-line);
  border-radius: 12px;
  padding: 28px 32px;
}}

.ctcm-section h2 {{ margin: 0 0 14px; font-size: 1.4rem; }}

/* Hero */
.ctcm-hero {{
  display: grid;
  grid-template-columns: minmax(280px, 0.95fr) minmax(300px, 1.05fr);
  gap: 28px;
  align-items: center;
  background: var(--ctcm-surface);
  border: 1px solid var(--ctcm-line);
  border-radius: 12px;
  padding: 30px;
  margin-top: 22px;
}}
.ctcm-hero.no-image {{ grid-template-columns: 1fr; text-align: center; }}
.ctcm-media {{
  aspect-ratio: 1 / 1;
  border: 1px solid var(--ctcm-line);
  border-radius: 10px;
  background: var(--ctcm-soft);
  display: grid;
  place-items: center;
  overflow: hidden;
}}
.ctcm-media img {{ width: 100%; height: 100%; object-fit: contain; }}
.ctcm-media-placeholder, .ctcm-card-image-placeholder {{ color: var(--ctcm-muted); font-size: 0.9rem; }}
.ctcm-title {{ margin: 0 0 10px; font-size: clamp(1.9rem, 3.4vw, 3rem); line-height: 1.08; }}
.ctcm-tagline {{ color: var(--ctcm-accent); font-weight: 700; margin: 0 0 12px; }}
.ctcm-description {{ color: var(--ctcm-muted); margin: 0 0 20px; }}

.ctcm-button {{
  border: 0; border-radius: 8px; background: var(--ctcm-accent); color: #fff;
  cursor: pointer; display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700; min-height: 44px; padding: 0 22px; text-decoration: none; font-size: 1rem;
}}

/* Feature grid / benefits */
.ctcm-card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }}
.ctcm-card {{ border: 1px solid var(--ctcm-line); border-radius: 10px; padding: 18px; background: var(--ctcm-soft); }}
.ctcm-card-image {{ width: 100%; aspect-ratio: 16 / 10; border-radius: 8px; overflow: hidden; background: #eef1f5; display: grid; place-items: center; margin-bottom: 12px; }}
.ctcm-card-image img {{ width: 100%; height: 100%; object-fit: cover; }}
.ctcm-card h3 {{ margin: 0 0 6px; font-size: 1.05rem; }}
.ctcm-card p {{ margin: 0; color: var(--ctcm-muted); }}

.ctcm-benefits-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }}
.ctcm-benefits-list li {{ display: flex; gap: 10px; align-items: flex-start; }}
.ctcm-benefits-list li::before {{ content: "\\2713"; color: var(--ctcm-accent); font-weight: 700; }}

/* Specifications */
.ctcm-specs dl {{ display: grid; grid-template-columns: minmax(140px, 0.35fr) minmax(0, 1fr); gap: 8px 16px; margin: 0; }}
.ctcm-specs dt {{ color: var(--ctcm-muted); font-weight: 700; }}
.ctcm-specs dd {{ margin: 0; }}

/* Comparison */
.ctcm-comparison-wrap {{ overflow-x: auto; }}
table.ctcm-comparison {{ width: 100%; border-collapse: collapse; }}
table.ctcm-comparison th, table.ctcm-comparison td {{ border: 1px solid var(--ctcm-line); padding: 10px 12px; text-align: left; }}
table.ctcm-comparison th {{ background: var(--ctcm-soft); }}

/* Testimonials */
.ctcm-testimonial-track {{ display: flex; gap: 18px; overflow-x: auto; scroll-snap-type: x mandatory; padding-bottom: 6px; }}
.ctcm-testimonial-card {{ flex: 0 0 280px; scroll-snap-align: start; border: 1px solid var(--ctcm-line); border-radius: 10px; padding: 18px; background: var(--ctcm-soft); }}
.ctcm-testimonial-avatar {{ width: 48px; height: 48px; border-radius: 999px; overflow: hidden; background: #e2e8f0; margin-bottom: 10px; }}
.ctcm-testimonial-avatar img {{ width: 100%; height: 100%; object-fit: cover; }}
.ctcm-testimonial-quote {{ font-style: italic; margin: 0 0 10px; }}
.ctcm-testimonial-author {{ font-weight: 700; color: var(--ctcm-muted); }}

/* FAQ */
.ctcm-faq-item {{ border-bottom: 1px solid var(--ctcm-line); }}
.ctcm-faq-item:last-child {{ border-bottom: 0; }}
.ctcm-faq-question {{
  width: 100%; text-align: left; background: none; border: 0; cursor: pointer;
  font-weight: 700; font-size: 1rem; padding: 14px 0; display: flex; justify-content: space-between; gap: 12px;
}}
.ctcm-faq-question::after {{ content: "+"; color: var(--ctcm-accent); }}
.ctcm-faq-item.is-open .ctcm-faq-question::after {{ content: "\\2212"; }}
.ctcm-faq-answer {{ display: none; color: var(--ctcm-muted); padding: 0 0 14px; }}
.ctcm-faq-item.is-open .ctcm-faq-answer {{ display: block; }}

/* CTA banner */
.ctcm-cta {{ text-align: center; background: color-mix(in srgb, var(--ctcm-accent) 10%, white); }}
.ctcm-cta h2 {{ margin-bottom: 8px; }}
.ctcm-cta p {{ color: var(--ctcm-muted); margin: 0 0 18px; }}

.ctcm-footer {{ text-align: center; padding: 28px 0; color: var(--ctcm-muted); font-size: 0.88rem; }}

@media (max-width: 780px) {{
  .ctcm-hero {{ grid-template-columns: 1fr; }}
}}

/* ==========================================================
   Product Tabs
   ========================================================== */

.ctcm-tabs-list{{
    display:flex;
    flex-wrap:wrap;
    gap:10px;
    margin-bottom:20px;
}}

.ctcm-tab-button{{
    border:1px solid var(--ctcm-line);
    background:white;
    border-radius:8px;
    padding:10px 16px;
    cursor:pointer;
    transition:.2s;
}}

.ctcm-tab-button.is-active{{
    background:var(--ctcm-accent);
    color:white;
}}

.ctcm-tab-panel{{
    display:none;
}}

.ctcm-tab-panel.is-active{{
    display:block;
}}


/* ==========================================================
   Configurator
   ========================================================== */

.ctcm-configurator-grid{{
    display:grid;
    grid-template-columns:1fr 340px;
    gap:28px;
}}

.ctcm-category{{
    border:1px solid var(--ctcm-line);
    border-radius:10px;
    margin-bottom:18px;
}}

.ctcm-category-toggle{{
    width:100%;
    border:none;
    background:#f7f8fa;
    padding:16px;
    text-align:left;
    cursor:pointer;
    font-weight:700;
}}

.ctcm-category-body{{
    display:none;
    padding:16px;
}}

.ctcm-category.is-open .ctcm-category-body{{
    display:block;
}}

.ctcm-option{{
    display:grid;
    grid-template-columns:90px 1fr auto;
    gap:16px;
    align-items:center;
    margin-bottom:16px;
}}

.ctcm-option-image{{
    aspect-ratio:1;
}}

.ctcm-option-name{{
    font-weight:700;
    display:block;
}}

.ctcm-option-meta{{
    color:var(--ctcm-muted);
    font-size:.9rem;
}}

.ctcm-qty{{
    display:flex;
    align-items:center;
    gap:6px;
}}

.ctcm-qty input{{
    width:56px;
    text-align:center;
}}

.ctcm-summary{{
    border:1px solid var(--ctcm-line);
    border-radius:10px;
    padding:20px;
    position:sticky;
    top:20px;
}}

.ctcm-summary-line{{
    display:flex;
    justify-content:space-between;
    margin-bottom:10px;
}}

.ctcm-summary-total{{
    display:flex;
    justify-content:space-between;
    font-size:1.15rem;
    font-weight:700;
    border-top:1px solid var(--ctcm-line);
    padding-top:12px;
    margin-top:12px;
}}

.ctcm-toast{{
    margin-top:12px;
    color:var(--ctcm-accent);
}}


/* ==========================================================
   Metafields
   ========================================================== */

.ctcm-metafields dl{{
    display:grid;
    grid-template-columns:220px 1fr;
    gap:10px 20px;
}}

.ctcm-metafields dt{{
    font-weight:700;
}}

.ctcm-metafields dd{{
    margin:0;
}}
""".strip()
    return BlockResult(files={"assets/css/site.css": css})


def block_base_interactions(context: dict[str, Any]) -> BlockResult:
    js = r"""
(function () {

function updateConfigurator(section){

    var total = 0;
    var lines = [];

    section.querySelectorAll("[data-ctcm-item-qty]").forEach(function(input){

        var qty = parseInt(input.value || 0);

        if(!qty) return;

        var price = parseFloat(
            String(input.dataset.price || "0").replace(/[^0-9.]/g,"")
        );

        total += qty * price;

        lines.push(
            "<div class='ctcm-summary-line'>" +
            "<span>" + input.dataset.name + " × " + qty + "</span>" +
            "<span>$" + (qty * price).toFixed(2) + "</span>" +
            "</div>"
        );

    });

    var summary = section.querySelector("[data-ctcm-summary-lines]");
    if(summary){
        summary.innerHTML = lines.join("");
    }

    var totalEl = section.querySelector("[data-ctcm-summary-total]");
    if(totalEl){
        totalEl.textContent = "$" + total.toFixed(2);
    }

}

document.addEventListener("click",function(event){

    /* FAQ */

    var faq = event.target.closest("[data-ctcm-faq-toggle]");

    if(faq){
        faq.closest(".ctcm-faq-item").classList.toggle("is-open");
        return;
    }

    /* Testimonials */

    var scroll = event.target.closest("[data-ctcm-testi-scroll]");

    if(scroll){

        var track=document.getElementById(
            scroll.dataset.ctcmTestiScroll ||
            scroll.getAttribute("data-ctcm-testi-scroll")
        );

        if(track){

            var dir =
                scroll.dataset.dir==="prev"
                ? -1
                : 1;

            track.scrollBy({
                left:track.clientWidth*0.9*dir,
                behavior:"smooth"
            });

        }

        return;

    }

    /* Tabs */

    var tab = event.target.closest("[data-ctcm-tab]");

    if(tab){

        var wrapper = tab.closest("[data-ctcm-tabs]");

        wrapper.querySelectorAll("[data-ctcm-tab]").forEach(function(btn){
            btn.classList.remove("is-active");
        });

        wrapper.querySelectorAll("[data-ctcm-tab-panel]").forEach(function(panel){
            panel.classList.remove("is-active");
        });

        tab.classList.add("is-active");

        var panel = document.getElementById(tab.dataset.ctcmTab);

        if(panel){
            panel.classList.add("is-active");
        }

        return;

    }

    /* Configurator accordion */

    var toggle = event.target.closest("[data-ctcm-category-toggle]");

    if(toggle){

        toggle.closest(".ctcm-category").classList.toggle("is-open");

        return;

    }

    /* Quantity */

    var qtyBtn = event.target.closest("[data-ctcm-qty]");

    if(qtyBtn){

        var input = qtyBtn.parentElement.querySelector("[data-ctcm-item-qty]");

        if(input){

            var value = parseInt(input.value||0);

            if(qtyBtn.dataset.ctcmQty==="inc") value++;
            if(qtyBtn.dataset.ctcmQty==="dec") value=Math.max(0,value-1);

            input.value=value;

            updateConfigurator(
                qtyBtn.closest("[data-ctcm-configurator]")
            );

        }

        return;

    }

    /* Add Selected */

    var add = event.target.closest("[data-ctcm-add-selected]");

    if(add){

        var toast = add.parentElement.querySelector("[data-ctcm-toast]");

        if(toast){

            toast.textContent="Selections ready for cart integration.";

            setTimeout(function(){

                toast.textContent="";

            },2500);

        }

    }

});

document.addEventListener("change",function(event){

    if(event.target.matches("[data-ctcm-item-qty]")){

        updateConfigurator(
            event.target.closest("[data-ctcm-configurator]")
        );

    }

});

})();
""".strip()

    return BlockResult(files={"assets/js/site.js": js})

def block_site_shell(context: dict[str, Any]) -> BlockResult:
    title = escape(str(context.get("site_title") or "Product Page"))
    order = context.get("_section_order") or []
    sections = context.get("_sections", {})
    body = "".join(sections.get(sid, "") for sid in order)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="Cache-Control" content="no-store">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="assets/css/site.css">
</head>
<body>
  <main class="ctcm-page">
    {body}
  </main>
  <script src="assets/js/site.js"></script>
</body>
</html>
"""
    return BlockResult(files={"index.html": html})


# ============================================================
# Section blocks (one Cornerstone Component -> one section)
# ============================================================

def block_hero(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    heading = _esc(section.get("heading") or ctx.get("product_name") or "")
    tagline = _esc(ctx.get("tagline") or "")
    body = _esc(section.get("body") or "")
    image = str(content.get("image") or "").strip()
    cta_text = _esc(content.get("cta_text") or ctx.get("primary_cta") or "")
    cta_url = str(content.get("cta_url") or "").strip()

    cta_html = ""
    if cta_text:
        if cta_url:
            cta_html = f'<a class="ctcm-button" href="{escape(cta_url, quote=True)}">{cta_text}</a>'
        else:
            cta_html = f'<button class="ctcm-button" type="button">{cta_text}</button>'

    media_html = (
        f'<div class="ctcm-media">{_image_tag(image, heading, "ctcm-media-placeholder")}</div>'
        if image else ""
    )
    hero_class = "ctcm-hero" if image else "ctcm-hero no-image"

    return f"""
<section class="{hero_class}" id="{_esc(section.get('id'))}">
  {media_html}
  <div class="ctcm-hero-info">
    {f'<p class="ctcm-tagline">{tagline}</p>' if tagline else ""}
    <h1 class="ctcm-title">{heading}</h1>
    {f'<p class="ctcm-description">{body}</p>' if body else ""}
    {cta_html}
  </div>
</section>
""".strip()


def block_product_visual(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    image = str(content.get("image") or "").strip()
    heading = _esc(section.get("heading") or "")
    return f"""
<section class="ctcm-section" id="{_esc(section.get('id'))}">
  {f'<h2>{heading}</h2>' if heading else ""}
  <div class="ctcm-media">{_image_tag(image, heading, "ctcm-media-placeholder")}</div>
</section>
""".strip()


def block_feature_grid(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    heading = _esc(section.get("heading") or "Features")
    items = content.get("items") or []
    cards = []
    for item in items:
        title = _esc(item.get("title") or "")
        body = _esc(item.get("body") or "")
        image = str(item.get("image") or "").strip()
        image_html = (
            f'<div class="ctcm-card-image">{_image_tag(image, title, "ctcm-card-image-placeholder")}</div>'
            if image else ""
        )
        cards.append(f"""
<div class="ctcm-card">
  {image_html}
  <h3>{title}</h3>
  <p>{body}</p>
</div>
""".strip())
    return f"""
<section class="ctcm-section" id="{_esc(section.get('id'))}">
  <h2>{heading}</h2>
  {f'<p class="ctcm-description">{_esc(section.get("body"))}</p>' if section.get("body") else ""}
  <div class="ctcm-card-grid">{''.join(cards)}</div>
</section>
""".strip()


def block_benefits(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    heading = _esc(section.get("heading") or "Benefits")
    items = content.get("items") or []
    rows = "".join(f"<li>{_esc(item.get('text') or item.get('title') or '')}</li>" for item in items)
    return f"""
<section class="ctcm-section" id="{_esc(section.get('id'))}">
  <h2>{heading}</h2>
  {f'<p class="ctcm-description">{_esc(section.get("body"))}</p>' if section.get("body") else ""}
  <ul class="ctcm-benefits-list">{rows}</ul>
</section>
""".strip()


def block_specifications(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    heading = _esc(section.get("heading") or "Specifications")
    items = content.get("items") or []
    rows = "".join(
        f"<dt>{_esc(item.get('key') or '')}</dt><dd>{_esc(item.get('value') or '')}</dd>"
        for item in items
    )
    return f"""
<section class="ctcm-section ctcm-specs" id="{_esc(section.get('id'))}">
  <h2>{heading}</h2>
  <dl>{rows}</dl>
</section>
""".strip()


def block_comparison(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    heading = _esc(section.get("heading") or "Comparison")
    columns = content.get("columns") or []
    rows = content.get("rows") or []
    head = "<th></th>" + "".join(f"<th>{_esc(c)}</th>" for c in columns)
    body_rows = []
    for row in rows:
        label = _esc(row.get("label") or "")
        values = row.get("values") or []
        cells = "".join(f"<td>{_esc(v)}</td>" for v in values)
        body_rows.append(f"<tr><th scope=\"row\">{label}</th>{cells}</tr>")
    return f"""
<section class="ctcm-section" id="{_esc(section.get('id'))}">
  <h2>{heading}</h2>
  <div class="ctcm-comparison-wrap">
    <table class="ctcm-comparison">
      <thead><tr>{head}</tr></thead>
      <tbody>{''.join(body_rows)}</tbody>
    </table>
  </div>
</section>
""".strip()


def block_testimonial(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    heading = _esc(section.get("heading") or "What people are saying")
    items = content.get("items") or []
    track_id = f"testi-track-{_esc(section.get('id'))}"
    cards = []
    for item in items:
        quote = _esc(item.get("quote") or "")
        author = _esc(item.get("author") or "")
        image = str(item.get("image") or "").strip()
        avatar = (
            f'<div class="ctcm-testimonial-avatar">{_image_tag(image, author, "")}</div>'
            if image else ""
        )
        cards.append(f"""
<div class="ctcm-testimonial-card">
  {avatar}
  <p class="ctcm-testimonial-quote">&ldquo;{quote}&rdquo;</p>
  <p class="ctcm-testimonial-author">{author}</p>
</div>
""".strip())
    nav = ""
    if len(items) > 1:
        nav = f"""
<div class="ctcm-testimonial-nav">
  <button type="button" data-ctcm-testi-scroll="{track_id}" data-dir="prev" class="ctcm-button">&larr;</button>
  <button type="button" data-ctcm-testi-scroll="{track_id}" data-dir="next" class="ctcm-button">&rarr;</button>
</div>
""".strip()
    return f"""
<section class="ctcm-section" id="{_esc(section.get('id'))}">
  <h2>{heading}</h2>
  <div class="ctcm-testimonial-track" id="{track_id}">{''.join(cards)}</div>
  {nav}
</section>
""".strip()


def block_faq(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    heading = _esc(section.get("heading") or "Frequently asked questions")
    items = content.get("items") or []
    rows = []
    for index, item in enumerate(items):
        question = _esc(item.get("question") or "")
        answer = _esc(item.get("answer") or "")
        open_class = " is-open" if index == 0 else ""
        rows.append(f"""
<div class="ctcm-faq-item{open_class}">
  <button class="ctcm-faq-question" type="button" data-ctcm-faq-toggle>{question}</button>
  <div class="ctcm-faq-answer">{answer}</div>
</div>
""".strip())
    return f"""
<section class="ctcm-section" id="{_esc(section.get('id'))}">
  <h2>{heading}</h2>
  {''.join(rows)}
</section>
""".strip()


def block_cta(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    heading = _esc(section.get("heading") or "Ready to get started?")
    body = _esc(section.get("body") or "")
    cta_text = _esc(content.get("cta_text") or ctx.get("primary_cta") or "Get started")
    cta_url = str(content.get("cta_url") or "").strip()
    if cta_url:
        button = f'<a class="ctcm-button" href="{escape(cta_url, quote=True)}">{cta_text}</a>'
    else:
        button = f'<button class="ctcm-button" type="button">{cta_text}</button>'
    return f"""
<section class="ctcm-section ctcm-cta" id="{_esc(section.get('id'))}">
  <h2>{heading}</h2>
  {f'<p>{body}</p>' if body else ""}
  {button}
</section>
""".strip()


def block_footer(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}
    text = _esc(content.get("text") or section.get("body") or section.get("heading") or "")
    return f"""
<footer class="ctcm-footer" id="{_esc(section.get('id'))}">{text}</footer>
""".strip()

def block_custom_field_tabs(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}

    heading = _esc(section.get("heading") or "Product Information")
    tabs = content.get("tabs") or []

    if not tabs:
        return ""

    buttons = []
    panels = []

    section_id = slugify(section.get("id") or heading)

    for index, tab in enumerate(tabs):
        title = _esc(tab.get("title") or f"Tab {index+1}")
        body = _esc(tab.get("content") or tab.get("body") or "")

        panel_id = f"{section_id}-panel-{index}"

        active = " is-active" if index == 0 else ""

        buttons.append(
            f'<button class="ctcm-tab-button{active}" '
            f'data-ctcm-tab="{panel_id}" '
            f'type="button">{title}</button>'
        )

        panels.append(
            f'<div id="{panel_id}" '
            f'class="ctcm-tab-panel{active}" '
            f'data-ctcm-tab-panel>'
            f'{body}'
            f'</div>'
        )

    return f"""
<section class="ctcm-section" id="{_esc(section.get("id"))}" data-ctcm-tabs>
    <h2>{heading}</h2>

    <div class="ctcm-tabs-list">
        {''.join(buttons)}
    </div>

    {''.join(panels)}
</section>
""".strip()

def block_configurator(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    content = section.get("content") or {}

    heading = _esc(section.get("heading") or "Configurator")

    categories = content.get("categories") or []

    html = []

    for cat_index, category in enumerate(categories):

        cat_name = _esc(category.get("name") or f"Category {cat_index+1}")

        options = []

        for opt_index, option in enumerate(category.get("items") or []):

            name = _esc(option.get("name") or "")
            variant = _esc(option.get("variant") or "")
            price = _esc(option.get("price") or "")
            image = option.get("image") or ""

            options.append(f"""
<div class="ctcm-option">

<div class="ctcm-option-image">
{_image_tag(image,name,"ctcm-card-image-placeholder")}
</div>

<div>

<span class="ctcm-option-name">{name}</span>

<span class="ctcm-option-meta">
{variant} {price}
</span>

</div>

<div class="ctcm-qty">

<button type="button" data-ctcm-qty="dec">−</button>

<input
type="number"
min="0"
max="99"
value="0"
data-ctcm-item-qty
data-name="{name}"
data-price="{price}">

<button type="button" data-ctcm-qty="inc">+</button>

</div>

</div>
""")

        open_class = " is-open" if cat_index == 0 else ""

        html.append(f"""
<div class="ctcm-category{open_class}">

<button
class="ctcm-category-toggle"
type="button"
data-ctcm-category-toggle>

<span>{cat_name}</span>

</button>

<div class="ctcm-category-body">

{''.join(options)}

</div>

</div>
""")

    return f"""
<section
class="ctcm-section"
id="{_esc(section.get("id"))}"
data-ctcm-configurator>

<h2>{heading}</h2>

<div class="ctcm-configurator-grid">

<div>

{''.join(html)}

</div>

<aside class="ctcm-summary">

<h3>Your Selection</h3>

<div data-ctcm-summary-lines></div>

<div class="ctcm-summary-total">

<span>Total</span>

<span data-ctcm-summary-total>$0.00</span>

</div>

<button
class="ctcm-button"
data-ctcm-add-selected>

Add Selected

</button>

<div
class="ctcm-toast"
data-ctcm-toast></div>

</aside>

</div>

</section>
""".strip()

def block_metafields_panel(section: dict[str, Any], ctx: dict[str, Any]) -> str:

    content = section.get("content") or {}

    heading = _esc(section.get("heading") or "Metafields")

    fields = content.get("items") or []

    rows = []

    for field in fields:

        rows.append(
            f"<dt>{_esc(field.get('key'))}</dt>"
            f"<dd>{_esc(field.get('value'))}</dd>"
        )

    return f"""
<section
class="ctcm-section ctcm-metafields"
id="{_esc(section.get('id'))}">

<h2>{heading}</h2>

<dl>

{''.join(rows)}

</dl>

</section>
""".strip()


SECTION_RENDERERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], str]] = {
    "hero": block_hero,
    "product_visual": block_product_visual,
    "feature_grid": block_feature_grid,
    "benefits": block_benefits,
    "specifications": block_specifications,
    "comparison": block_comparison,
    "testimonial": block_testimonial,
    "faq": block_faq,
    "cta": block_cta,
    "footer": block_footer,
    "custom_field_tabs": block_custom_field_tabs,
    "configurator": block_configurator,
    "metafields_panel": block_metafields_panel,
}


def render_section(section: dict[str, Any], ctx: dict[str, Any]) -> str:
    renderer = SECTION_RENDERERS.get(section.get("type"))
    if renderer is None:
        return ""
    return renderer(section, ctx)


def assemble_site(sections: list[dict[str, Any]], ctx: dict[str, Any]) -> dict[str, str]:
    sections = _fold_product_visual_into_hero(sections)

    rendered: dict[str, str] = {}
    order: list[str] = []
    for section in sections:
        sid = section.get("id") or slugify(section.get("heading", "section"))
        html = render_section(section, ctx)
        if not html:
            continue
        rendered[sid] = html
        order.append(sid)

    context = dict(ctx)
    context["_sections"] = rendered
    context["_section_order"] = order

    files: dict[str, str] = {}
    files.update(block_base_styles(context).files or {})
    files.update(block_base_interactions(context).files or {})
    files.update(block_site_shell(context).files or {})
    return files


def _fold_product_visual_into_hero(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    has_hero = any(s.get("type") == "hero" for s in sections)
    hero_has_image = any(
        s.get("type") == "hero" and (s.get("content") or {}).get("image")
        for s in sections
    )
    if not (has_hero and not hero_has_image):
        return sections

    visual_image = None
    remaining = []
    for section in sections:
        if section.get("type") == "product_visual" and visual_image is None:
            visual_image = (section.get("content") or {}).get("image")
            continue
        remaining.append(section)

    if visual_image is None:
        return sections

    for section in remaining:
        if section.get("type") == "hero":
            section = dict(section)
            section["content"] = {**(section.get("content") or {}), "image": visual_image}
            remaining[remaining.index(next(s for s in remaining if s.get("type") == "hero"))] = section
            break
    return remaining
