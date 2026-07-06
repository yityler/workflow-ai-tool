"""Reusable CTCM product-page block functions.

These blocks are distilled from the Cornerstone tabs/configurator/metafields
theme customization into portable functions that can be selected by RAG and
assembled by another program.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any, Callable


BLOCK_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = BLOCK_DIR / "block_manifest.json"


@dataclass
class BlockResult:
    """A block can contribute page sections and/or files."""

    sections: dict[str, str] | None = None
    files: dict[str, str] | None = None


def get_block_manifest() -> dict[str, Any]:
    """Return the RAG-friendly block manifest."""

    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def get_required_block_names() -> list[str]:
    """Return blocks that should be called immediately by a site generator."""

    manifest = get_block_manifest()
    return [block["name"] for block in manifest["blocks"] if block.get("required")]


def get_block_callable(name: str) -> Callable[[dict[str, Any]], BlockResult]:
    """Resolve a manifest block name to its Python function."""

    mapping: dict[str, Callable[[dict[str, Any]], BlockResult]] = {
        "site_shell": block_site_shell,
        "base_styles": block_base_styles,
        "base_interactions": block_base_interactions,
        "product_hero": block_product_hero,
        "custom_field_tabs": block_custom_field_tabs,
        "configurator": block_configurator,
        "metafields_panel": block_metafields_panel,
    }
    if name not in mapping:
        raise KeyError(f"Unknown block: {name}")
    return mapping[name]


def as_money(value: Any) -> str:
    """Format a numeric-ish value as money, preserving strings like '$19.99'."""

    if value is None or value == "":
        return "$0.00"
    if isinstance(value, str) and value.strip().startswith("$"):
        return value.strip()
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return escape(str(value))


def price_number(value: Any, default: float = 0) -> float:
    """Return a plain numeric price for internal calculations/data attributes."""

    if value is None or value == "":
        return default
    try:
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (TypeError, ValueError):
        return default


def slugify(value: str) -> str:
    """Small slug helper for ids/classes."""

    chars = []
    for char in value.lower().strip():
        if char.isalnum():
            chars.append(char)
        elif char in {" ", "-", "_"}:
            chars.append("-")
    slug = "".join(chars).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "section"


def block_base_styles(context: dict[str, Any]) -> BlockResult:
    accent = context.get("accent_color") or "#0f766e"
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
  font-family: Arial, Helvetica, sans-serif;
  line-height: 1.5;
}}

.ctcm-page {{
  max-width: 1180px;
  margin: 0 auto;
  padding: 28px 18px 56px;
}}

.ctcm-product {{
  display: grid;
  grid-template-columns: minmax(280px, 0.95fr) minmax(300px, 1.05fr);
  gap: 28px;
  align-items: start;
  background: var(--ctcm-surface);
  border: 1px solid var(--ctcm-line);
  border-radius: 8px;
  padding: 22px;
}}

.ctcm-media {{
  aspect-ratio: 1 / 1;
  border: 1px solid var(--ctcm-line);
  border-radius: 8px;
  background: var(--ctcm-soft);
  display: grid;
  place-items: center;
  overflow: hidden;
}}

.ctcm-media img {{
  width: 100%;
  height: 100%;
  object-fit: contain;
}}

.ctcm-media-placeholder {{
  color: var(--ctcm-muted);
  font-size: 0.95rem;
}}

.ctcm-title {{
  margin: 0 0 8px;
  font-size: clamp(2rem, 4vw, 3.4rem);
  line-height: 1.05;
}}

.ctcm-price {{
  margin: 0 0 16px;
  color: var(--ctcm-accent);
  font-size: 1.45rem;
  font-weight: 700;
}}

.ctcm-description {{
  color: var(--ctcm-muted);
  margin: 0 0 20px;
}}

.ctcm-button {{
  border: 0;
  border-radius: 6px;
  background: var(--ctcm-accent);
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  min-height: 42px;
  padding: 0 18px;
  text-decoration: none;
}}

.ctcm-button:disabled {{
  cursor: not-allowed;
  opacity: 0.48;
}}

.ctcm-section {{
  margin-top: 22px;
  background: var(--ctcm-surface);
  border: 1px solid var(--ctcm-line);
  border-radius: 8px;
  padding: 20px;
}}

.ctcm-section h2 {{
  margin: 0 0 14px;
  font-size: 1.25rem;
}}

.ctcm-tabs-list {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0 0 14px;
  padding: 0;
  list-style: none;
}}

.ctcm-tab-button {{
  border: 1px solid var(--ctcm-line);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  padding: 8px 12px;
}}

.ctcm-tab-button.is-active {{
  border-color: var(--ctcm-accent);
  color: var(--ctcm-accent);
  font-weight: 700;
}}

.ctcm-tab-panel {{ display: none; }}
.ctcm-tab-panel.is-active {{ display: block; }}

.ctcm-configurator-grid {{
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
}}

.ctcm-category {{
  border: 1px solid var(--ctcm-line);
  border-radius: 8px;
  margin-bottom: 12px;
  overflow: hidden;
}}

.ctcm-category-toggle {{
  width: 100%;
  min-height: 48px;
  border: 0;
  background: var(--ctcm-soft);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 14px;
  text-align: left;
  font-weight: 700;
}}

.ctcm-category-body {{
  display: none;
  padding: 12px;
}}

.ctcm-category.is-open .ctcm-category-body {{
  display: grid;
  gap: 10px;
}}

.ctcm-option {{
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  border: 1px solid var(--ctcm-line);
  border-radius: 8px;
  padding: 12px;
}}

.ctcm-option-image {{
  width: 72px;
  height: 72px;
  border: 1px solid var(--ctcm-line);
  border-radius: 6px;
  background: var(--ctcm-soft);
  display: grid;
  place-items: center;
  overflow: hidden;
}}

.ctcm-option-image img {{
  width: 100%;
  height: 100%;
  object-fit: contain;
}}

.ctcm-option-image-placeholder {{
  color: var(--ctcm-muted);
  font-size: 0.75rem;
  text-align: center;
}}

.ctcm-option-name {{
  display: block;
  font-weight: 700;
}}

.ctcm-option-meta {{
  color: var(--ctcm-muted);
  font-size: 0.92rem;
}}

.ctcm-qty {{
  display: grid;
  grid-template-columns: 34px 48px 34px;
  align-items: center;
}}

.ctcm-qty button,
.ctcm-qty input {{
  height: 34px;
  border: 1px solid var(--ctcm-line);
  text-align: center;
}}

.ctcm-qty button {{
  background: #fff;
  cursor: pointer;
  font-weight: 700;
}}

.ctcm-summary {{
  border: 1px solid var(--ctcm-line);
  border-radius: 8px;
  padding: 14px;
  position: sticky;
  top: 16px;
}}

.ctcm-summary-line {{
  display: flex;
  justify-content: space-between;
  gap: 10px;
  border-bottom: 1px solid var(--ctcm-line);
  padding: 8px 0;
}}

.ctcm-summary-total {{
  display: flex;
  justify-content: space-between;
  font-size: 1.1rem;
  font-weight: 700;
  padding: 12px 0;
}}

.ctcm-metafields dl {{
  display: grid;
  grid-template-columns: minmax(120px, 0.35fr) minmax(0, 1fr);
  gap: 8px 16px;
  margin: 0;
}}

.ctcm-metafields dt {{
  color: var(--ctcm-muted);
  font-weight: 700;
}}

.ctcm-toast {{
  color: var(--ctcm-accent);
  min-height: 24px;
  padding-top: 8px;
}}

@media (max-width: 780px) {{
  .ctcm-product,
  .ctcm-configurator-grid {{
    grid-template-columns: 1fr;
  }}

  .ctcm-option {{
    grid-template-columns: 56px minmax(0, 1fr);
  }}

  .ctcm-option-image {{
    width: 56px;
    height: 56px;
  }}

  .ctcm-qty {{
    grid-column: 1 / -1;
    justify-self: start;
  }}

  .ctcm-summary {{
    position: static;
  }}
}}
""".strip()
    return BlockResult(files={"assets/css/site.css": css})


def block_base_interactions(context: dict[str, Any]) -> BlockResult:
    js = r"""
(function () {
  function parsePrice(value) {
    var cleaned = String(value || "0").replace(/[$,]/g, "").trim();
    var parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function money(value) {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: "USD"
    }).format(parsePrice(value));
  }

  function updateConfigurator(root) {
    var lines = [];
    var configuredSubtotal = 0;
    var baseCost = parsePrice(root.getAttribute("data-base-cost"));
    var multiplier = parsePrice(root.getAttribute("data-price-multiplier") || "1") || 1;
    root.querySelectorAll("[data-ctcm-item-qty]").forEach(function (input) {
      var qty = parseInt(input.value || "0", 10);
      if (Number.isNaN(qty) || qty < 0) qty = 0;
      if (qty > 99) qty = 99;
      input.value = qty;
      if (!qty) return;
      var price = parsePrice(input.getAttribute("data-price") || "0");
      var name = input.getAttribute("data-name") || "Item";
      var lineTotal = price * qty;
      configuredSubtotal += lineTotal;
      lines.push('<div class="ctcm-summary-line"><span>' + name + ' x ' + qty + '</span><strong>' + money(lineTotal) + '</strong></div>');
    });
    var total = baseCost + (configuredSubtotal * multiplier);
    var lineHolder = root.querySelector("[data-ctcm-summary-lines]");
    var totalHolder = root.querySelector("[data-ctcm-summary-total]");
    var addButton = root.querySelector("[data-ctcm-add-selected]");
    var emptyText = root.getAttribute("data-empty-summary") || "No items selected yet.";
    lineHolder.innerHTML = lines.length ? lines.join("") : "<p>" + emptyText + "</p>";
    totalHolder.textContent = money(total);
    addButton.disabled = !lines.length && baseCost <= 0;
  }

  document.addEventListener("click", function (event) {
    var tabButton = event.target.closest("[data-ctcm-tab]");
    if (tabButton) {
      var group = tabButton.closest("[data-ctcm-tabs]");
      var target = tabButton.getAttribute("data-ctcm-tab");
      group.querySelectorAll("[data-ctcm-tab]").forEach(function (button) {
        button.classList.toggle("is-active", button === tabButton);
      });
      group.querySelectorAll("[data-ctcm-tab-panel]").forEach(function (panel) {
        panel.classList.toggle("is-active", panel.id === target);
      });
    }

    var categoryToggle = event.target.closest("[data-ctcm-category-toggle]");
    if (categoryToggle) {
      var category = categoryToggle.closest(".ctcm-category");
      category.classList.toggle("is-open");
    }

    var qtyButton = event.target.closest("[data-ctcm-qty]");
    if (qtyButton) {
      var wrapper = qtyButton.closest(".ctcm-qty");
      var input = wrapper.querySelector("input");
      var value = parseInt(input.value || "0", 10);
      var action = qtyButton.getAttribute("data-ctcm-qty");
      input.value = Math.max(0, Math.min(99, value + (action === "inc" ? 1 : -1)));
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }

    var addButton = event.target.closest("[data-ctcm-add-selected]");
    if (addButton) {
      var root = addButton.closest("[data-ctcm-configurator]");
      var toast = root.querySelector("[data-ctcm-toast]");
      var lines = root.querySelectorAll(".ctcm-summary-line");
      toast.textContent = lines.length ? "Selected items are ready for cart integration." : "Choose at least one item first.";
    }
  });

  document.addEventListener("input", function (event) {
    if (!event.target.matches("[data-ctcm-item-qty]")) return;
    var root = event.target.closest("[data-ctcm-configurator]");
    updateConfigurator(root);
  });

  document.addEventListener("change", function (event) {
    if (!event.target.matches("[data-ctcm-variant-select]")) return;
    var selected = event.target.options[event.target.selectedIndex];
    var targetId = event.target.getAttribute("data-ctcm-variant-select");
    var target = document.getElementById(targetId);
    if (!target) return;
    target.querySelectorAll("[data-ctcm-variant-fields]").forEach(function (panel) {
      panel.hidden = panel.getAttribute("data-ctcm-variant-fields") !== selected.value;
    });
  });

  document.querySelectorAll("[data-ctcm-configurator]").forEach(updateConfigurator);
})();
""".strip()
    return BlockResult(files={"assets/js/site.js": js})


def block_product_hero(context: dict[str, Any]) -> BlockResult:
    name = escape(str(context.get("product_name", "Product")))
    price = escape(str(context.get("product_price", "$0.00")))
    description = escape(str(context.get("product_description", "")))
    image = str(context.get("product_image", "")).strip()
    cta_text = escape(str(context.get("primary_cta_text", "Add Base Product")))
    cta_url = str(context.get("primary_cta_url", "")).strip()
    if image:
        media = f'<img src="{escape(image, quote=True)}" alt="{name}">'
    else:
        media = '<div class="ctcm-media-placeholder">Product image</div>'
    if cta_url:
        cta = f'<a class="ctcm-button" href="{escape(cta_url, quote=True)}">{cta_text}</a>'
    else:
        cta = f'<button class="ctcm-button" type="button">{cta_text}</button>'
    html = f"""
<section class="ctcm-product">
  <div class="ctcm-media">{media}</div>
  <div class="ctcm-product-info">
    <h1 class="ctcm-title">{name}</h1>
    <p class="ctcm-price">{price}</p>
    <p class="ctcm-description">{description}</p>
    {cta}
  </div>
</section>
""".strip()
    return BlockResult(sections={"product_hero": html})


def block_custom_field_tabs(context: dict[str, Any]) -> BlockResult:
    heading = escape(str(context.get("product_info_heading", "Product Information")))
    tabs = context.get("tabs") or []
    if not tabs:
        tabs = [
            {"title": "Details", "content": "Add product details here."},
            {"title": "Specifications", "content": "Add specifications here."},
        ]

    buttons = []
    panels = []
    for index, tab in enumerate(tabs):
        title = str(tab.get("title") or f"Tab {index + 1}")
        content = str(tab.get("content") or "")
        panel_id = f"ctcm-tab-{slugify(title)}-{index + 1}"
        active = " is-active" if index == 0 else ""
        buttons.append(
            f'<li><button class="ctcm-tab-button{active}" type="button" data-ctcm-tab="{panel_id}">{escape(title)}</button></li>'
        )
        panels.append(
            f'<div class="ctcm-tab-panel{active}" id="{panel_id}" data-ctcm-tab-panel>{escape(content)}</div>'
        )

    html = f"""
<section class="ctcm-section" data-ctcm-tabs>
  <h2>{heading}</h2>
  <ul class="ctcm-tabs-list">{''.join(buttons)}</ul>
  {''.join(panels)}
</section>
""".strip()
    return BlockResult(sections={"custom_field_tabs": html})


def block_configurator(context: dict[str, Any]) -> BlockResult:
    heading = escape(str(context.get("configurator_heading", "Product Configurator")))
    summary_heading = escape(str(context.get("summary_heading", "Your Selections")))
    empty_summary_text = escape(str(context.get("empty_summary_text", "No items selected yet.")))
    add_selected_text = escape(str(context.get("add_selected_text", "Add Selected")))
    base_cost = price_number(context.get("configurator_base_cost", 0))
    price_multiplier = price_number(context.get("configurator_price_multiplier", 1), 1) or 1
    categories = context.get("configurator_categories") or []
    if not categories:
        categories = [
            {
                "name": "Accessories",
                "items": [
                    {"name": "Starter Add-on", "price": 19.99, "variant": "Default"},
                    {"name": "Premium Add-on", "price": 39.99, "variant": "Default"},
                ],
            }
        ]

    category_html = []
    for cat_index, category in enumerate(categories):
        category_name = str(category.get("name") or f"Category {cat_index + 1}")
        options = []
        for item_index, item in enumerate(category.get("items") or []):
            item_name = str(item.get("name") or f"Item {item_index + 1}")
            variant = str(item.get("variant") or item.get("sku") or "")
            price_value = item.get("price", 0)
            numeric_price = price_number(price_value)
            image = str(item.get("image") or "").strip()
            option_id = f"ctcm-item-{cat_index + 1}-{item_index + 1}"
            if image:
                option_image = f'<img src="{escape(image, quote=True)}" alt="{escape(item_name, quote=True)}">'
            else:
                option_image = '<span class="ctcm-option-image-placeholder">Image</span>'
            options.append(f"""
        <div class="ctcm-option">
          <div class="ctcm-option-image">{option_image}</div>
          <div>
            <span class="ctcm-option-name">{escape(item_name)}</span>
            <span class="ctcm-option-meta">{escape(variant)} · {as_money(price_value)}</span>
          </div>
          <div class="ctcm-qty">
            <button type="button" data-ctcm-qty="dec" aria-label="Decrease">-</button>
            <input id="{option_id}" type="number" min="0" max="99" value="0" data-ctcm-item-qty data-name="{escape(item_name, quote=True)}" data-price="{numeric_price:.2f}">
            <button type="button" data-ctcm-qty="inc" aria-label="Increase">+</button>
          </div>
        </div>
""".rstrip())
        open_class = " is-open" if cat_index == 0 else ""
        category_html.append(f"""
      <div class="ctcm-category{open_class}">
        <button class="ctcm-category-toggle" type="button" data-ctcm-category-toggle>
          <span>{escape(category_name)}</span>
          <span>{len(options)} options</span>
        </button>
        <div class="ctcm-category-body">
          {''.join(options)}
        </div>
      </div>
""".rstrip())

    html = f"""
<section class="ctcm-section" data-ctcm-configurator data-base-cost="{base_cost:.2f}" data-price-multiplier="{price_multiplier:.4f}" data-empty-summary="{empty_summary_text}">
  <h2>{heading}</h2>
  <div class="ctcm-configurator-grid">
    <div>{''.join(category_html)}</div>
    <aside class="ctcm-summary">
      <h3>{summary_heading}</h3>
      <div data-ctcm-summary-lines><p>{empty_summary_text}</p></div>
      <div class="ctcm-summary-total"><span>Total</span><span data-ctcm-summary-total>$0.00</span></div>
      <button class="ctcm-button" type="button" data-ctcm-add-selected disabled>{add_selected_text}</button>
      <div class="ctcm-toast" data-ctcm-toast></div>
    </aside>
  </div>
</section>
""".strip()
    return BlockResult(sections={"configurator": html})


def block_metafields_panel(context: dict[str, Any]) -> BlockResult:
    heading = escape(str(context.get("metafields_heading", "Metafields")))
    variant_label = escape(str(context.get("variant_metafields_label", "Variant metafields")))
    base_fields = context.get("base_metafields") or []
    variant_fields = context.get("variant_metafields") or []

    if not base_fields:
        base_fields = [{"key": "Material", "value": "Example material"}]

    base_rows = "".join(
        f"<dt>{escape(str(field.get('key', 'Field')))}</dt><dd>{escape(str(field.get('value', '')))}</dd>"
        for field in base_fields
    )

    variant_select = ""
    variant_panels = ""
    if variant_fields:
        target_id = "ctcm-variant-metafields"
        options = []
        panels = []
        for index, variant in enumerate(variant_fields):
            variant_name = str(variant.get("variant") or f"Variant {index + 1}")
            value = slugify(variant_name)
            options.append(f'<option value="{escape(value, quote=True)}">{escape(variant_name)}</option>')
            rows = "".join(
                f"<dt>{escape(str(field.get('key', 'Field')))}</dt><dd>{escape(str(field.get('value', '')))}</dd>"
                for field in variant.get("fields", [])
            )
            hidden = "" if index == 0 else " hidden"
            panels.append(f'<dl data-ctcm-variant-fields="{escape(value, quote=True)}"{hidden}>{rows}</dl>')
        variant_select = f"""
  <label>
    {variant_label}
    <select data-ctcm-variant-select="{target_id}">{''.join(options)}</select>
  </label>
""".rstrip()
        variant_panels = f'<div id="{target_id}">{"".join(panels)}</div>'

    html = f"""
<section class="ctcm-section ctcm-metafields">
  <h2>{heading}</h2>
  <dl>{base_rows}</dl>
  {variant_select}
  {variant_panels}
</section>
""".strip()
    return BlockResult(sections={"metafields_panel": html})


def block_site_shell(context: dict[str, Any]) -> BlockResult:
    title = escape(str(context.get("site_title") or context.get("product_name") or "CTCM Product Page"))
    sections = context.get("_sections", {})
    ordered_sections = [
        sections.get("product_hero", ""),
        sections.get("custom_field_tabs", ""),
        sections.get("configurator", ""),
        sections.get("metafields_panel", ""),
    ]
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="assets/css/site.css">
</head>
<body>
  <main class="ctcm-page">
    {''.join(section for section in ordered_sections if section)}
  </main>
  <script src="assets/js/site.js"></script>
</body>
</html>
"""
    return BlockResult(files={"index.html": html})


def merge_result(context: dict[str, Any], result: BlockResult, output_files: dict[str, str]) -> None:
    """Merge a block result into shared assembly state."""

    if result.sections:
        context.setdefault("_sections", {}).update(result.sections)
    if result.files:
        output_files.update(result.files)


def assemble_site(context: dict[str, Any], block_names: list[str]) -> dict[str, str]:
    """Call blocks and return a mapping of relative output paths to file text."""

    output_files: dict[str, str] = {}
    for name in block_names:
        if name == "site_shell":
            continue
        merge_result(context, get_block_callable(name)(context), output_files)
    merge_result(context, block_site_shell(context), output_files)
    return output_files
