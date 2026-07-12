"""Local content backend for this generated CTCM site.

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
}

PRICING_TOP_LEVEL = {
    "configurator_base_cost": "Base item cost before configurations",
    "configurator_price_multiplier": "Configuration price multiplier",
}

LINK_TOP_LEVEL = {
    "primary_cta_url": "Primary button link URL",
}

IMAGE_TOP_LEVEL = {
    "product_image": "Product image URL/path",
}

TEXT_DEFAULTS = {
    "product_info_heading": "Product Information",
    "configurator_heading": "Product Configurator",
    "summary_heading": "Your Selections",
    "empty_summary_text": "No items selected yet.",
    "add_selected_text": "Add Selected",
    "metafields_heading": "Metafields",
    "variant_metafields_label": "Variant metafields",
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
    for key, label in IMAGE_TOP_LEVEL.items():
        fields.append(field([key], label, inputs.get(key, ""), "image"))

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
