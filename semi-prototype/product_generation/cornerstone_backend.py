

from __future__ import annotations

from typing import Any
_SKIP_KEYS = {"type", "id"}

_LONG_TEXT_KEYS = {"body", "description", "answer", "quote", "text"}


def infer_kind(path: list) -> str:
    last = path[-1]
    key = path[-2] if isinstance(last, int) and len(path) >= 2 else last
    key = str(key)
    if key == "image" or key.endswith("_image") or key.endswith("images"):
        return "image"
    if key.endswith("_url") or key == "url":
        return "link"
    if key in _LONG_TEXT_KEYS:
        return "long_text"
    return "text"


def _label(path: list) -> str:
    parts = []
    for part in path:
        if isinstance(part, int):
            parts.append(str(part + 1))
        else:
            parts.append(str(part).replace("_", " ").title())
    return " \u203a ".join(parts)


def _is_section_root(path: list) -> bool:
    return len(path) == 2 and path[0] == "sections" and isinstance(path[1], int)


def _walk(value: Any, path: list, fields: list) -> None:
    if isinstance(value, dict):
        skip_structural = _is_section_root(path)
        for key, sub in value.items():
            if skip_structural and key in _SKIP_KEYS:
                continue
            _walk(sub, path + [key], fields)
    elif isinstance(value, list):
        for index, sub in enumerate(value):
            _walk(sub, path + [index], fields)
    else:
        fields.append(
            {
                "id": ".".join(str(p) for p in path),
                "path": path,
                "label": _label(path),
                "value": "" if value is None else str(value),
                "kind": infer_kind(path),
            }
        )


def build_content_model(config: dict) -> dict:
    fields: list = []
    for key in ("site_title", "tagline", "primary_cta"):
        if key in config:
            _walk(config[key], [key], fields)
    if "accent_color" in config:
        fields.append(
            {
                "id": "accent_color",
                "path": ["accent_color"],
                "label": "Accent color",
                "value": config.get("accent_color") or "#2563eb",
                "kind": "color",
            }
        )
    for index, section in enumerate(config.get("sections", [])):
        _walk(section, ["sections", index], fields)
    return {
        "notice": "Editable content only: text, links, and images. Layout and styling are locked in the block library.",
        "fields": fields,
    }


def set_nested(config: dict, path: list, value) -> None:
    target = config
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


def apply_fields(config: dict, fields: list) -> None:
    for item in fields:
        path = item.get("path")
        if not isinstance(path, list) or not path:
            continue
        try:
            set_nested(config, path, item.get("value", ""))
        except (KeyError, IndexError, TypeError):
            continue
