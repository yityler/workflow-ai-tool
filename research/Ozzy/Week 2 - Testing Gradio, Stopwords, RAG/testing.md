# AI Model Testing — Ozzy
**Week 2 of Summer Ladder Internship with SmartStickies**

### Task Overview
* Test the Gradio python library, Stopword implementation, and Retrival Augumented Generation




> All three models were called through OpenAI-compatible chat-completions endpoints — `gpt-oss-20b` and `Llama-3.1-8B` via NVIDIA NIM, and `Phi-4-mini-instruct` captured against an earlier NVIDIA NIM configuration (before it was later moved to GitHub Models).

For background on licensing, pros/cons, and hardware requirements for each model, see the [Week 1 Markdown](Ozzy/Week 1 - AI Model Research/aimodelresearch.mdOzzy/Week 1 - AI Model Research/aimodelresearch.md). Cost comparisons across providers are [here](Ozzy\Week 1 - AI Model Research\pricing.md).

### Contents
* [Gradio / Stopwords](#Gradio/Stopwords)
* [1. `openai/gpt-oss-20b`](#1-openaigpt-oss-20b)
* [2. `microsoft/Phi-4-mini-instruct`](#2-microsoftphi-4-mini-instruct)
* [3. `meta-llama/Llama-3.1-8B`](#3-meta-llamallama-31-8b)
* [Side-by-Side Comparison](#side-by-side-comparison)
* [Other Thoughts](#other-thoughts)

---

## Gradio/Stopwords

Three prompts were sent to each model, each asking for a fairly large, code-heavy deliverable:

| # | Prompt | Topic |
| :-: | :--- | :--- |
| 1 | Design a modern, responsive website for a [business type]. Include a homepage with hero section, services, testimonials, and CTA; plus About, Services, and Contact pages. Use clean UI, mobile-first layout, smooth animations, SEO-friendly structure, and accessible design. Generate complete HTML/CSS/JS (or React) code with organized components and production-ready styling.| Full website (HTML/CSS/JS or React) |
| 2 | Write a Python program that implements a fully playable chess game. Use clean OOP design, a board representation, and enforce official chess rules (legal moves, check, checkmate, castling, en passant, promotion). Include a simple UI (console or Pygame), move validation, game state tracking, and an option for AI opponent with basic strategy.| Chess engine with OOP design |
| 3 | Create a Python application that analyzes and visualizes real-world weather data. Use an external API to fetch current and historical weather for any user-specified city. Process the data to display trends like temperature changes, humidity, and precipitation. Build a clean CLI or simple web interface, include error handling, caching for efficiency, and generate interactive charts using a plotting library. Ensure the code is modular, well-documented, and easy to extend for future features like forecasting or alerts.| Weather CLI/web app |

Each prompt was sent twice per model — once as-is (**unfiltered**) and once with stopwords removed (**filtered**) — for 6 calls per model, 18 calls total. For every call I logged prompt tokens, completion tokens, `finish_reason`, and wall-clock time.

---

## 1. `openai/gpt-oss-20b`

> Fastest average response of the three, but its chain-of-thought reasoning crowded out the actual answer entirely.

### Performance Summary

| Prompt | Mode | Prompt Tokens | Completion Tokens | Time (s) |
| :--- | :--- | :-: | :-: | :-: |
| Website | Unfiltered | 150 | 1024 | 7.38 |
| Chess | Unfiltered | 137 | 1024 | 6.83 |
| Weather | Unfiltered | 159 | 1024 | 7.31 |
| Website | Filtered | 134 | 1024 | 7.33 |
| Chess | Filtered | 128 | 1024 | 7.03 |
| Weather | Filtered | 137 | 1024 | 7.35 |

**Average latency: ~7.20s** — every call hit the 1024-token cap (`finish_reason: 'length'`).

### Sample Exchange
For the website prompt, `gpt-oss-20b` opened with a full React project layout (`marketing-agency/public/...`, `src/components/...`) before getting cut off mid-CSS — typical of its responses.

The **chess prompt (unfiltered) is the standout result**: the model spent its *entire* 1024-token budget on internal reasoning (visible in the `reasoning_content` field — outlining `Piece`, `Board`, and `Game` class designs, castling/en passant logic, etc.). However, the content answer was ever written.

### Observations

| Pros | Cons |
| :--- | :--- |
| Fastest average latency (~7.2s) despite being a reasoning model | Reasoning consumed the *entire* token budget on 1 of 6 calls, returning no answer at all |
| Exposes full chain-of-thought via `reasoning_content`, useful for debugging | Without a `reasoning_content` guard in the app, a `None` response crashes downstream `word_tokenize()` calls |
| Filtered-prompt runs never showed the empty-content issue in this batch | Reasoning effort isn't capped by default — needs an explicit low-effort hint or a larger token budget to reliably leave room for the actual answer |

---

## 2. `microsoft/Phi-4-mini-instruct`

> Consistently the fastest model end-to-end, but every single response in this batch was cut off because of a 256 token cap (which I put on it because it otherwise takes forever to generate)

### Performance Summary

| Prompt | Mode | Prompt Tokens | Completion Tokens | Time (s) |
| :--- | :--- | :-: | :-: | :-: |
| Website | Unfiltered | 77 | 256 | 7.32 |
| Chess | Unfiltered | 75 | 256 | 6.61 |
| Weather | Unfiltered | 97 | 256 | 6.64 |
| Website | Filtered | 66 | 256 | 6.30 |
| Chess | Filtered | 66 | 256 | 6.13 |
| Weather | Filtered | 75 | 256 | 7.02 |

**Average latency: ~6.67s** — every call hit the 256-token cap (`finish_reason: 'length'`); none came close to finishing.

### Sample Exchange
The website prompt produced a reasonable opening ("Sure, I'll design a modern, responsive website for a law firm...") and a clean project folder tree, but the response was cut off after just the file listing — before any actual HTML/CSS/JS appeared. Same pattern on the chess and weather prompts: a solid plan, then a cut off in a mid-class-definition.

### Observations

| Pros | Cons |
| :--- | :--- |
| Lowest average latency of the three models | 256-token cap meant **0 of 6** responses were ever complete |
| Picks a sensible default when the prompt is under-specified (e.g. chose "law firm" for the `[business type]` placeholder) | Cut off well before reaching any working code in every test |
| Quick to start writing — no visible "thinking" delay like `gpt-oss-20b` | Confirms the model needs noticeably more than 256 output tokens for code-generation tasks of this size |

---

## 3. `meta-llama/Llama-3.1-8B`

> Slowest of the three by roughly 2x, but produced the most code before running into the same 1024-token wall.

### Performance Summary

| Prompt | Mode | Prompt Tokens | Completion Tokens | Time (s) |
| :--- | :--- | :-: | :-: | :-: |
| Website | Unfiltered | 110 | 1024 | 12.16 |
| Chess | Unfiltered | 107 | 1024 | 10.91 |
| Weather | Unfiltered | 129 | 1024 | 14.19 |
| Website | Filtered | 99 | 1024 | 11.68 |
| Chess | Filtered | 98 | 1024 | 14.67 |
| Weather | Filtered | 107 | 1024 | 11.46 |

**Average latency: ~12.51s** — every call hit the 1024-token cap (`finish_reason: 'length'`).

### Sample Exchange
The chess prompt produced the most structurally complete output of any model in this test: full `Piece`/`King`/`Queen`/`Rook`/`Bishop`/`Knight`/`Pawn` class hierarchy, a `Board` class with `initialize_board()` populating all 32 starting pieces, a `print_board()` method, and a partially-written `is_valid_move()` — all before hitting the cap mid-`isinstance` check.


### Observations

| Pros | Cons |
| :--- | :--- |
| Most complete, furthest-progressed code of the three models before truncation | Roughly 2x slower than `gpt-oss-20b` or `Phi-4-mini-instruct` on identical prompts |
| No empty-response failures like `gpt-oss-20b`'s reasoning-tax issue | Still truncated on **6 of 6** calls — 1024 tokens isn't enough for a full chess engine or website either |
| Detailed NVIDIA NIM telemetry (KV cache hit rate, prefill/decode timing) available for deeper tuning | Near-zero KV cache hit rate across calls — prompts weren't being reused/cached between requests |

---

## Side-by-Side Comparison

| Model | Avg Latency | Calls Truncated | Notable Issue |
| :--- | :-: | :-: | :--- |
| `gpt-oss-20b` | ~7.2s | 6/6 | 1 of 6 calls returned **zero content** — reasoning ate the whole budget |
| `Phi-4-mini-instruct` | ~6.7s | 6/6 | Fastest, but the 256-token cap used here was far too tight for any prompt |
| `Llama-3.1-8B` | ~12.5s | 6/6 | Slowest, but got furthest into working code before being cut off |

**Stopword filtering:** removing English stopwords cut prompt length by roughly **16–25% (avg ~20%)** across all three test prompts. It had no effect on truncation, since that's governed entirely by the output `max_tokens` setting, not input length — and response openings were qualitatively similar whether the prompt was filtered or not.

---

## Other Thoughts

1. **Output budget matters more than model choice** for these prompts — all three models hit their cap on every single call. Before drawing conclusions about model "quality" on tasks like this, the token budget needs to be raised well past 1024 (closer to 2k–4k) so a model actually has room to finish. (which I did not do because the models ended up taking ~8 minutes to generate 1 answer)
2. **Reasoning models need a separate budget strategy.** `gpt-oss-20b`'s empty-response failure on the chess prompt suggests reasoning-capable models should either get a larger ceiling than non-reasoning models, or an explicit low-reasoning-effort hint, so the visible answer doesn't get crowded out.
3. **Stopword filtering are not useful for outputs** — it trims tokens on the input side, but since the outputs end up being way larger, the savings become very marginal. It trims significantly more the large the prompt is. It would likely be more helpful to find a way to cut down on output tokens.
4. A natural next test: rerun all three models at a consistent, larger `max_tokens` (e.g. 4096) to see which one actually finishes a complete response first, rather than just which one runs fastest per token.
