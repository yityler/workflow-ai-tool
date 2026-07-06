# CTCM V1.0 Call System

Run `python3 ctcm_call_system.py` from this folder.

The program:

1. Loads callable blocks from `../CTCM-V1.0-blockFunctions`.
2. Immediately includes every block marked `required` in `block_manifest.json`.
3. Lets the user add optional blocks such as tabs, configurator, and metafields.
4. Prompts for inputs needed by the selected blocks.
5. Writes a new generated site folder in `../CTCM-V1.0-pageHolder`.

Generated folders are named sequentially:

- `CTCM-S1`
- `CTCM-S2`
- `CTCM-S3`

Each site contains:

- `index.html`
- `assets/css/site.css`
- `assets/js/site.js`
- `site_config.json`
- `content.json`
- `backend/server.py`
- `backend/admin.html`
- `backend/admin.css`
- `backend/admin.js`

## Editing Generated Sites

Each generated site includes a small local backend for content editing only.
From inside a generated site folder, run:

```bash
python3 backend/server.py
```

Then open:

```text
http://127.0.0.1:8765
```

The backend shows a visual editing version of the front end. Text is editable
directly on the page, links are edited beside the relevant button, and pictures
can be dragged onto the image slot where they should appear. If a future block
adds a picture slider, select the slide/image slot first, then drop the picture
onto the selected slot.

Dropped local image files are converted in the browser to WebP data URLs before
they are saved. The conversion sizes each image to the selected slot and uses a
contain fit, so the picture is as large as possible while remaining fully visible
inside its allotted space.

Configurator item prices are stored as internal numeric prices. If you type a
formatted value such as `$25.50`, the backend saves it as `25.50` so totals keep
working. Total-price displays are calculated, not free-edited: use the base item
cost and configuration multiplier controls to adjust total pricing.

It does not expose font choices, font sizes, button placement, layout, spacing,
or CSS controls. Those remain locked in the block functions.
