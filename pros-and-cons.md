# Pros & Cons

### Mistral AI (Mistral Small)
| Pros | Cons |
|------|------|
| Very fast — while testing, it was consistently the quickest AI | Smaller models trail frontier models (Claude / Gemini / GPT) on the hardest reasoning |
| Works directly from the browser (CORS-friendly) — responds without a backend | Smaller ecosystem of tools and integrations than the big providers |
| Many models are open-weight (Apache 2.0), so they can be self-hosted | |
| OpenAI-compatible API → simple, familiar request format | |
| Strong at code and multilingual tasks for its size | |
| EU-based → good for data-residency concerns | |

### Reka AI (Reka Flash)
| Pros | Cons |
|------|------|
| Natively multimodal — understands text, images, audio, and video | Small company → fewer docs, examples, and community help |
| OpenAI-compatible API → familiar request format | Blocks browser CORS → needs a backend proxy to respond in the app |
| Independent, less common pick → makes the project stand out | Less battle-tested; model names / availability can change |

### Cohere (Command R)
| Pros | Cons |
|------|------|
| Built for RAG, search, and tool-use / agents — strong at retrieval-augmented generation | Blocks browser CORS → needs a backend proxy to respond in the app |
| Strong multilingual support | Tuned for RAG over open-ended chat, so general conversation can feel weaker |
| Simple API with good documentation | Slowest and most inconsistent response times in testing (up to ~49 sec) |
| | Smaller consumer-facing ecosystem |
