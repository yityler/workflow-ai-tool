# DeepSeek API Pricing

Prices are in USD per 1 million tokens, according to DeepSeek's official API documentation.

| Model name | Version | Input, cache hit | Input, cache miss | Output |
|---|---|---:|---:|---:|
| `deepseek-v4-flash` | DeepSeek-V4-Flash | $0.0028 | $0.14 | $0.28 |
| `deepseek-v4-pro` | DeepSeek-V4-Pro | $0.003625 | $0.435 | $0.87 |

Notes:

- DeepSeek lists input token pricing separately for cache hits and cache misses.
- `deepseek-chat` and `deepseek-reasoner` correspond to non-thinking and thinking modes of `deepseek-v4-flash`, respectively, for compatibility.
- Source checked: DeepSeek API Docs, "Models & Pricing" (`https://api-docs.deepseek.com/quick_start/pricing`).
