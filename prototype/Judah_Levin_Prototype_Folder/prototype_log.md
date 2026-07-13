# Prototype Log — page_generator.py

A record of how the storefront generator was built and refined, iteration by iteration.
The prototype generates an enterprise's in-store kiosk screens (home, product, checkout pages)
from their catalog and brand color, with token optimization as the core architecture.

## Iteration 1 — Initial pipeline (token-optimized architecture)

Built the first working version around six cost-reduction decisions:

| # | Decision | Effect |
|---|----------|--------|
| 1 | Template-once: the LLM designs ONE page template as compact JSON; every page is rendered by Python | 0 tokens per page; measured 94% saving vs naive per-page generation |
| 2 | Structured specs (Instructor + Pydantic) instead of free-form HTML | 5-10x smaller outputs, machine-validated |
| 3 | Catalog slicing: design calls see category names only, never the full catalog | Input stays tiny at any catalog size |
| 4 | Diff edits: "change the header" sends one section's JSON, not the page | ~70-90% saved per edit |
| 5 | Template cache on disk per (brand, color, page type) | Repeat generations cost 0 tokens |
| 6 | Model routing: designs and small edits go to different models | Edits run on a cheaper model |

Also added: sample enterprise catalog (catalog.json), naive-vs-optimized cost table in the UI,
session savings tracker.

## Iteration 2 — Provider changes

- Started on Mistral (design + edits on mistral-small-latest).
- Switched to Gemini (gemini-2.0-flash for designs, flash-lite for edits) per team decision.
- Switched to OpenAI (gpt-5-mini / gpt-5-nano) per team decision; failed at runtime because the
  account had no billing — OpenAI has no free tier.
- Settled on Mistral: mistral-small-latest for designs, ministral-8b-latest for edits.
- Lesson recorded: provider swaps are a two-line change in the MODELS config thanks to LiteLLM;
  added a friendly quota/billing error message instead of a raw crash.

## Iteration 3 — First output review: schema and prompt refinement

First generated pages were nearly empty. Diagnosis: the prompt let the model invent arbitrary
section ids the renderer didn't recognize, so product name and price never rendered; plus
white-on-white text in dark mode.

Fixes, and the principle behind them:
- Section `type` became a closed vocabulary (Literal) — the model cannot return a section the
  renderer can't draw. Rule: use the schema for requirements, the prompt for intent.
- Pydantic validators enforce required sections (product page must have details + price + CTA);
  a validation failure makes Instructor auto-retry with the error message.
- Prompt rewritten as a design brief: kiosk context (arm's length, 3-second scannability),
  audience, tone, concrete limits with an example heading.
- Explicit text colors fixed the dark-mode invisibility.

## Iteration 4 — Design research round (35+ sources)

Researched UI design fundamentals: Nielsen Norman Group visual design principles, Refactoring UI
(numeric rules), all 30 Laws of UX, Baymard checkout research, kiosk touchscreen standards,
8-point grid, 60-30-10 color rule. Encoded the findings in three layers:

- Renderer: 8-pt spacing grid, 3-size type scale, 60-30-10 color discipline, soft two-layer
  shadows, tinted product tiles (enclose-don't-scale), 56px+ CTA button with automatic WCAG
  contrast check, Baymard-style checkout (muted math, one dominant total, single CTA).
- Schema: model picks a theme, writes microcopy; validators encode Von Restorff (max one promo)
  and Miller's law (max 6 sections).
- Prompt: "senior retail UX designer" brief with design direction.

Also fixed two bugs: ghost text (Gradio dark theme overrides inherited colors — every text
element now sets an explicit inline color) and a template cache polluted by a mock test.

## Iteration 5 — Full-page layouts + home page

Feedback: output looked like a card, not a page. Rebuilt renderers into full page anatomy
(header bar, hero band, content bands, footer bar) and added a third page type:

- Home/browse screen (new): hero with CTA, category chips, product grid rendered from the
  catalog in Python (zero tokens per card), one promo band.
- Product page: two-column layout — visual tile | name, description, price, CTA.
- Checkout: two-column — itemized order card | payment panel with total and payment methods.

Now 3 design calls on first run (home, product, checkout); all pages still render token-free.

## Iteration 6 — The design-knowledge RAG (major architecture change)

Feedback: pages looked "AI-generated." Research confirmed the "AI slop" aesthetic is documented:
uniform padding/radius/card heights, everything centered, flat rhythm, indigo-purple defaults,
vague aspirational copy. Response:

- Created design_knowledge.txt — a curated design library sourced from human designers:
  Dieter Rams (ten principles), Robin Williams (Contrast/Repetition/Alignment/Proximity),
  Massimo Vignelli (typography discipline), Johannes Itten (color harmony), Refactoring UI,
  Baymard, kiosk ergonomics, color psychology, microcopy voice.
- Restructured the prompt: COMPANY BRIEF (client-specific facts only) + DESIGN KNOWLEDGE
  (chunks retrieved by BM25 per page type) + short output instruction. General design wisdom
  no longer lives in the prompt at all.
- Token benefit: only the relevant ~6 of 19 knowledge chunks (~800 of ~2,450 tokens) are sent
  per design call; the report shows the retrieval stats.
- Palette derivation from the single brand color (HSL tonal-scale method): backgrounds are
  high-lightness low-saturation tints of the brand hue; text is a dark desaturated shade; even
  hairlines carry the hue. The static grey themes were deleted — every client gets hue-tinted
  neutrals derived from their own color.
- Anti-generic renderer tweaks: left-aligned hero (editorial asymmetry), varied corner radii.

## Iteration 7 — Web writing knowledge

Added two writing topics to the knowledge base, from Nielsen Norman eyetracking research
(people scan in an F-pattern, read ~20-28% of words — front-load everything, numerals not
words, one idea per paragraph) and Steve Krug (happy talk must die, omit needless words,
verb-first button labels, never "Click here"). Retrieval queries updated so all three page
types pull the writing guidance.

## Iteration 8 — Brand-matched typography

Researched font psychology by industry (serifs read as heritage/luxury/trust; geometric
sans as modern/tech; rounded sans as warm/friendly; condensed display as bold/fashion) and
curated Google Fonts pairings. Changes:

- New FONTS table with five researched pairings (display + body): elegant (Playfair
  Display/Lato), friendly (Nunito/Nunito Sans), bold (Bebas Neue/Open Sans), modern
  (Space Grotesk/Work Sans), classic (Lora/Source Sans 3).
- PageTemplate gained a `font` field (bounded Literal choice with a default so old cached
  templates still load) — the model picks the personality that matches the client's name
  and story.
- Renderer loads the pairing from Google Fonts and applies the display face to brand name,
  heroes, product names, and grid headings via a scoped .disp class; body text uses the
  workhorse face. Replaces the system-font default — the last big "generic AI look" tell.
- New knowledge-base topic "Typeface personality — matching the font to the business";
  retrieval queries updated (and k raised to 7) so all three page types receive it.
- Process note: this iteration was the first logged under the new rule (a PostToolUse hook
  now reminds that every page_generator.py change gets a prototype_log.md entry).

## Iteration 9 — Trade-specific font matching

Feedback: the font should follow what the business SELLS, not an abstract mood — a candle
store suits a cursive script, a sports-equipment store suits a bold display face. Changes:

- Added a sixth font personality, "handmade": Dancing Script headings (artisanal cursive)
  paired with Karla body for legibility — for candle shops, bakeries, florists, boutique
  makers. Script is confined to headings; body stays plain sans.
- The design prompt now maps concrete trades to personalities (candles/bakery=handmade,
  sports/streetwear=bold, bank/pharmacy=classic, jewellery=elegant, toys/family=friendly,
  gadgets=modern) and instructs the model to match the trade, not a generic mood.
- The knowledge-base typeface topic was extended with the script category and the same
  trade examples, so retrieval teaches the mapping on every design call.

## Current state

- Files: page_generator.py (pipeline + UI), catalog.json (sample enterprise catalog),
  design_knowledge.txt (20-topic design library), token_optimizer.py (shared module),
  templates/ (cache).
- Runs at http://127.0.0.1:7861 with a Mistral API key.
- The refinement loop going forward: improving output quality means editing
  design_knowledge.txt — no code or prompt changes required. Retrieval picks up new topics
  automatically.
