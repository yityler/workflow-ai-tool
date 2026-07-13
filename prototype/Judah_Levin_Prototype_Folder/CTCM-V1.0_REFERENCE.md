# CTCM V1.0 Atomic Block Reference

## System purpose

CTCM assembles static product and add-on webpages from atomic Python block functions. Each public content block owns one visible UI responsibility. This lets an AI retrieve the smallest useful block set instead of selecting a large page template.

- Implementation: `CTCM-V1.0-blockFunctions/ctcm_blocks.py`
- Machine-readable catalog: `CTCM-V1.0-blockFunctions/block_manifest.json`
- Interactive generator: `CTCM-V1.0-callSystem/ctcm_call_system.py`

## Mandatory AI assembly algorithm

1. Select `core_runtime` for every page.
2. Convert the user request into individual visible UI requirements.
3. Select one atomic block for each requirement.
4. Recursively add every block listed in `dependencies`.
5. Collect every input whose manifest field says `required: true`.
6. Put all inputs in one shared context dictionary.
7. Call `assemble_site(context, block_names)`.
8. Write every returned path/content pair to the generated site directory.

Block-name order does not determine visual order. `core_runtime` uses stable named output slots. Missing slots are omitted.

## Input conventions

- `string`: plain text unless explicitly described as a URL/path or formatted price.
- `product_images`: list of strings or objects. Object shape: `{"url": string, "alt": string, "caption": string}`.
- `tabs`: `[{"title": string, "content": string}]`.
- `configurator_categories`: `[{"name": string, "items": [{"name": string, "variant": string, "price": number|string, "image": string}]}]`.
- `base_metafields`: `[{"key": string, "value": string}]`.
- `variant_metafields`: `[{"variant": string, "fields": [{"key": string, "value": string}]}]`.
- Visible user text and attribute values are escaped. Tab and description values are plain text, not trusted HTML.

## Required infrastructure block

### `core_runtime`

- Function: `block_core_runtime`
- Required: always.
- Does: creates `index.html`, shared responsive CSS, and shared browser JavaScript; assembles every selected output slot into gallery, product, tabs, add-on, and metafield containers.
- Required inputs: none.
- Optional inputs: `site_title` (falls back to `product_name`), `accent_color` (default `#0f766e`).
- Outputs: `index.html`, `assets/css/site.css`, `assets/js/site.js`.
- Provides behavior for gallery thumbnails/captions, tab switching, add-on category toggles, quantities/totals, and variant switching.

## Gallery blocks

### `gallery_main_image`

- Does: renders the large currently selected image. If no usable image exists, renders a placeholder.
- Required inputs: none.
- Optional inputs: `product_images`, legacy `product_image`, and `product_name` for fallback alt text.
- Dependencies: `core_runtime`.
- Select alone for a single-image product. It is also the required foundation for thumbnails and captions.

### `gallery_thumbnails`

- Does: renders one accessible thumbnail button per product image. Clicking a thumbnail changes the main image and active thumbnail state.
- Required input: `product_images` with at least one object containing `url`; `alt` and `caption` are strongly recommended.
- Dependencies: `core_runtime`, `gallery_main_image`.
- Important: this block owns navigation only; it deliberately does not render the main display image.

### `gallery_caption`

- Does: renders the current image caption below the gallery. Thumbnail clicks replace the caption with the selected image's `caption` value.
- Required input: `product_images` objects containing `url` and `caption`.
- Dependencies: `core_runtime`, `gallery_main_image`.
- May be used without thumbnails to show the first image's caption.

## Primary product blocks

### `product_title`

- Does: renders only the primary `<h1>`.
- Required input: `product_name`.
- Dependencies: `core_runtime`.

### `product_price`

- Does: renders only the visible base price; it does not calculate or localize the supplied string.
- Required input: `product_price`, for example `$99.00`.
- Dependencies: `core_runtime`.

### `product_description`

- Does: renders only the short plain-text product description.
- Required input: `product_description`.
- Dependencies: `core_runtime`.

### `primary_action`

- Does: renders one primary call to action. A nonempty URL produces an anchor; an empty URL produces a button.
- Required inputs: none.
- Optional inputs: `primary_cta_text` (default `Add Base Product`), `primary_cta_url` (default empty).
- Dependencies: `core_runtime`.
- Important: a button has no real commerce integration until application code connects it.

## Product-information blocks

### `information_heading`

- Does: renders only the heading above the product-information area.
- Required inputs: none.
- Optional input: `product_info_heading` (default `Product Information`).
- Dependencies: `core_runtime`.

### `information_tab_navigation`

- Does: renders only the clickable tab-button list. Button target IDs are deterministically derived from tab titles and positions.
- Required input: `tabs`.
- Dependencies: `core_runtime`, `information_tab_panels`.
- Important: do not select without panels because the buttons need matching targets.

### `information_tab_panels`

- Does: renders only the tab content panels and marks the first panel active.
- Required input: `tabs`; it must be identical to the list used by navigation.
- Dependencies: `core_runtime`.
- Can be selected without navigation if all content panels are needed as generated markup, although only the first is visible under standard CSS.

## Add-on/configurator blocks

### `addon_heading`

- Does: renders only the heading above the add-on options area.
- Required inputs: none.
- Optional input: `configurator_heading` (default `Product Configurator`).
- Dependencies: `core_runtime`.

### `addon_catalog`

- Does: renders collapsible categories and item cards. Each card can include an image, name, variant/SKU label, price, and decrement/input/increment quantity controls.
- Required input: `configurator_categories`.
- Dependencies: `core_runtime`.
- This is the foundational add-on block required by every live summary/total/action block.

### `addon_summary_heading`

- Does: renders only the title above the selection summary.
- Required inputs: none.
- Optional input: `summary_heading` (default `Your Selections`).
- Dependencies: `core_runtime`, `addon_catalog`.

### `addon_selection_lines`

- Does: renders the live region where JavaScript itemizes selected names, quantities, and line totals.
- Required inputs: none.
- Optional input: `empty_summary_text` (default `No items selected yet.`).
- Dependencies: `core_runtime`, `addon_catalog`.

### `addon_total`

- Does: renders only the live calculated total row.
- Required inputs: none.
- Optional inputs: `addon_total_label` (default `Total`), `configurator_base_cost` (default `0`), `configurator_price_multiplier` (default `1`).
- Formula: `base cost + (selected add-on subtotal × multiplier)`.
- Dependencies: `core_runtime`, `addon_catalog`.

### `addon_submit_action`

- Does: renders the final Add Selected button and its status-message region.
- Required inputs: none.
- Optional input: `add_selected_text` (default `Add Selected`).
- Dependencies: `core_runtime`, `addon_catalog`.
- Important: this demonstrates selection handoff but does not call a real cart API.

## Product metafield blocks

### `product_metafields_heading`

- Does: renders only the heading above product-level metadata.
- Required inputs: none.
- Optional input: `metafields_heading` (default `Metafields`).
- Dependencies: `core_runtime`.

### `product_metafields_list`

- Does: renders only the product-level key/value definition list, suitable for material, dimensions, warranty, manufacturer, or origin.
- Required input: `base_metafields`.
- Dependencies: `core_runtime`.
- Fallback: an empty list produces an example Material field.

## Variant metafield blocks

### `variant_metafields_heading`

- Does: renders only the heading above variant metadata.
- Required inputs: none.
- Optional input: `variant_metafields_heading` (default `Variant Metafields`).
- Dependencies: `core_runtime`.

### `variant_selector`

- Does: renders only the dropdown used to choose which variant metadata panel is visible.
- Required input: `variant_metafields`.
- Optional input: `variant_metafields_label` (default `Variant metafields`).
- Dependencies: `core_runtime`, `variant_metafields_panels`.
- Important: use the exact same variant list for the selector and panels.

### `variant_metafields_panels`

- Does: renders one key/value definition list per variant, with only the first initially visible.
- Required input: `variant_metafields`.
- Dependencies: `core_runtime`.

## Stable visual assembly order

1. Gallery: main image → thumbnails → caption.
2. Product information column: title → price → description → primary action.
3. Information area: heading → tab navigation → tab panels.
4. Add-on options: heading → catalog.
5. Add-on summary: heading → selection lines → total → submit action.
6. Product metafields: heading → list.
7. Variant metafields: heading → selector → panels.

## Common AI recipes

### Simple product card/page

`core_runtime`, `gallery_main_image`, `product_title`, `product_price`, `product_description`, `primary_action`.

### Full photo gallery

`core_runtime`, `gallery_main_image`, `gallery_thumbnails`, `gallery_caption` with multiple `product_images` objects.

### Add-on selection page

`core_runtime`, `addon_heading`, `addon_catalog`, `addon_summary_heading`, `addon_selection_lines`, `addon_total`, `addon_submit_action`.

### Tabbed technical product page

`core_runtime`, `product_title`, `information_heading`, `information_tab_navigation`, `information_tab_panels`, `product_metafields_heading`, `product_metafields_list`.

## Migration from manifest schema 2.0

- `photo_gallery` → `gallery_main_image`, optionally `gallery_thumbnails`, `gallery_caption`.
- `information_tabs` → `information_heading`, `information_tab_navigation`, `information_tab_panels`.
- `addon_options` → `addon_heading`, `addon_catalog`.
- `addon_summary` → `addon_summary_heading`, `addon_selection_lines`, `addon_total`, `addon_submit_action`.
- `product_metafields` → `product_metafields_heading`, `product_metafields_list`.
- `variant_metafields` → `variant_metafields_heading`, `variant_selector`, `variant_metafields_panels`.
- `product_title`, `product_price`, `product_description`, `primary_action`, and `core_runtime` remain unchanged because they already represent single responsibilities.
