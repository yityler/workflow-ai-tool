# GitHub tools to upgrade the AI workflow tool

## LiteLLM
https://github.com/BerriAI/litellm
One unified function to call ~100 LLM providers (Mistral, Cohere, etc.) in the same format, with built-in token and cost tracking.

Pros
- One completion() call replaces the three separate call_mistral/reka/cohere functions.
- Returns token usage in a consistent shape and can track cost, so the hardcoded price table can mostly go.
- Works with ~100 providers, so adding a new model is trivial later.

Cons
- One more dependency to install and learn.
- Abstracts away provider-specific options, so some niche features get harder to reach.

## rank_bm25
https://github.com/dorianbrown/rank_bm25
A small library that ranks text by keyword relevance using the BM25 algorithm.

Pros
- Proper keyword ranking (BM25) instead of the raw word-overlap in retrieve().
- Tiny, pure Python, no embeddings or extra services.
- Almost a drop-in for what retrieve() already does.

Cons
- Still keyword-based, so it misses synonyms (a "tax" question won't match "GST").
- You manage the index yourself; it doesn't persist anything.

## sentence-transformers
https://github.com/UKPLab/sentence-transformers
Turns text into embeddings (number vectors) so you can search by meaning rather than exact words.

Pros
- Embeds chunks by meaning, so retrieval matches related wording, not just exact words.
- Big quality jump over the current overlap scoring.

Cons
- Downloads a model and needs more memory/CPU than BM25.
- Overkill if the knowledge base stays small.

## Chroma
https://github.com/chroma-core/chroma
A vector database that stores those embeddings and finds the closest matches to a query.

Pros
- Stores and searches the embeddings so retrieval persists between runs.
- Simple local setup, pairs naturally with sentence-transformers.

Cons
- Another moving part to run and keep in sync with your documents.
- Unnecessary if you stick with BM25 or a tiny doc.

## Instructor
https://github.com/567-labs/instructor
Forces an LLM's output into a defined structure (a Pydantic model) instead of free text, with validation and retries.

Pros
- Makes the model return a structured cart (items, subtotal, GST, total) via a Pydantic schema instead of free text, so the checkout math is reliable.
- Built-in validation and automatic retries.
- Has a from_provider interface and supports Mistral/Cohere, so it fits the multi-provider setup.

Cons
- Adds Pydantic models and a bit of structure to the code.
- Not needed for plain chat replies, only for the structured parts.

## tiktoken
https://github.com/openai/tiktoken
A fast tokenizer that counts the actual tokens in a piece of text.

Pros
- Counts real tokens instead of words, so the cost numbers and the "minimize tokens" before/after are honest.
- Lets you check token counts before sending.

Cons
- Its tokenizer is OpenAI's, so counts are approximate for Mistral/Cohere/Reka.
- Small extra step for something the API already reports after the call.

## Langfuse
https://github.com/langfuse/langfuse
A tool that logs and traces every LLM call (prompt, tokens, cost, latency) into a dashboard.

Pros
- Logs each request so there's history and a dashboard instead of numbers that vanish.
- Drops into LiteLLM, so cheap to add if you switch to that.

Cons
- Another service to run or an account to set up.
- More than you need if you only ever look at one response at a time.

## Ragas
https://github.com/explodinggradients/ragas
A library that scores how good RAG answers are (e.g. faithfulness and relevance).

Pros
- Scores RAG answers on faithfulness and relevance, so you can tell if turning RAG on actually helps.
- Directly useful for the "what to improve" part of the assignment.

Cons
- Adds an evaluation step and some setup.
- Only relevant once RAG is doing real work.
