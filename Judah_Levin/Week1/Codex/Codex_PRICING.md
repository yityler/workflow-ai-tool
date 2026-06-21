# Codex Prices

Sources checked: [Codex pricing](https://developers.openai.com/codex/pricing) and [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), accessed June 14, 2026.

## Codex Free Plan

The Codex docs say Codex is included in ChatGPT Free, Go, Plus, Pro, Business, Edu, and Enterprise plans. The Free plan is listed at **$0/month**. The docs do not list a separate input-token or output-token price for Codex usage inside the ChatGPT Free plan.

| Codex access option | Monthly price | Input price / 1M tokens | Output price / 1M tokens | Notes |
|---|---:|---:|---:|---|
| ChatGPT Free with Codex | $0/month | Not listed separately | Not listed separately | Free-plan Codex access is included with ChatGPT Free rather than priced per Mtok in the Codex pricing page. |

## Codex API Token Pricing

For API-key usage, Codex is billed by the API model token rates. The current Codex-specific API model listed in OpenAI's API pricing page is `gpt-5.3-codex`.

| Codex API model | Processing tier | Input price / 1M tokens | Cached input price / 1M tokens | Output price / 1M tokens |
|---|---|---:|---:|---:|
| `gpt-5.3-codex` | Standard | $1.75 | $0.175 | $14.00 |
| `gpt-5.3-codex` | Priority | $3.50 | $0.35 | $28.00 |
