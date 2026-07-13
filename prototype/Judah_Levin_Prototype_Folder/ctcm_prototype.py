"""Programmatic entry point for Judah's atomic CTCM prototype.

This module keeps Tyler's original Gradio prototype intact while exposing the
Week4 schema-3 block library from the same prototype folder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
BLOCK_DIR = HERE / "CTCM-V1.0-blockFunctions"
sys.path.insert(0, str(BLOCK_DIR))

import ctcm_blocks  # noqa: E402


def list_blocks() -> list[dict[str, Any]]:
    """Return the current AI-readable catalog of 22 atomic blocks."""

    return ctcm_blocks.get_block_manifest()["blocks"]


def build_site(
    output_dir: str | Path,
    context: dict[str, Any],
    selected_blocks: list[str],
) -> Path:
    """Assemble and write one CTCM site plus its reproducible configuration."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    files = ctcm_blocks.assemble_site(context, selected_blocks)
    for relative_path, content in files.items():
        target = output_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    config = {
        "selected_blocks": selected_blocks,
        "inputs": {key: value for key, value in context.items() if not key.startswith("_")},
    }
    (output_path / "site_config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
    return output_path


if __name__ == "__main__":
    print("Available CTCM atomic blocks:")
    for block in list_blocks():
        required = "required" if block.get("required") else "optional"
        print(f"- {block['name']} ({required}): {block['summary']}")

