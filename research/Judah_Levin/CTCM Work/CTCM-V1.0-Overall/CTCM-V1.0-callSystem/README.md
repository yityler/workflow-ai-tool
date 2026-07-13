# CTCM V1.0 Call System

## Run

From this folder:

```text
python ctcm_call_system.py
```

The system reads the current schema-3 block manifest from `../CTCM-V1.0-blockFunctions/block_manifest.json` and creates the next sequential site under `../CTCM-V1.0-pageHolder/CTCM-SN`.

## Current block-selection behavior

1. `core_runtime` is always selected because it is the only required block.
2. Every atomic content block is offered independently.
3. Selected dependencies are added automatically. For example, selecting `gallery_thumbnails` also selects `gallery_main_image`; selecting `variant_selector` also selects `variant_metafields_panels`.
4. The caller collects inputs only for the selected feature families.
5. `assemble_site` generates the site using the current 22-block API.

Feature families include:

- Gallery main image, thumbnail navigation, and captions.
- Product title, price, description, and primary action.
- Information heading, tab navigation, and tab panels.
- Add-on heading, catalog, summary heading, selection lines, total, and submit action.
- Product metafield heading/list and variant heading/selector/panels.

## Gallery input collection

The caller asks how many product images are needed. For every image it collects:

- URL or local path.
- Accessible alt text.
- Optional visible caption.

These values are stored in `product_images` objects shaped as:

```json
{"url": "image.jpg", "alt": "Front view", "caption": "Shown in blue"}
```

`product_image` is also saved as a legacy first-image fallback.

## Generated files

- `index.html`
- `assets/css/site.css`
- `assets/js/site.js`
- `site_config.json`
- `content.json`
- `backend/server.py`
- `backend/admin.html`
- `backend/admin.css`
- `backend/admin.js`

## Generated-site editor

From a generated site folder, run:

```text
python backend/server.py
```

Then open `http://127.0.0.1:8765`.

The editor is aware of `selected_blocks` and previews only the atomic blocks chosen for that site. It supports editing:

- Gallery image files/URLs, alt text, and captions.
- Product and section text.
- Primary-action link URL.
- Tab titles and content.
- Add-on categories, item images, variants, prices, summary labels, base cost, and multiplier.
- Product and variant metafields.

Dropped images are converted in the browser to WebP data URLs. Prices are normalized to internal numeric strings so add-on totals continue to work.

The editor intentionally does not expose layout, font, spacing, or CSS controls. Those remain owned by the block library.

## Configuration contract

`site_config.json` stores:

- `site_folder`: generated folder name.
- `selected_blocks`: current atomic public block names, including resolved dependencies.
- `inputs`: the shared context passed to block assembly.

The backend rebuilds the generated files using those exact block names and inputs after every save.
