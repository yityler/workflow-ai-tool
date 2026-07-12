"""
llm_chat.py — a simple Gradio chat interface for three free LLMs.

Pick a model (Mistral / Reka / Cohere), type a prompt, and get back:
  - the model's response
  - a token + cost breakdown (input tokens & cost, output tokens & cost, total)
  - an optional NLTK "token minimizer" that strips stopwords to shrink the prompt

Run:
  pip install -r requirements.txt
  python llm_chat.py
Then open the local URL it prints (e.g. http://127.0.0.1:7860).
(The first run auto-downloads NLTK's stopword list.)

API keys are read from a textbox in the app, or from environment variables:
  export MISTRAL_API_KEY="..."
  export REKA_API_KEY="..."
  export COHERE_API_KEY="..."
"""

import os
import re
import time
import gradio as gr
import requests
import nltk
from nltk.corpus import stopwords


# --- NLTK token minimizer -----------------------------------------------------
_STOPWORDS = None


def _get_stopwords():
    """Load English stopwords, downloading them once if needed."""
    global _STOPWORDS
    if _STOPWORDS is None:
        try:
            _STOPWORDS = set(stopwords.words("english"))
        except LookupError:
            nltk.download("stopwords")
            _STOPWORDS = set(stopwords.words("english"))
    return _STOPWORDS


def count_words(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def minimize_prompt(text: str) -> str:
    """Remove common stopwords (the, is, a, of, ...) to shrink the prompt."""
    sw = _get_stopwords()
    words = re.findall(r"\b[\w']+\b", text)
    kept = [w for w in words if w.lower() not in sw]
    return " ".join(kept)


# --- One call function per provider -------------------------------------------
# Each returns (response_text, input_tokens, output_tokens).

def call_mistral(prompt: str, key: str):
    res = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "mistral-small-latest",
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    data = res.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    usage = data.get("usage", {})
    text = data["choices"][0]["message"]["content"]
    return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def call_reka(prompt: str, key: str):
    res = requests.post(
        "https://api.reka.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "reka-flash",
              "messages": [{"role": "user", "content": prompt}]},
        timeout=60,
    )
    data = res.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    usage = data.get("usage", {})
    text = data["choices"][0]["message"]["content"]
    return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def call_cohere(prompt: str, key: str):
    res = requests.post(
        "https://api.cohere.ai/v1/chat",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": "command-r-08-2024", "message": prompt},
        timeout=60,
    )
    data = res.json()
    if "message" in data and "text" not in data:
        raise RuntimeError(data["message"])
    meta = data.get("meta", {})
    tokens = meta.get("tokens") or meta.get("billed_units") or {}
    return data["text"], tokens.get("input_tokens", 0), tokens.get("output_tokens", 0)


# --- Provider registry: pricing is per 1,000,000 tokens (input, output) -------
PROVIDERS = {
    "Mistral (Mistral Small)": {"fn": call_mistral, "env": "MISTRAL_API_KEY", "price": (0.20, 0.60)},
    "Reka (Reka Flash)":       {"fn": call_reka,    "env": "REKA_API_KEY",    "price": (0.30, 0.80)},
    "Cohere (Command R)":      {"fn": call_cohere,  "env": "COHERE_API_KEY",  "price": (0.15, 0.60)},
}


def chat(provider_name: str, api_key: str, minimize: bool, prompt: str):
    cfg = PROVIDERS[provider_name]
    key = (api_key or "").strip() or os.environ.get(cfg["env"], "")

    if not key:
        return "", f"No API key. Paste one above or set {cfg['env']} in your terminal."
    if not (prompt or "").strip():
        return "", "Enter a prompt first."

    original = prompt.strip()
    sent = original
    if minimize:
        trimmed = minimize_prompt(original)
        sent = trimmed if trimmed else original  # don't send an empty prompt

    start = time.perf_counter()
    try:
        text, in_tok, out_tok = cfg["fn"](sent, key)
    except Exception as e:
        return "", f"Error: {e}"
    elapsed = time.perf_counter() - start

    in_price, out_price = cfg["price"]
    in_cost = in_tok / 1_000_000 * in_price
    out_cost = out_tok / 1_000_000 * out_price
    total_cost = in_cost + out_cost

    breakdown = (
        "| | Tokens | Cost (USD) |\n"
        "|---|---:|---:|\n"
        f"| **Input** | {in_tok} | ${in_cost:.6f} |\n"
        f"| **Output** | {out_tok} | ${out_cost:.6f} |\n"
        f"| **Total** | {in_tok + out_tok} | ${total_cost:.6f} |\n\n"
        f"**Response time:** {elapsed:.1f} sec\n\n"
        f"_Pricing used: ${in_price:.2f} / 1M input, ${out_price:.2f} / 1M output._"
    )

    if minimize:
        orig_words = count_words(original)
        sent_words = count_words(sent)
        # Estimate what the original would have cost by scaling the real token count.
        est_orig_tokens = round(in_tok * orig_words / sent_words) if sent_words else in_tok
        saved_tokens = max(est_orig_tokens - in_tok, 0)
        saved_cost = saved_tokens / 1_000_000 * in_price
        breakdown += (
            "\n\n**NLTK token minimizer (stopword removal)**\n\n"
            f"- Words: {orig_words} → {sent_words} after trimming\n"
            f"- Sent prompt: `{sent}`\n"
            f"- Input tokens actually sent: **{in_tok}**\n"
            f"- Estimated input tokens *without* minimizing: ~{est_orig_tokens}\n"
            f"- Estimated savings: ~{saved_tokens} tokens (~${saved_cost:.6f})"
        )

    return text, breakdown


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Free LLM Chat") as demo:
        gr.Markdown("# Free LLM Chat\nPick a model, enter a prompt, and see the response "
                    "plus a token & cost breakdown.")
        with gr.Row():
            provider = gr.Dropdown(
                choices=list(PROVIDERS.keys()),
                value=list(PROVIDERS.keys())[0],
                label="Model",
            )
            api_key = gr.Textbox(label="API key", type="password",
                                 placeholder="Paste key (or set it as an environment variable)")
        minimize = gr.Checkbox(label="Minimize tokens (NLTK stopword removal)", value=False)
        prompt = gr.Textbox(label="Prompt", placeholder="Ask something…", lines=6)
        submit = gr.Button("Send", variant="primary")
        out = gr.Textbox(label="Response", lines=12)
        cost = gr.Markdown(label="Token & cost breakdown")

        inputs = [provider, api_key, minimize, prompt]
        submit.click(fn=chat, inputs=inputs, outputs=[out, cost])
        prompt.submit(fn=chat, inputs=inputs, outputs=[out, cost])
    return demo


if __name__ == "__main__":
    build_ui().launch()
