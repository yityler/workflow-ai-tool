# CTCM V1.0 Block Functions

This folder contains reusable Python block functions distilled from the
`cornerstone-tabs-configurator-metafields` product-page work.

The blocks are intentionally small and metadata-rich so another program can use
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
use only the required shell/style/script blocks, then opt into media, tabs,
configurator, metafields, or cart behavior as needed.

