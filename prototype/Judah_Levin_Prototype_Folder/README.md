# Judah Levin Prototype Folder

## Purpose

This folder begins as an exact copy of `../Tyler_Yi_Prototype_Folder` and adds Judah Levin's current Week4 CTCM work. It preserves Tyler's token-optimized LLM storefront experiment while adding a second, deterministic webpage-generation path based on 22 atomic, AI-retrievable block functions.

## What was copied unchanged from Tyler's prototype

The following files were copied without intentional code or content changes:

- `page_generator.py`: Tyler's Gradio-based B2B storefront generator, structured layout specification, template caching, model routing, RAG design-knowledge retrieval, and Python HTML rendering.
- `token_optimizer.py`: token counting, compression, caching, adaptive RAG, output limits, and savings measurement utilities.
- `design_knowledge.txt`: design-knowledge corpus used by Tyler's RAG workflow.
- `optimization-strategy.md`: Tyler's token-optimization documentation.
- `prototype_log.md`: Tyler's development log.

This means Judah's folder retains Tyler's original prototype path. Run `page_generator.py` under the same dependency and data assumptions as Tyler's version.

## What was integrated from Judah's Week4 work

### Atomic CTCM block library

`CTCM-V1.0-blockFunctions/` contains:

- `ctcm_blocks.py`: implementations and site assembly.
- `block_manifest.json`: schema-3, AI-readable catalog of 22 public blocks.
- `README.md`: short library overview.

The library uses one required infrastructure block, `core_runtime`, and 21 optional content blocks. The optional blocks independently represent:

- Main gallery image, thumbnail navigation, and caption.
- Product title, price, description, and primary action.
- Information heading, tab navigation, and tab panels.
- Add-on heading, catalog, summary heading, selection lines, total, and submit action.
- Product-metafield heading/list and variant heading/selector/panels.

### Current CTCM call system

`CTCM-V1.0-callSystem/` contains the interactive generator and its documentation. It:

- Reads the 22-block manifest.
- Always includes `core_runtime`.
- Prompts for atomic optional blocks.
- Resolves dependencies automatically.
- Collects multi-image gallery URLs/paths, alt text, and captions.
- Generates sequential sites under `CTCM-V1.0-pageHolder/`.
- Adds a local visual editing backend that respects the selected atomic blocks.

Run it from this folder with:

```text
python CTCM-V1.0-callSystem/ctcm_call_system.py
```

### Programmatic integration entry point

`ctcm_prototype.py` provides a small API for code that wants to use the CTCM system without the interactive questionnaire:

```python
from ctcm_prototype import build_site, list_blocks

blocks = list_blocks()
build_site(
    "CTCM-V1.0-pageHolder/example",
    {
        "site_title": "Example",
        "product_name": "Example Product",
        "product_price": "$99.00",
        "product_images": [
            {"url": "front.jpg", "alt": "Front view", "caption": "Front"},
            {"url": "back.jpg", "alt": "Back view", "caption": "Back"}
        ]
    },
    [
        "core_runtime",
        "gallery_main_image",
        "gallery_thumbnails",
        "gallery_caption",
        "product_title",
        "product_price"
    ]
)
```

Run `python ctcm_prototype.py` to print the available public block catalog.

The complete AI-oriented block contract is copied into `CTCM-V1.0_REFERENCE.md`.

## Differences from `Tyler_Yi_Prototype_Folder`

| Area | Tyler folder | Judah folder |
|---|---|---|
| Original prototype files | Five token-optimization/design files | Same five files, copied unchanged |
| Primary generation approach | LLM produces a compact page template; Python renders pages | Retains Tyler's approach and adds deterministic atomic-block assembly |
| Public UI block catalog | Fixed `SectionType` vocabulary inside `page_generator.py` | Adds an external JSON manifest containing 22 independently retrievable blocks |
| Required runtime | Tyler's renderer and Gradio application | Adds `core_runtime`, which emits HTML, CSS, and JavaScript |
| Gallery model | Product rendering owned by Tyler's page renderer | Adds independently selectable main image, thumbnails, and caption blocks |
| Tab model | No standalone atomic CTCM tab API | Separate heading, navigation, and panel blocks |
| Add-on configurator | Not provided as the CTCM add-on system | Separate catalog, selection lines, total, and submit-action blocks |
| Metafields | Not provided as the CTCM metadata system | Separate product and variant metadata components |
| Block dependencies | Enforced through Tyler's Pydantic template validation | Declared in `block_manifest.json` and resolved by the call system |
| Content editor | Gradio generation/edit workflow | Retains Gradio workflow and adds a generated-site local editor |
| Image input | Tyler's product/catalog rendering | Adds multi-image URL/path, alt-text, caption, thumbnail, and WebP-drop support |
| Programmatic API | Functions inside `page_generator.py` | Adds `ctcm_prototype.py` with `list_blocks()` and `build_site()` |
| Generated output directory | Tyler's template/cache behavior | Adds `CTCM-V1.0-pageHolder/` for generated CTCM sites |
| AI documentation | Tyler's optimization documents | Adds schema-3 manifest plus `CTCM-V1.0_REFERENCE.md` |

## Architectural relationship

The two approaches are intentionally retained side by side:

- Tyler's system optimizes how an LLM designs reusable storefront templates and measures token savings.
- Judah's CTCM system makes the rendered interface itself composable from narrow, deterministic functions that an AI can retrieve by capability and required input.

No automatic bridge currently converts Tyler's `PageTemplate`/`Section` objects into CTCM block selections. They are two available generation paths in the same prototype folder, which avoids changing or destabilizing Tyler's original experiment.

## Verification expectations

- `ctcm_prototype.py` must load exactly 22 public blocks.
- Every manifest block name must resolve to a callable implementation.
- All declared dependencies must refer to known blocks.
- A smoke-test site should produce `index.html`, `assets/css/site.css`, `assets/js/site.js`, and `site_config.json`.
