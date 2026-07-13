# CTCM V1.0 Block Functions

This folder contains reusable Python block functions distilled from the
`cornerstone-tabs-configurator-metafields` product-page work.

The blocks are intentionally fine-grained and metadata-rich so another program can use
retrieval-augmented generation to search `block_manifest.json`, pick relevant
blocks, collect required inputs, and assemble a product display page.

## Files

- `ctcm_blocks.py` - callable block functions and assembly helpers.
- `block_manifest.json` - RAG-friendly block catalog with descriptions, inputs,
  dependencies, and required flags.

## Core Idea

The original Cornerstone customization had three major behaviors:

- Custom fields can become product detail tabs.
- `--Category` custom fields can become configurator categories.
- Product and variant metafields can be displayed on the product page.

These blocks recreate those behaviors in portable static-site form. A caller can
use the required `core_runtime` block, then opt into atomic gallery, product,
tab, add-on, and metafield pieces independently. Gallery main image, thumbnails,
and caption are separate blocks; tabs separate heading, navigation, and panels;
add-ons separate catalog, summary lines, total, and action. See
`../CTCM-V1.0_README.md` for the complete AI-oriented dependency and input
catalog.

