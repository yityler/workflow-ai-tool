"""Interactive CTCM webpage generator.

This caller uses the block functions in ../CTCM-V1.0-blockFunctions to create a
new product display webpage in ../CTCM-V1.0-pageHolder/CTCM-SX.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
OVERALL_DIR = CURRENT_DIR.parent
BLOCK_DIR = OVERALL_DIR / "CTCM-V1.0-blockFunctions"
PAGE_HOLDER_DIR = OVERALL_DIR / "CTCM-V1.0-pageHolder"

sys.path.insert(0, str(BLOCK_DIR))

import ctcm_blocks  # noqa: E402


def ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default not in (None, "") else ""
    value = input(f"{prompt}{suffix}: ").strip()
    if value:
        return value
    return default or ""


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    default_label = "Y/n" if default else "y/N"
    value = input(f"{prompt} ({default_label}): ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes"}


def next_site_dir() -> Path:
    PAGE_HOLDER_DIR.mkdir(parents=True, exist_ok=True)
    highest = 0
    pattern = re.compile(r"^CTCM-S(\d+)$")
    for path in PAGE_HOLDER_DIR.iterdir():
        if not path.is_dir():
            continue
        match = pattern.match(path.name)
        if match:
            highest = max(highest, int(match.group(1)))
    return PAGE_HOLDER_DIR / f"CTCM-S{highest + 1}"


def parse_price(value: str) -> str:
    value = value.strip()
    if not value:
        return "$0.00"
    if value.startswith("$"):
        return value
    try:
        return f"${float(value):,.2f}"
    except ValueError:
        return value


def internal_price(value: str, default: str = "0.00") -> str:
    value = str(value or "").replace("$", "").replace(",", "").strip()
    if not value:
        return default
    try:
        return f"{float(value):.2f}"
    except ValueError:
        return default


def internal_multiplier(value: str, default: str = "1") -> str:
    value = str(value or "").replace(",", "").strip()
    if not value:
        return default
    try:
        return f"{float(value):g}"
    except ValueError:
        return default


def collect_required_inputs(context: dict[str, Any]) -> None:
    print("\nRequired site inputs")
    context["site_title"] = ask("Site title", "Generated Product Page")
    context["product_name"] = ask("Product name", "Example Product")
    context["product_price"] = parse_price(ask("Product price", "$99.00"))
    context["product_description"] = ask(
        "Short product description",
        "A configurable product display page generated from CTCM block functions.",
    )
    context["primary_cta_text"] = ask("Primary button text", "Add Base Product")
    context["primary_cta_url"] = ask("Primary button link URL", "")
    context["accent_color"] = ask("Accent color", "#0f766e")
    context["product_info_heading"] = "Product Information"
    context["configurator_heading"] = "Product Configurator"
    context["summary_heading"] = "Your Selections"
    context["empty_summary_text"] = "No items selected yet."
    context["add_selected_text"] = "Add Selected"
    context["configurator_base_cost"] = internal_price(context["product_price"])
    context["configurator_price_multiplier"] = "1"
    context["metafields_heading"] = "Metafields"
    context["variant_metafields_label"] = "Variant metafields"
    context["variant_metafields_heading"] = "Variant Metafields"
    context["addon_total_label"] = "Total"


def collect_gallery(context: dict[str, Any]) -> None:
    print("\nProduct gallery")
    count_text = ask("How many product images?", "1")
    try:
        count = max(0, int(count_text))
    except ValueError:
        count = 1
    images = []
    for index in range(count):
        url = ask(f"Image {index + 1} URL or local path", "")
        alt = ask(f"Image {index + 1} alt text", f"{context.get('product_name', 'Product')} image {index + 1}")
        caption = ask(f"Image {index + 1} caption", "")
        if url:
            images.append({"url": url, "alt": alt, "caption": caption})
    context["product_images"] = images
    context["product_image"] = images[0]["url"] if images else ""


def collect_tabs(context: dict[str, Any]) -> None:
    tabs = []
    print("\nCustom field tabs")
    count_text = ask("How many tabs?", "2")
    try:
        count = max(0, int(count_text))
    except ValueError:
        count = 2
    for index in range(count):
        title = ask(f"Tab {index + 1} title", "Details" if index == 0 else "Specifications")
        content = ask(f"Tab {index + 1} content", "Add product information here.")
        tabs.append({"title": title, "content": content})
    context["tabs"] = tabs


def collect_configurator(context: dict[str, Any]) -> None:
    categories = []
    print("\nConfigurator categories")
    count_text = ask("How many configurator categories?", "1")
    try:
        category_count = max(0, int(count_text))
    except ValueError:
        category_count = 1

    for category_index in range(category_count):
        category_name = ask(f"Category {category_index + 1} name", "Accessories")
        item_count_text = ask(f"How many items in {category_name}?", "2")
        try:
            item_count = max(0, int(item_count_text))
        except ValueError:
            item_count = 2

        items = []
        for item_index in range(item_count):
            item_name = ask(f"Item {item_index + 1} name", f"{category_name} Option {item_index + 1}")
            variant = ask(f"Item {item_index + 1} variant/SKU label", "Default")
            price = internal_price(ask(f"Item {item_index + 1} price", "19.99"), "19.99")
            image = ask(f"Item {item_index + 1} image URL or local path", "")
            items.append({"name": item_name, "variant": variant, "price": price, "image": image})
        categories.append({"name": category_name, "items": items})
    context["configurator_categories"] = categories


def collect_metafields(context: dict[str, Any]) -> None:
    print("\nBase product metafields")
    base_fields = []
    base_count_text = ask("How many base metafields?", "2")
    try:
        base_count = max(0, int(base_count_text))
    except ValueError:
        base_count = 2
    for index in range(base_count):
        key = ask(f"Base metafield {index + 1} key", "Material" if index == 0 else "Warranty")
        value = ask(f"Base metafield {index + 1} value", "Example value")
        base_fields.append({"key": key, "value": value})
    context["base_metafields"] = base_fields

    variant_fields = []
    if ask_yes_no("Add variant-specific metafields?", False):
        variant_count_text = ask("How many variants?", "1")
        try:
            variant_count = max(0, int(variant_count_text))
        except ValueError:
            variant_count = 1
        for variant_index in range(variant_count):
            variant_name = ask(f"Variant {variant_index + 1} name", f"Variant {variant_index + 1}")
            field_count_text = ask(f"How many fields for {variant_name}?", "2")
            try:
                field_count = max(0, int(field_count_text))
            except ValueError:
                field_count = 2
            fields = []
            for field_index in range(field_count):
                key = ask(f"{variant_name} field {field_index + 1} key", "SKU")
                value = ask(f"{variant_name} field {field_index + 1} value", "Example")
                fields.append({"key": key, "value": value})
            variant_fields.append({"variant": variant_name, "fields": fields})
    context["variant_metafields"] = variant_fields


def choose_blocks(manifest: dict[str, Any]) -> list[str]:
    required = [block["name"] for block in manifest["blocks"] if block.get("required")]
    selected = list(required)

    print("\nRequired blocks will be called immediately:")
    for name in required:
        print(f"  - {name}")

    optional_blocks = [block for block in manifest["blocks"] if not block.get("required")]
    print("\nOptional blocks")
    for block in optional_blocks:
        default_blocks = {
            "gallery_main_image", "gallery_thumbnails", "gallery_caption",
            "product_title", "product_price", "product_description", "primary_action",
            "information_heading", "information_tab_navigation", "information_tab_panels",
            "addon_heading", "addon_catalog", "addon_summary_heading",
            "addon_selection_lines", "addon_total", "addon_submit_action",
            "product_metafields_heading", "product_metafields_list",
            "variant_metafields_heading", "variant_selector", "variant_metafields_panels",
        }
        include = ask_yes_no(f"Include {block['name']}? {block['summary']}", block["name"] in default_blocks)
        if include:
            selected.append(block["name"])

    block_by_name = {block["name"]: block for block in manifest["blocks"]}
    pending = list(selected)
    while pending:
        name = pending.pop()
        for dependency in block_by_name[name].get("dependencies", []):
            if dependency not in selected:
                selected.append(dependency)
                pending.append(dependency)

    return selected


def collect_optional_inputs(context: dict[str, Any], selected_blocks: list[str]) -> None:
    gallery_blocks = {"gallery_main_image", "gallery_thumbnails", "gallery_caption"}
    if gallery_blocks.intersection(selected_blocks):
        collect_gallery(context)
    if "information_tab_navigation" in selected_blocks or "information_tab_panels" in selected_blocks:
        collect_tabs(context)
    if "addon_catalog" in selected_blocks:
        collect_configurator(context)
    metafield_blocks = {"product_metafields_list", "variant_selector", "variant_metafields_panels"}
    if metafield_blocks.intersection(selected_blocks):
        collect_metafields(context)


BACKEND_SERVER = r'''"""Local content backend for this generated CTCM site.

Run from this folder with:
    python3 backend/server.py

Then open:
    http://127.0.0.1:8765

This backend edits text, links, and image URLs/paths only. Layout, fonts, font sizes, button
placement, and other styling remain controlled by the block functions.
"""

from __future__ import annotations

import json
import mimetypes
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote


SITE_DIR = Path(__file__).resolve().parents[1]
OVERALL_DIR = SITE_DIR.parents[1]
BLOCK_DIR = OVERALL_DIR / "CTCM-V1.0-blockFunctions"
CONFIG_PATH = SITE_DIR / "site_config.json"
CONTENT_PATH = SITE_DIR / "content.json"

sys.path.insert(0, str(BLOCK_DIR))

import ctcm_blocks  # noqa: E402


TEXT_TOP_LEVEL = {
    "site_title": "Site title",
    "product_name": "Product name",
    "product_price": "Product price",
    "product_description": "Product description",
    "primary_cta_text": "Primary button text",
    "product_info_heading": "Product information heading",
    "configurator_heading": "Configurator heading",
    "summary_heading": "Summary heading",
    "empty_summary_text": "Empty summary text",
    "add_selected_text": "Add selected button text",
    "metafields_heading": "Metafields heading",
    "variant_metafields_label": "Variant metafields label",
    "variant_metafields_heading": "Variant metafields heading",
    "addon_total_label": "Add-on total label",
}

PRICING_TOP_LEVEL = {
    "configurator_base_cost": "Base item cost before configurations",
    "configurator_price_multiplier": "Configuration price multiplier",
}

LINK_TOP_LEVEL = {
    "primary_cta_url": "Primary button link URL",
}

TEXT_DEFAULTS = {
    "product_info_heading": "Product Information",
    "configurator_heading": "Product Configurator",
    "summary_heading": "Your Selections",
    "empty_summary_text": "No items selected yet.",
    "add_selected_text": "Add Selected",
    "metafields_heading": "Metafields",
    "variant_metafields_label": "Variant metafields",
    "variant_metafields_heading": "Variant Metafields",
    "addon_total_label": "Total",
    "configurator_base_cost": "0.00",
    "configurator_price_multiplier": "1",
}


def normalize_price(value, default="0.00"):
    cleaned = str(value or "").replace("$", "").replace(",", "").strip()
    if not cleaned:
        return default
    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return default


def normalize_multiplier(value, default="1"):
    cleaned = str(value or "").replace(",", "").strip()
    if not cleaned:
        return default
    try:
        return f"{float(cleaned):g}"
    except ValueError:
        return default


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_inputs() -> dict:
    config = read_json(CONFIG_PATH)
    return config.get("inputs", {})


def set_nested(inputs: dict, path: list, value: str) -> None:
    target = inputs
    for part in path[:-1]:
        if isinstance(part, int):
            target = target[part]
        else:
            target = target[part]
    target[path[-1]] = value


def field(path: list, label: str, value: str, kind: str = "text") -> dict:
    return {
        "id": ".".join(str(part) for part in path),
        "path": path,
        "label": label,
        "value": "" if value is None else str(value),
        "kind": kind,
    }


def build_content_model() -> dict:
    inputs = get_inputs()
    fields = []

    for key, label in TEXT_TOP_LEVEL.items():
        fields.append(field([key], label, inputs.get(key, TEXT_DEFAULTS.get(key, "")), "text"))
    for key, label in PRICING_TOP_LEVEL.items():
        kind = "multiplier" if key.endswith("multiplier") else "price"
        default = TEXT_DEFAULTS.get(key, "1" if kind == "multiplier" else "0.00")
        value = inputs.get(key, default)
        if kind == "multiplier":
            value = normalize_multiplier(value, default)
        else:
            value = normalize_price(value, default)
        fields.append(field([key], label, value, kind))
    for key, label in LINK_TOP_LEVEL.items():
        fields.append(field([key], label, inputs.get(key, ""), "link"))
    for index, image in enumerate(inputs.get("product_images", [])):
        if isinstance(image, str):
            image = {"url": image, "alt": "", "caption": ""}
        fields.append(field(["product_images", index, "url"], f"Gallery image {index + 1} URL/path", image.get("url", ""), "image"))
        fields.append(field(["product_images", index, "alt"], f"Gallery image {index + 1} alt text", image.get("alt", ""), "text"))
        fields.append(field(["product_images", index, "caption"], f"Gallery image {index + 1} caption", image.get("caption", ""), "text"))

    for index, tab in enumerate(inputs.get("tabs", [])):
        fields.append(field(["tabs", index, "title"], f"Tab {index + 1} title", tab.get("title", ""), "text"))
        fields.append(field(["tabs", index, "content"], f"Tab {index + 1} content", tab.get("content", ""), "long_text"))

    for category_index, category in enumerate(inputs.get("configurator_categories", [])):
        fields.append(field(["configurator_categories", category_index, "name"], f"Configurator category {category_index + 1} name", category.get("name", ""), "text"))
        for item_index, item in enumerate(category.get("items", [])):
            prefix = f"{category.get('name', 'Category')} item {item_index + 1}"
            fields.append(field(["configurator_categories", category_index, "items", item_index, "name"], f"{prefix} name", item.get("name", ""), "text"))
            fields.append(field(["configurator_categories", category_index, "items", item_index, "variant"], f"{prefix} variant/SKU label", item.get("variant", ""), "text"))
            fields.append(field(["configurator_categories", category_index, "items", item_index, "price"], f"{prefix} internal price", normalize_price(item.get("price", "")), "price"))
            fields.append(field(["configurator_categories", category_index, "items", item_index, "image"], f"{prefix} image URL/path", item.get("image", ""), "image"))

    for index, item in enumerate(inputs.get("base_metafields", [])):
        fields.append(field(["base_metafields", index, "key"], f"Base metafield {index + 1} key", item.get("key", ""), "text"))
        fields.append(field(["base_metafields", index, "value"], f"Base metafield {index + 1} value", item.get("value", ""), "text"))

    for variant_index, variant in enumerate(inputs.get("variant_metafields", [])):
        fields.append(field(["variant_metafields", variant_index, "variant"], f"Variant {variant_index + 1} name", variant.get("variant", ""), "text"))
        for field_index, item in enumerate(variant.get("fields", [])):
            prefix = f"{variant.get('variant', 'Variant')} metafield {field_index + 1}"
            fields.append(field(["variant_metafields", variant_index, "fields", field_index, "key"], f"{prefix} key", item.get("key", ""), "text"))
            fields.append(field(["variant_metafields", variant_index, "fields", field_index, "value"], f"{prefix} value", item.get("value", ""), "text"))

    model = {
        "notice": "Editable content only: text, links, and image URLs/paths. Styling and layout are locked in the block functions.",
        "fields": fields,
        "selected_blocks": read_json(CONFIG_PATH).get("selected_blocks", []),
    }
    write_json(CONTENT_PATH, model)
    return model


def rebuild_site() -> None:
    config = read_json(CONFIG_PATH)
    inputs = config.get("inputs", {})
    selected_blocks = config.get("selected_blocks", [])
    files = ctcm_blocks.assemble_site(inputs, selected_blocks)
    for relative_path, content in files.items():
        if relative_path == "site_config.json":
            continue
        output_path = SITE_DIR / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
    write_json(CONFIG_PATH, config)
    build_content_model()


def save_fields(updated_fields: list) -> dict:
    config = read_json(CONFIG_PATH)
    inputs = config.setdefault("inputs", {})
    for item in updated_fields:
        path = item.get("path")
        if isinstance(path, list):
            value = item.get("value", "")
            field_id = ".".join(str(part) for part in path)
            if item.get("kind") == "price" or field_id.endswith(".price"):
                value = normalize_price(value)
            elif item.get("kind") == "multiplier" or field_id == "configurator_price_multiplier":
                value = normalize_multiplier(value)
            set_nested(inputs, path, value)
    write_json(CONFIG_PATH, config)
    rebuild_site()
    return build_content_model()


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/content":
            self.send_json(build_content_model())
            return
        if self.path == "/site":
            self.send_response(302)
            self.send_header("Location", "/index.html")
            self.end_headers()
            return

        relative = "backend/admin.html" if self.path in {"/", "/admin"} else unquote(self.path.lstrip("/"))
        target = SITE_DIR / relative
        if not target.exists() or not target.is_file():
            self.send_error(404)
            return
        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/content":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        model = save_fields(payload.get("fields", []))
        self.send_json({"ok": True, "content": model})


def main() -> None:
    build_content_model()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("CTCM content backend running at http://127.0.0.1:8765")
    print("Edit text, links, and image URLs/paths there, then use the View site link.")
    server.serve_forever()


if __name__ == "__main__":
    main()
'''


BACKEND_ADMIN_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>CTCM Visual Backend</title>
  <link rel="stylesheet" href="/assets/css/site.css">
  <link rel="stylesheet" href="/backend/admin.css">
</head>
<body>
  <header class="admin-toolbar">
    <div>
      <strong>Visual Backend</strong>
      <span>Edit text in place. Drop images onto picture slots.</span>
    </div>
    <div class="admin-toolbar-actions">
      <button id="save-button" type="button">Save and rebuild</button>
      <a href="/index.html" target="_blank">View site</a>
      <span id="status"></span>
    </div>
  </header>
  <main class="ctcm-page admin-preview-shell">
    <div class="admin-note">
      <strong>Editing mode:</strong> text and pictures are editable; styling, font size, and layout controls are locked.
    </div>
    <div id="visual-editor"></div>
  </main>
  <script src="/assets/js/site.js"></script>
  <script src="/backend/admin.js"></script>
</body>
</html>
'''


BACKEND_ADMIN_CSS = r'''body {
  padding-top: 72px;
}

.admin-toolbar {
  position: fixed;
  z-index: 50;
  top: 0;
  right: 0;
  left: 0;
  min-height: 72px;
  background: #17202a;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 12px 18px;
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.18);
}

.admin-toolbar strong {
  display: block;
}

.admin-toolbar span {
  color: #cbd5e1;
  font-size: 0.9rem;
}

.admin-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.admin-toolbar button,
.admin-toolbar a {
  border: 0;
  border-radius: 6px;
  background: #2563eb;
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  min-height: 38px;
  padding: 0 13px;
  text-decoration: none;
  font-weight: 700;
}

#status {
  min-width: 112px;
}

.admin-preview-shell {
  padding-top: 22px;
}

.admin-note {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  color: #1e3a8a;
  margin-bottom: 18px;
  padding: 12px 14px;
}

[contenteditable="true"] {
  outline: 2px dashed transparent;
  outline-offset: 3px;
  border-radius: 4px;
  cursor: text;
}

[contenteditable="true"]:hover,
[contenteditable="true"]:focus {
  outline-color: #2563eb;
  background: rgba(37, 99, 235, 0.08);
}

.admin-image-edit {
  position: relative;
  cursor: pointer;
  outline: 2px dashed rgba(37, 99, 235, 0.55);
  outline-offset: -6px;
}

.admin-image-edit img,
.admin-image-edit .ctcm-media-placeholder,
.admin-image-edit .ctcm-option-image-placeholder {
  pointer-events: none;
}

.admin-image-edit.is-selected,
.admin-image-edit.is-drag-over {
  outline-color: #0f766e;
  box-shadow: 0 0 0 4px rgba(15, 118, 110, 0.18);
}

.admin-image-help {
  position: absolute;
  right: 8px;
  bottom: 8px;
  border-radius: 999px;
  background: rgba(23, 32, 42, 0.78);
  color: #fff;
  font-size: 0.78rem;
  padding: 4px 8px;
  pointer-events: none;
}

.admin-link-edit {
  display: grid;
  gap: 6px;
  margin-top: 10px;
}

.admin-link-edit label {
  color: #657080;
  font-size: 0.82rem;
  font-weight: 700;
}

.admin-link-edit input {
  width: min(100%, 420px);
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  font: inherit;
  padding: 8px 10px;
}

@media (max-width: 780px) {
  body {
    padding-top: 118px;
  }

  .admin-toolbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
'''


BACKEND_ADMIN_JS = r'''let fields = [];
let fieldMap = new Map();
let selectedBlocks = new Set();
let selectedImageFieldId = null;
const IMAGE_OUTPUT_TYPE = "image/webp";
const IMAGE_OUTPUT_QUALITY = 0.92;

function byId(id) {
  return fieldMap.get(id) || { id, value: "", path: [] };
}

function html(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function money(value) {
  const raw = String(value || "").trim();
  if (raw.startsWith("$")) return html(raw);
  const number = Number(raw);
  if (Number.isNaN(number)) return html(raw);
  return new Intl.NumberFormat(undefined, { style: "currency", currency: "USD" }).format(number);
}

function parsePrice(value, fallback = 0) {
  const cleaned = String(value || "").replace(/[$,]/g, "").trim();
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function normalizePrice(value, fallback = "0.00") {
  return parsePrice(value, Number(fallback || 0)).toFixed(2);
}

function normalizeMultiplier(value, fallback = "1") {
  const parsed = parsePrice(value, Number(fallback || 1));
  return Number.isFinite(parsed) && parsed > 0 ? String(parsed) : fallback;
}

function editable(id, tag, className = "") {
  const field = byId(id);
  return `<${tag} class="${className}" contenteditable="true" data-edit-text="${field.id}">${html(field.value)}</${tag}>`;
}

function editablePrice(id, tag, className = "") {
  const field = byId(id);
  return `<${tag} class="${className}" contenteditable="true" data-edit-price="${field.id}">${money(field.value)}</${tag}>`;
}

function imageSlot(id, className, altText) {
  const field = byId(id);
  const value = String(field.value || "").trim();
  const image = value
    ? `<img src="${html(value)}" alt="${html(altText || "Image")}">`
    : `<div class="${className.includes("ctcm-media") ? "ctcm-media-placeholder" : "ctcm-option-image-placeholder"}">Image</div>`;
  return `<div class="${className} admin-image-edit" data-edit-image="${field.id}" data-image-output-type="${IMAGE_OUTPUT_TYPE}">${image}<span class="admin-image-help">Drop image here</span></div>`;
}

function linkInput(id, label) {
  const field = byId(id);
  return `<div class="admin-link-edit">
    <label>${html(label)}</label>
    <input type="url" value="${html(field.value)}" data-edit-link="${field.id}">
  </div>`;
}

function pricingInput(id, label, kind = "price") {
  const field = byId(id);
  const value = kind === "multiplier" ? normalizeMultiplier(field.value) : normalizePrice(field.value);
  return `<div class="admin-link-edit">
    <label>${html(label)}</label>
    <input type="number" step="${kind === "multiplier" ? "0.01" : "0.01"}" min="${kind === "multiplier" ? "0.01" : "0"}" value="${html(value)}" data-edit-pricing="${field.id}" data-pricing-kind="${kind}">
  </div>`;
}

function getItems(prefix) {
  return fields
    .filter((field) => field.id.startsWith(prefix))
    .sort((a, b) => a.id.localeCompare(b.id));
}

function hasBlock(name) {
  return selectedBlocks.has(name);
}

function galleryIndexes() {
  return [...new Set(getItems("product_images.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function tabIndexes() {
  return [...new Set(getItems("tabs.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function categoryIndexes() {
  return [...new Set(getItems("configurator_categories.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function categoryItemIndexes(categoryIndex) {
  const prefix = `configurator_categories.${categoryIndex}.items.`;
  return [...new Set(getItems(prefix).map((field) => field.path[3]))].sort((a, b) => a - b);
}

function baseMetafieldIndexes() {
  return [...new Set(getItems("base_metafields.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function variantIndexes() {
  return [...new Set(getItems("variant_metafields.").map((field) => field.path[1]))].sort((a, b) => a - b);
}

function variantFieldIndexes(variantIndex) {
  const prefix = `variant_metafields.${variantIndex}.fields.`;
  return [...new Set(getItems(prefix).map((field) => field.path[3]))].sort((a, b) => a - b);
}

function renderGallery() {
  const indexes = galleryIndexes();
  if (!hasBlock("gallery_main_image") && !hasBlock("gallery_thumbnails") && !hasBlock("gallery_caption")) return "";
  const first = indexes[0];
  const main = hasBlock("gallery_main_image")
    ? (first === undefined ? `<div class="ctcm-media"><div class="ctcm-media-placeholder">Image</div></div>` : imageSlot(`product_images.${first}.url`, "ctcm-media ctcm-gallery-main", byId(`product_images.${first}.alt`).value))
    : "";
  const thumbnails = hasBlock("gallery_thumbnails")
    ? `<div class="ctcm-gallery-thumbnails">${indexes.map((index) => imageSlot(`product_images.${index}.url`, "ctcm-gallery-thumbnail", byId(`product_images.${index}.alt`).value)).join("")}</div>`
    : "";
  const caption = hasBlock("gallery_caption") && first !== undefined
    ? editable(`product_images.${first}.caption`, "p", "ctcm-gallery-caption") : "";
  return `<div class="ctcm-gallery">${main}${thumbnails}${caption}</div>`;
}

function renderHero() {
  const info = [
    hasBlock("product_title") ? editable("product_name", "h1", "ctcm-title") : "",
    hasBlock("product_price") ? editable("product_price", "p", "ctcm-price") : "",
    hasBlock("product_description") ? editable("product_description", "p", "ctcm-description") : "",
    hasBlock("primary_action") ? `<span class="ctcm-button" contenteditable="true" data-edit-text="primary_cta_text">${html(byId("primary_cta_text").value || "Add Base Product")}</span>${linkInput("primary_cta_url", "Primary button link")}` : ""
  ].join("");
  const gallery = renderGallery();
  if (!gallery && !info) return "";
  return `<section class="ctcm-product">
    ${gallery}
    <div class="ctcm-product-info">
      ${info}
    </div>
  </section>`;
}

function renderTabs() {
  if (!hasBlock("information_heading") && !hasBlock("information_tab_navigation") && !hasBlock("information_tab_panels")) return "";
  const indexes = tabIndexes();
  const buttons = indexes.map((index, i) => {
    const active = i === 0 ? " is-active" : "";
    return `<li><button class="ctcm-tab-button${active}" type="button" data-ctcm-tab="admin-tab-${index}">
      <span contenteditable="true" data-edit-text="tabs.${index}.title">${html(byId(`tabs.${index}.title`).value)}</span>
    </button></li>`;
  }).join("");
  const panels = indexes.map((index, i) => {
    const active = i === 0 ? " is-active" : "";
    return `<div class="ctcm-tab-panel${active}" id="admin-tab-${index}" data-ctcm-tab-panel contenteditable="true" data-edit-text="tabs.${index}.content">${html(byId(`tabs.${index}.content`).value)}</div>`;
  }).join("");
  return `<section class="ctcm-section" data-ctcm-tabs>
    ${hasBlock("information_heading") ? editable("product_info_heading", "h2") : ""}
    ${hasBlock("information_tab_navigation") ? `<ul class="ctcm-tabs-list">${buttons}</ul>` : ""}
    ${hasBlock("information_tab_panels") ? panels : ""}
  </section>`;
}

function renderConfigurator() {
  const addonNames = ["addon_heading", "addon_catalog", "addon_summary_heading", "addon_selection_lines", "addon_total", "addon_submit_action"];
  if (!addonNames.some(hasBlock)) return "";
  const cats = categoryIndexes();
  const baseCost = parsePrice(byId("configurator_base_cost").value);
  const categories = cats.map((categoryIndex, i) => {
    const itemIndexes = categoryItemIndexes(categoryIndex);
    const items = itemIndexes.map((itemIndex) => {
      const prefix = `configurator_categories.${categoryIndex}.items.${itemIndex}`;
      const name = byId(`${prefix}.name`).value;
      return `<div class="ctcm-option">
        ${imageSlot(`${prefix}.image`, "ctcm-option-image", name)}
        <div>
          <span class="ctcm-option-name" contenteditable="true" data-edit-text="${prefix}.name">${html(name)}</span>
          <span class="ctcm-option-meta">
            <span contenteditable="true" data-edit-text="${prefix}.variant">${html(byId(`${prefix}.variant`).value)}</span>
            ·
            ${editablePrice(`${prefix}.price`, "span")}
          </span>
        </div>
        <div class="ctcm-qty">
          <button type="button" disabled>-</button>
          <input type="number" value="0" disabled>
          <button type="button" disabled>+</button>
        </div>
      </div>`;
    }).join("");
    return `<div class="ctcm-category${i === 0 ? " is-open" : ""}">
      <button class="ctcm-category-toggle" type="button" data-ctcm-category-toggle>
        <span contenteditable="true" data-edit-text="configurator_categories.${categoryIndex}.name">${html(byId(`configurator_categories.${categoryIndex}.name`).value)}</span>
        <span>${itemIndexes.length} options</span>
      </button>
      <div class="ctcm-category-body">${items}</div>
    </div>`;
  }).join("");
  return `<section class="ctcm-section" data-ctcm-configurator>
    ${hasBlock("addon_heading") ? editable("configurator_heading", "h2") : ""}
    <div class="ctcm-configurator-grid">
      <div>${hasBlock("addon_catalog") ? categories : ""}</div>
      <aside class="ctcm-summary">
        ${hasBlock("addon_summary_heading") ? editable("summary_heading", "h3") : ""}
        ${hasBlock("addon_selection_lines") ? `<div><p contenteditable="true" data-edit-text="empty_summary_text">${html(byId("empty_summary_text").value)}</p></div>` : ""}
        ${hasBlock("addon_total") ? `<div class="ctcm-summary-total"><span contenteditable="true" data-edit-text="addon_total_label">${html(byId("addon_total_label").value)}</span><span>${money(baseCost)}</span></div>${pricingInput("configurator_base_cost", "Base item cost before configurations", "price")}${pricingInput("configurator_price_multiplier", "Configuration price multiplier", "multiplier")}` : ""}
        ${hasBlock("addon_submit_action") ? `<span class="ctcm-button" contenteditable="true" data-edit-text="add_selected_text">${html(byId("add_selected_text").value)}</span>` : ""}
      </aside>
    </div>
  </section>`;
}

function renderMetafields() {
  const base = baseMetafieldIndexes();
  const variants = variantIndexes();
  const productSelected = hasBlock("product_metafields_heading") || hasBlock("product_metafields_list");
  const variantSelected = hasBlock("variant_metafields_heading") || hasBlock("variant_selector") || hasBlock("variant_metafields_panels");
  if (!productSelected && !variantSelected) return "";
  const baseRows = base.map((index) => `<dt contenteditable="true" data-edit-text="base_metafields.${index}.key">${html(byId(`base_metafields.${index}.key`).value)}</dt><dd contenteditable="true" data-edit-text="base_metafields.${index}.value">${html(byId(`base_metafields.${index}.value`).value)}</dd>`).join("");
  const variantOptions = variants.map((index) => `<option>${html(byId(`variant_metafields.${index}.variant`).value)}</option>`).join("");
  const variantRows = variants.map((variantIndex) => {
    const rows = variantFieldIndexes(variantIndex).map((fieldIndex) => `<dt contenteditable="true" data-edit-text="variant_metafields.${variantIndex}.fields.${fieldIndex}.key">${html(byId(`variant_metafields.${variantIndex}.fields.${fieldIndex}.key`).value)}</dt><dd contenteditable="true" data-edit-text="variant_metafields.${variantIndex}.fields.${fieldIndex}.value">${html(byId(`variant_metafields.${variantIndex}.fields.${fieldIndex}.value`).value)}</dd>`).join("");
    return `<dl>${rows}</dl>`;
  }).join("");
  const productBlock = productSelected ? `<section class="ctcm-section ctcm-metafields">${hasBlock("product_metafields_heading") ? editable("metafields_heading", "h2") : ""}${hasBlock("product_metafields_list") ? `<dl>${baseRows}</dl>` : ""}</section>` : "";
  const variantBlock = variantSelected ? `<section class="ctcm-section ctcm-metafields">${hasBlock("variant_metafields_heading") ? editable("variant_metafields_heading", "h2") : ""}${hasBlock("variant_selector") && variants.length ? `<label><span contenteditable="true" data-edit-text="variant_metafields_label">${html(byId("variant_metafields_label").value)}</span><select>${variantOptions}</select></label>` : ""}${hasBlock("variant_metafields_panels") ? variantRows : ""}</section>` : "";
  return productBlock + variantBlock;
}

function renderEditor() {
  document.title = `${byId("site_title").value || "CTCM"} - Visual Backend`;
  document.getElementById("visual-editor").innerHTML = [
    renderHero(),
    renderTabs(),
    renderConfigurator(),
    renderMetafields()
  ].join("");
  bindEditorEvents();
}

function updateField(id, value) {
  const field = byId(id);
  field.value = value;
}

function bindEditorEvents() {
  document.querySelectorAll("[data-edit-text]").forEach((node) => {
    node.addEventListener("input", () => updateField(node.dataset.editText, node.textContent.trim()));
  });

  document.querySelectorAll("[data-edit-price]").forEach((node) => {
    node.addEventListener("input", () => updateField(node.dataset.editPrice, normalizePrice(node.textContent)));
    node.addEventListener("blur", () => {
      node.textContent = money(byId(node.dataset.editPrice).value);
    });
  });

  document.querySelectorAll("[data-edit-link]").forEach((node) => {
    node.addEventListener("input", () => updateField(node.dataset.editLink, node.value.trim()));
  });

  document.querySelectorAll("[data-edit-pricing]").forEach((node) => {
    node.addEventListener("input", () => {
      const kind = node.dataset.pricingKind;
      updateField(node.dataset.editPricing, kind === "multiplier" ? normalizeMultiplier(node.value) : normalizePrice(node.value));
    });
  });

  document.querySelectorAll("[data-edit-image]").forEach((slot) => {
    slot.addEventListener("click", () => selectImageSlot(slot));
    slot.addEventListener("dragenter", (event) => {
      event.preventDefault();
      slot.classList.add("is-drag-over");
    });
    slot.addEventListener("dragover", (event) => {
      event.preventDefault();
      slot.classList.add("is-drag-over");
    });
    slot.addEventListener("dragleave", () => slot.classList.remove("is-drag-over"));
    slot.addEventListener("drop", (event) => handleImageDrop(event, event.currentTarget));
  });
}

function selectImageSlot(slot) {
  document.querySelectorAll(".admin-image-edit").forEach((el) => el.classList.remove("is-selected"));
  slot.classList.add("is-selected");
  selectedImageFieldId = slot.dataset.editImage;
}

function setImageValue(fieldId, value) {
  updateField(fieldId, value);
  renderEditor();
  const slot = document.querySelector(`[data-edit-image="${fieldId}"]`);
  if (slot) selectImageSlot(slot);
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Unable to read image file."));
    reader.onload = () => {
      const image = new Image();
      image.onerror = () => reject(new Error("Unable to load image file."));
      image.onload = () => resolve(image);
      image.src = reader.result;
    };
    reader.readAsDataURL(file);
  });
}

function slotSize(slot) {
  const rect = slot.getBoundingClientRect();
  const style = window.getComputedStyle(slot);
  const cssWidth = Number.parseFloat(style.width);
  const cssHeight = Number.parseFloat(style.height);
  const width = Math.max(1, Math.round(rect.width || slot.clientWidth || cssWidth || 800));
  const fallbackHeight = slot.classList.contains("ctcm-option-image") ? width : width;
  const height = Math.max(1, Math.round(rect.height || slot.clientHeight || cssHeight || fallbackHeight));
  return { width, height };
}

async function convertImageForSlot(file, slot) {
  const image = await loadImageFromFile(file);
  const target = slotSize(slot);
  const canvas = document.createElement("canvas");
  canvas.width = target.width;
  canvas.height = target.height;
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const scale = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
  const drawWidth = Math.round(image.naturalWidth * scale);
  const drawHeight = Math.round(image.naturalHeight * scale);
  const dx = Math.round((canvas.width - drawWidth) / 2);
  const dy = Math.round((canvas.height - drawHeight) / 2);
  ctx.drawImage(image, dx, dy, drawWidth, drawHeight);

  return canvas.toDataURL(slot.dataset.imageOutputType || IMAGE_OUTPUT_TYPE, IMAGE_OUTPUT_QUALITY);
}

function handleImageDrop(event, slot = null) {
  event.preventDefault();
  const droppedSlot = event.target.closest ? event.target.closest("[data-edit-image]") : null;
  const target = slot || droppedSlot || (selectedImageFieldId ? document.querySelector(`[data-edit-image="${selectedImageFieldId}"]`) : null);
  if (!target) return;
  target.classList.remove("is-drag-over");
  selectImageSlot(target);
  const fieldId = target.dataset.editImage;
  const file = event.dataTransfer.files && event.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) {
    convertImageForSlot(file, target)
      .then((dataUrl) => setImageValue(fieldId, dataUrl))
      .catch(() => {
        const reader = new FileReader();
        reader.onload = () => setImageValue(fieldId, reader.result);
        reader.readAsDataURL(file);
      });
    return;
  }
  const url = event.dataTransfer.getData("text/uri-list") || event.dataTransfer.getData("text/plain");
  if (url) setImageValue(fieldId, url.trim());
}

document.addEventListener("dragover", (event) => {
  if (selectedImageFieldId) event.preventDefault();
});

document.addEventListener("drop", (event) => {
  if (!event.target.closest("[data-edit-image]") && selectedImageFieldId) {
    handleImageDrop(event);
  }
});

async function loadContent() {
  const response = await fetch("/api/content");
  const model = await response.json();
  fields = model.fields || [];
  selectedBlocks = new Set(model.selected_blocks || []);
  fieldMap = new Map(fields.map((field) => [field.id, field]));
  renderEditor();
}

async function saveContent() {
  const status = document.getElementById("status");
  status.textContent = "Saving...";
  const response = await fetch("/api/content", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields })
  });
  if (!response.ok) {
    status.textContent = "Save failed.";
    return;
  }
  const payload = await response.json();
  fields = payload.content.fields || fields;
  fieldMap = new Map(fields.map((field) => [field.id, field]));
  status.textContent = "Saved.";
}

document.getElementById("save-button").addEventListener("click", saveContent);
loadContent();
'''


def backend_files() -> dict[str, str]:
    return {
        "backend/server.py": BACKEND_SERVER,
        "backend/admin.html": BACKEND_ADMIN_HTML,
        "backend/admin.css": BACKEND_ADMIN_CSS,
        "backend/admin.js": BACKEND_ADMIN_JS,
    }


def build_initial_content(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "notice": "Editable content only: text, links, and image URLs/paths. Styling and layout are locked in the block functions.",
        "inputs": {key: value for key, value in context.items() if not key.startswith("_")},
    }


def write_site(site_dir: Path, files: dict[str, str], context: dict[str, Any], selected_blocks: list[str]) -> None:
    site_dir.mkdir(parents=True, exist_ok=False)
    files.update(backend_files())
    for relative_path, content in files.items():
        output_path = site_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    config = {
        "site_folder": site_dir.name,
        "selected_blocks": selected_blocks,
        "inputs": {key: value for key, value in context.items() if not key.startswith("_")},
    }
    (site_dir / "site_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    (site_dir / "content.json").write_text(json.dumps(build_initial_content(context), indent=2), encoding="utf-8")


def main() -> None:
    manifest = ctcm_blocks.get_block_manifest()
    context: dict[str, Any] = {}

    print("CTCM V1.0 Call System")
    print("Build a product display webpage from reusable block functions.")

    selected_blocks = choose_blocks(manifest)
    collect_required_inputs(context)
    collect_optional_inputs(context, selected_blocks)

    site_dir = next_site_dir()
    files = ctcm_blocks.assemble_site(context, selected_blocks)
    write_site(site_dir, files, context, selected_blocks)

    print("\nCreated site:")
    print(site_dir)
    print("\nOpen index.html in a browser to view it.")
    print("Run python3 backend/server.py inside the site folder to edit text, links, and image URLs/paths.")


if __name__ == "__main__":
    main()
