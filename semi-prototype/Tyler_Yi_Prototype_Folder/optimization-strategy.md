# Token Optimization Strategy

How our AI storefront platform keeps LLM costs down without reducing output quality.
Role owner: token reduction / LLM optimization. Prototype code: `page_generator.py`,
`token_optimizer.py`, sample input: `catalog.json`.

## The product and where tokens burn

Our platform lets an enterprise (a retailer using Smart Stickies RFID checkout) upload its
catalog and brand, and the AI generates its in-store screens: product pages, the self-checkout
page, and related layouts.

The naive way to build this is to ask the LLM to write one full HTML page per product. That
fails at enterprise scale:

| | Calls | Tokens per page | 10,000-SKU catalog |
|---|---|---|---|
| Naive (LLM writes each page) | 1 per product | ~300 in / ~1,500 out | ~18M tokens per full generation |
| Our pipeline | 1 per page *type* | one-time | ~800 tokens total, then 0 per product |

Token costs concentrate in three places, and each needs a different fix:
1. **Input tokens** — catalogs, brand guidelines, page context sent to the model.
2. **Output tokens** — the generated layouts (priced ~3x higher than input).
3. **The calls themselves** — repeated or unnecessary generations.

## The six methods (implemented in the prototype)

### 1. Template-once generation — the core architecture decision
The LLM designs ONE page template per page type (product page, checkout page) as a compact
JSON spec. Every actual page is then rendered by plain Python code filling product data into
the template — zero tokens per page.

- Measured in the prototype: 7 pages cost 780 tokens instead of ~12,600 — **94% saved**.
- The saving grows with catalog size: 12 products or 10,000 SKUs is still one design call.
- Quality is *better*, not worse: every product page is perfectly consistent.

### 2. Structured layout specs instead of HTML
The model returns a small validated JSON object (Pydantic schema via Instructor), not verbose
HTML. Output drops 5–10x, and the result is machine-checkable — a malformed layout is caught
and retried automatically instead of shipping a broken page.

### 3. Template caching
Same brand + page type = the saved template is reused from disk. Zero tokens. Verified in the
prototype: a second generation run produced 13 pages for 0 tokens. (The chat prototype also has
an exact + *semantic* response cache — similar questions reuse earlier answers.)

### 4. Catalog slicing
The design call never sees the full catalog — only the category names (a dozen tokens instead
of the whole product database). Any task that needs product context gets only the fields it
requires (`slice_catalog()` helper).

### 5. Diff-based edits
When a customer asks for a change ("make the header friendlier"), we send the LLM only that one
section's JSON, not the whole template or page. The prototype reports the tokens avoided on
every edit.

### 6. Model routing
Full template designs and small edits go through separate routes (`MODELS` config). Small jobs
can be pointed at a cheaper model without touching the pipeline code.

## Supporting methods (in `token_optimizer.py`, reusable anywhere)

| Method | What it does | When to use |
|---|---|---|
| `normalize()` | Collapses extra whitespace | Always — free, zero risk |
| `compress()` | LLMLingua-2 learned compression, measured −42% while preserving quantities and meaning | Long context blocks (brand guidelines, policies) |
| `ResponseCache` | Exact + semantic answer reuse (100% saving on hits) | Any repeated-question surface (kiosk assistant) |
| `filter_chunks()` | Adaptive RAG — drop low-relevance context chunks | Any RAG retrieval |
| `suggest_max_tokens()` + concise instruction | Caps output length by question type | All chat-style calls — output is the expensive side |
| `strip_stopwords()` | NLTK stopword removal | Optional only — riskiest for meaning (can drop negations) |
| `count_tokens()` / `SavingsTracker` | tiktoken counting + per-method session savings report | Measurement — proves the savings |

## Evidence from our own experiments (Week 2 findings)

Our stopword experiment (12 runs, 3 models, 2 prompts — see `stopword-findings.md`) showed:
- Input-side trimming alone cut input tokens 40–47% but barely moved **total** cost, because
  output tokens dominate the bill on generation-heavy tasks.
- Conclusion baked into this strategy: the biggest levers are **avoiding calls entirely**
  (templates, caching) and **shrinking outputs** (structured specs, output caps) — input
  trimming is the garnish, not the meal.

## Measured results (prototype, mocked baseline)

| Scenario | Naive tokens | Pipeline tokens | Saving |
|---|---:|---:|---:|
| Generate 7 pages (first run) | ~12,600 | 780 | 94% |
| Regenerate 13 pages (cache) | ~25,200 | 0 | 100% |
| Edit one section | whole template each time | one section only | ~70–90% per edit |

Note: the naive baseline (~300 in / ~1,500 out per page) is an estimate. To make it bulletproof,
run one real full-HTML-per-page generation and substitute its actual counts.

## How to run the prototype

```
pip install -r requirements.txt
python page_generator.py        # http://127.0.0.1:7861
```

Enter a brand name, brand color, and a Mistral API key (free tier at
https://console.mistral.ai/api-keys).
"Generate store" designs the templates (one-time) and renders the checkout page plus product
pages, with a naive-vs-optimized cost table. "Apply edit" demonstrates diff-based editing with
tokens-avoided reporting.

The prototype runs on Mistral via LiteLLM with real model routing: full template designs use
`mistral-small-latest`; small diff edits are routed to the cheaper `ministral-8b-latest`.
Swapping providers later is a two-line change in the `MODELS` config.

## Recommendations for the final build

1. Adopt template-once as the core generation architecture — it is the difference between the
   platform scaling to enterprise catalogs or not.
2. All model outputs should be structured (Pydantic schemas), never free-form HTML/text.
3. Cache templates per (brand, page type, version); invalidate on brand changes only.
4. Route edits to a cheaper model than designs once a second provider is configured.
5. Keep the `SavingsTracker` wired in production — the per-customer savings report is itself a
   selling point for the B2B product ("our AI platform costs X, a naive one costs 20X").
