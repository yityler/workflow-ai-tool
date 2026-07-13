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
        "core_runtime": block_core_runtime,
        "gallery_main_image": block_gallery_main_image,
        "gallery_thumbnails": block_gallery_thumbnails,
        "gallery_caption": block_gallery_caption,
        "product_title": block_product_title,
        "product_price": block_product_price,
        "product_description": block_product_description,
        "primary_action": block_primary_action,
        "information_heading": block_information_heading,
        "information_tab_navigation": block_information_tab_navigation,
        "information_tab_panels": block_information_tab_panels,
        "addon_heading": block_addon_heading,
        "addon_catalog": block_addon_catalog,
        "addon_summary_heading": block_addon_summary_heading,
        "addon_selection_lines": block_addon_selection_lines,
        "addon_total": block_addon_total,
        "addon_submit_action": block_addon_submit_action,
        "product_metafields_heading": block_product_metafields_heading,
        "product_metafields_list": block_product_metafields_list,
        "variant_metafields_heading": block_variant_metafields_heading,
        "variant_selector": block_variant_selector,
        "variant_metafields_panels": block_variant_metafields_panels,
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

.ctcm-gallery {{ display: grid; gap: 10px; }}
.ctcm-gallery-main {{ aspect-ratio: 1 / 1; }}
.ctcm-gallery-thumbnails {{ display: flex; gap: 8px; overflow-x: auto; }}
.ctcm-gallery-thumbnail {{
  width: 64px;
  height: 64px;
  padding: 2px;
  border: 2px solid var(--ctcm-line);
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
  flex: 0 0 auto;
}}
.ctcm-gallery-thumbnail.is-active {{ border-color: var(--ctcm-accent); }}
.ctcm-gallery-caption {{ margin: 0; color: var(--ctcm-muted); font-size: 0.9rem; }}

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

    var galleryButton = event.target.closest("[data-ctcm-gallery-image]");
    if (galleryButton) {
      var gallery = galleryButton.closest("[data-ctcm-gallery]");
      var mainImage = gallery.querySelector("[data-ctcm-gallery-main]");
      mainImage.src = galleryButton.getAttribute("data-src");
      mainImage.alt = galleryButton.getAttribute("data-alt") || "Product image";
      var caption = gallery.querySelector("[data-ctcm-gallery-caption]");
      if (caption) caption.textContent = galleryButton.getAttribute("data-caption") || "";
      gallery.querySelectorAll("[data-ctcm-gallery-image]").forEach(function (button) {
        button.classList.toggle("is-active", button === galleryButton);
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


def normalized_product_images(context: dict[str, Any]) -> list[dict[str, str]]:
    """Normalize legacy and current gallery inputs for all gallery blocks."""

    name = escape(str(context.get("product_name", "Product")))
    images = context.get("product_images") or []
    if not images and context.get("product_image"):
        images = [{"url": context["product_image"], "alt": name}]
    normalized = []
    for index, image in enumerate(images):
        if isinstance(image, str):
            normalized.append({"url": image, "alt": f"{name} image {index + 1}"})
        else:
            normalized.append(image)
    return [image for image in normalized if image.get("url")]


def block_gallery_main_image(context: dict[str, Any]) -> BlockResult:
    images = normalized_product_images(context)
    if not images:
        html = '<div class="ctcm-media"><div class="ctcm-media-placeholder">Product image</div></div>'
    else:
        image = images[0]
        html = (f'<div class="ctcm-media ctcm-gallery-main"><img '
                f'src="{escape(str(image["url"]), quote=True)}" '
                f'alt="{escape(str(image.get("alt") or "Product image"), quote=True)}" '
                f'data-ctcm-gallery-main></div>')
    return BlockResult(sections={"gallery_main_image": html})


def block_gallery_thumbnails(context: dict[str, Any]) -> BlockResult:
    images = normalized_product_images(context)
    thumbnails = "".join(
        f'<button class="ctcm-gallery-thumbnail{" is-active" if index == 0 else ""}" type="button" '
        f'data-ctcm-gallery-image data-src="{escape(str(image["url"]), quote=True)}" '
        f'data-alt="{escape(str(image.get("alt") or "Product image"), quote=True)}" '
        f'data-caption="{escape(str(image.get("caption") or ""), quote=True)}" aria-label="Show image {index + 1}">'
        f'<img src="{escape(str(image["url"]), quote=True)}" alt=""></button>'
        for index, image in enumerate(images)
    )
    html = f'<div class="ctcm-gallery-thumbnails" aria-label="Product image thumbnails">{thumbnails}</div>'
    return BlockResult(sections={"gallery_thumbnails": html})


def block_gallery_caption(context: dict[str, Any]) -> BlockResult:
    images = normalized_product_images(context)
    caption = str(images[0].get("caption") or "") if images else ""
    html = f'<p class="ctcm-gallery-caption" data-ctcm-gallery-caption>{escape(caption)}</p>'
    return BlockResult(sections={"gallery_caption": html})


def block_product_title(context: dict[str, Any]) -> BlockResult:
    name = escape(str(context.get("product_name", "Product")))
    return BlockResult(sections={"product_title": f'<h1 class="ctcm-title">{name}</h1>'})


def block_product_price(context: dict[str, Any]) -> BlockResult:
    price = escape(str(context.get("product_price", "$0.00")))
    return BlockResult(sections={"product_price": f'<p class="ctcm-price">{price}</p>'})


def block_product_description(context: dict[str, Any]) -> BlockResult:
    description = escape(str(context.get("product_description", "")))
    return BlockResult(sections={"product_description": f'<p class="ctcm-description">{description}</p>'})


def block_primary_action(context: dict[str, Any]) -> BlockResult:
    cta_text = escape(str(context.get("primary_cta_text", "Add Base Product")))
    cta_url = str(context.get("primary_cta_url", "")).strip()
    if cta_url:
        cta = f'<a class="ctcm-button" href="{escape(cta_url, quote=True)}">{cta_text}</a>'
    else:
        cta = f'<button class="ctcm-button" type="button">{cta_text}</button>'
    return BlockResult(sections={"primary_action": cta})


def normalized_tabs(context: dict[str, Any]) -> list[dict[str, Any]]:
    tabs = context.get("tabs") or []
    if not tabs:
        tabs = [
            {"title": "Details", "content": "Add product details here."},
            {"title": "Specifications", "content": "Add specifications here."},
        ]

    return tabs


def block_information_heading(context: dict[str, Any]) -> BlockResult:
    heading = escape(str(context.get("product_info_heading", "Product Information")))
    return BlockResult(sections={"information_heading": f"<h2>{heading}</h2>"})


def block_information_tab_navigation(context: dict[str, Any]) -> BlockResult:
    buttons = []
    for index, tab in enumerate(normalized_tabs(context)):
        title = str(tab.get("title") or f"Tab {index + 1}")
        panel_id = f"ctcm-tab-{slugify(title)}-{index + 1}"
        active = " is-active" if index == 0 else ""
        buttons.append(
            f'<li><button class="ctcm-tab-button{active}" type="button" data-ctcm-tab="{panel_id}">{escape(title)}</button></li>'
        )
    html = f'<ul class="ctcm-tabs-list">{"".join(buttons)}</ul>'
    return BlockResult(sections={"information_tab_navigation": html})


def block_information_tab_panels(context: dict[str, Any]) -> BlockResult:
    panels = []
    for index, tab in enumerate(normalized_tabs(context)):
        title = str(tab.get("title") or f"Tab {index + 1}")
        content = str(tab.get("content") or "")
        panel_id = f"ctcm-tab-{slugify(title)}-{index + 1}"
        active = " is-active" if index == 0 else ""
        panels.append(
            f'<div class="ctcm-tab-panel{active}" id="{panel_id}" data-ctcm-tab-panel>{escape(content)}</div>'
        )
    return BlockResult(sections={"information_tab_panels": "".join(panels)})


def block_addon_heading(context: dict[str, Any]) -> BlockResult:
    heading = escape(str(context.get("configurator_heading", "Product Configurator")))
    return BlockResult(sections={"addon_heading": f"<h2>{heading}</h2>"})


def block_addon_catalog(context: dict[str, Any]) -> BlockResult:
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

    return BlockResult(sections={"addon_catalog": "".join(category_html)})


def block_addon_summary_heading(context: dict[str, Any]) -> BlockResult:
    summary_heading = escape(str(context.get("summary_heading", "Your Selections")))
    return BlockResult(sections={"addon_summary_heading": f"<h3>{summary_heading}</h3>"})


def block_addon_selection_lines(context: dict[str, Any]) -> BlockResult:
    empty_summary_text = escape(str(context.get("empty_summary_text", "No items selected yet.")))
    html = f'<div data-ctcm-summary-lines><p>{empty_summary_text}</p></div>'
    return BlockResult(sections={"addon_selection_lines": html})


def block_addon_total(context: dict[str, Any]) -> BlockResult:
    label = escape(str(context.get("addon_total_label", "Total")))
    html = f'<div class="ctcm-summary-total"><span>{label}</span><span data-ctcm-summary-total>$0.00</span></div>'
    return BlockResult(sections={"addon_total": html})


def block_addon_submit_action(context: dict[str, Any]) -> BlockResult:
    add_selected_text = escape(str(context.get("add_selected_text", "Add Selected")))
    html = (f'<button class="ctcm-button" type="button" data-ctcm-add-selected disabled>{add_selected_text}</button>'
            '<div class="ctcm-toast" data-ctcm-toast></div>')
    return BlockResult(sections={"addon_submit_action": html})


def block_product_metafields_heading(context: dict[str, Any]) -> BlockResult:
    heading = escape(str(context.get("metafields_heading", "Metafields")))
    return BlockResult(sections={"product_metafields_heading": f"<h2>{heading}</h2>"})


def block_product_metafields_list(context: dict[str, Any]) -> BlockResult:
    base_fields = context.get("base_metafields") or []

    if not base_fields:
        base_fields = [{"key": "Material", "value": "Example material"}]

    base_rows = "".join(
        f"<dt>{escape(str(field.get('key', 'Field')))}</dt><dd>{escape(str(field.get('value', '')))}</dd>"
        for field in base_fields
    )

    return BlockResult(sections={"product_metafields_list": f"<dl>{base_rows}</dl>"})


def block_variant_metafields_heading(context: dict[str, Any]) -> BlockResult:
    heading = escape(str(context.get("variant_metafields_heading", "Variant Metafields")))
    return BlockResult(sections={"variant_metafields_heading": f"<h2>{heading}</h2>"})


def block_variant_selector(context: dict[str, Any]) -> BlockResult:
    variant_label = escape(str(context.get("variant_metafields_label", "Variant metafields")))
    variant_fields = context.get("variant_metafields") or []
    if variant_fields:
        target_id = "ctcm-variant-metafields"
        options = []
        for index, variant in enumerate(variant_fields):
            variant_name = str(variant.get("variant") or f"Variant {index + 1}")
            value = slugify(variant_name)
            options.append(f'<option value="{escape(value, quote=True)}">{escape(variant_name)}</option>')
        variant_select = f"""
  <label>
    {variant_label}
    <select data-ctcm-variant-select="{target_id}">{''.join(options)}</select>
  </label>
""".rstrip()
    else:
        variant_select = ""
    return BlockResult(sections={"variant_selector": variant_select})


def block_variant_metafields_panels(context: dict[str, Any]) -> BlockResult:
    panels = []
    for index, variant in enumerate(context.get("variant_metafields") or []):
        variant_name = str(variant.get("variant") or f"Variant {index + 1}")
        value = slugify(variant_name)
        rows = "".join(
            f"<dt>{escape(str(field.get('key', 'Field')))}</dt><dd>{escape(str(field.get('value', '')))}</dd>"
            for field in variant.get("fields", [])
        )
        hidden = "" if index == 0 else " hidden"
        panels.append(f'<dl data-ctcm-variant-fields="{escape(value, quote=True)}"{hidden}>{rows}</dl>')
    html = f'<div id="ctcm-variant-metafields">{"".join(panels)}</div>'
    return BlockResult(sections={"variant_metafields_panels": html})


def block_core_runtime(context: dict[str, Any]) -> BlockResult:
    title = escape(str(context.get("site_title") or context.get("product_name") or "CTCM Product Page"))
    sections = context.get("_sections", {})
    gallery_parts = "".join(sections.get(name, "") for name in (
        "gallery_main_image", "gallery_thumbnails", "gallery_caption"
    ))
    product_media = f'<div class="ctcm-gallery" data-ctcm-gallery>{gallery_parts}</div>' if gallery_parts else ""
    product_info = "".join(sections.get(name, "") for name in (
        "product_title", "product_price", "product_description", "primary_action"
    ))
    product_section = ""
    if product_media or product_info:
        product_section = f'<section class="ctcm-product">{product_media}<div class="ctcm-product-info">{product_info}</div></section>'
    information_parts = "".join(sections.get(name, "") for name in (
        "information_heading", "information_tab_navigation", "information_tab_panels"
    ))
    information_section = (f'<section class="ctcm-section" data-ctcm-tabs>{information_parts}</section>'
                           if information_parts else "")
    addon_options = "".join(sections.get(name, "") for name in ("addon_heading", "addon_catalog"))
    if addon_options:
        addon_options = f'<div class="ctcm-addon-options">{addon_options}</div>'
    addon_summary = "".join(sections.get(name, "") for name in (
        "addon_summary_heading", "addon_selection_lines", "addon_total", "addon_submit_action"
    ))
    if addon_summary:
        addon_summary = f'<aside class="ctcm-summary">{addon_summary}</aside>'
    addon_section = ""
    if addon_options or addon_summary:
        base_cost = price_number(context.get("configurator_base_cost", 0))
        multiplier = price_number(context.get("configurator_price_multiplier", 1), 1) or 1
        empty = escape(str(context.get("empty_summary_text", "No items selected yet.")), quote=True)
        addon_section = (f'<section class="ctcm-section" data-ctcm-configurator data-base-cost="{base_cost:.2f}" '
                         f'data-price-multiplier="{multiplier:.4f}" data-empty-summary="{empty}">'
                         f'<div class="ctcm-configurator-grid">{addon_options}{addon_summary}</div></section>')
    ordered_sections = [
        product_section,
        information_section,
        addon_section,
        (f'<section class="ctcm-section ctcm-metafields">'
         f'{sections.get("product_metafields_heading", "")}{sections.get("product_metafields_list", "")}</section>'
         if sections.get("product_metafields_heading") or sections.get("product_metafields_list") else ""),
        (f'<section class="ctcm-section ctcm-metafields">'
         f'{sections.get("variant_metafields_heading", "")}{sections.get("variant_selector", "")}'
         f'{sections.get("variant_metafields_panels", "")}</section>'
         if any(sections.get(name) for name in ("variant_metafields_heading", "variant_selector", "variant_metafields_panels")) else ""),
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
    files = {"index.html": html}
    files.update(block_base_styles(context).files or {})
    files.update(block_base_interactions(context).files or {})
    return BlockResult(files=files)


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
        if name == "core_runtime":
            continue
        merge_result(context, get_block_callable(name)(context), output_files)
    merge_result(context, block_core_runtime(context), output_files)
    return output_files
