# Prototype #2 — Merged Storefront Generator

One app combining the best of both earlier prototypes:
the rich input system (business brief, style dropdowns, reference-document RAG) from the
input module, the FLUX product-image step from the integrated pipeline, and the
token-optimized storefront engine (design-knowledge RAG, brand-derived palettes,
trade-matched fonts, template-once generation) from Tyler's prototype.

## What it does

Describe a business, optionally upload reference documents, and get a complete branded
storefront for in-store RFID kiosks: a home/browse screen with product grid, product detail
pages, and a checkout screen — plus a generated product image. Every generation prints a
token report: what each step cost, what the cache saved, and a naive-vs-optimized comparison.

## Credits

This prototype builds directly on the whole team's work:

- Ozzy — the input system this app's form is modeled on (business brief, style options,
  reference-document uploads with RAG) and the prompt-builder concept, from prototype/input.
- Rohan — the FLUX product-image generation (image_gen_hf.py), reimplemented here with a
  provider fix, and the cornerstone layout generator that pioneered integrating the input
  system with structured page generation (semi-prototype/product_generation).
- Judah — the CTCM block system remains a parallel deterministic generation path in
  prototype/Judah_Levin_Prototype_Folder; it is not duplicated here.
- Tyler — the storefront engine, design-knowledge RAG, and token-optimization architecture.

prototype_#2 is the merge of these parts into one runnable app, not a replacement for the
individual folders.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python page_generator.py         # opens on http://127.0.0.1:7861 (or set PORT)
```

## Keys

- Mistral API key (required): paste in the UI, or set the MISTRAL_API_KEY environment
  variable. Free tier: https://console.mistral.ai/api-keys
- Hugging Face token (optional, for the product image): paste in the UI or set HF_TOKEN.
  Free: https://huggingface.co/settings/tokens
- Never commit keys. Use environment variables or a local .env that is gitignored.

## How to use

1. Enter a brand name, brand color, and a business/product description.
2. Optionally pick industry, audience, tone, and style; add notes; upload .txt/.md/.pdf
   reference documents (relevant chunks are retrieved via RAG under a token budget).
3. Catalog: "AI-generated for this brand" (default) invents fitting products from your
   description (cached per brand+description); a bundled stationery sample is available as a
   zero-token fallback.
4. Generate. First run makes up to 4 small structured calls; identical repeats are free
   (template cache). The diff-edit box below changes one section without resending the page.

## Files

| File | Purpose |
|---|---|
| page_generator.py | The whole app: pipeline + UI |
| token_optimizer.py | Shared token-optimization utilities |
| design_knowledge.txt | 20-topic design library (RAG source) — edit this to improve design quality, no code changes needed |
| catalog.json | Bundled zero-token sample catalog |
| requirements.txt | Exact dependencies for this app |
| prototype_log.md | Iteration-by-iteration engineering log |
| optimization-strategy.md | Token-optimization strategy documentation |

Runtime caches (templates/, catalogs/, generated_product_image.png) are created next to the
script on first use and are safe to delete.
