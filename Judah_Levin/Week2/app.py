"""A Gradio prompt cleaner for DeepSeek, OpenAI, and Gemini."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

import gradio as gr
from stop_words import get_stop_words


PROVIDERS = {
    "DeepSeek": {
        "key_label": "DeepSeek API key",
        "models": [
            ("DeepSeek V4 Flash · fast and economical", "deepseek-v4-flash"),
            ("DeepSeek V4 Pro · highest capability", "deepseek-v4-pro"),
            ("DeepSeek Chat · compatibility alias", "deepseek-chat"),
            ("DeepSeek Reasoner · compatibility alias", "deepseek-reasoner"),
        ],
    },
    "ChatGPT / OpenAI": {
        "key_label": "OpenAI API key",
        "models": [
            ("GPT-5.5 · flagship", "gpt-5.5"),
            ("GPT-5.4 · balanced", "gpt-5.4"),
            ("GPT-5.4 mini · faster and cheaper", "gpt-5.4-mini"),
        ],
    },
    "Gemini": {
        "key_label": "Gemini API key",
        "models": [
            ("Gemini 3.5 Flash · intelligent and fast", "gemini-3.5-flash"),
            ("Gemini 3.1 Flash-Lite · lowest cost", "gemini-3.1-flash-lite"),
        ],
    },
}

# Standard paid-tier USD rates per one million text tokens, checked 2026-06-21.
# Provider pricing changes; verify these constants before production use.
PRICING = {
    "deepseek-v4-flash": {"input": 0.14, "cached": 0.0028, "output": 0.28},
    "deepseek-v4-pro": {"input": 0.435, "cached": 0.003625, "output": 0.87},
    "deepseek-chat": {"input": 0.14, "cached": 0.0028, "output": 0.28},
    "deepseek-reasoner": {"input": 0.14, "cached": 0.0028, "output": 0.28},
    "gpt-5.5": {"input": 5.00, "cached": 0.50, "output": 30.00},
    "gpt-5.4": {"input": 2.50, "cached": 0.25, "output": 15.00},
    "gpt-5.4-mini": {"input": 0.75, "cached": 0.075, "output": 4.50},
    "gemini-3.5-flash": {"input": 1.50, "cached": 0.15, "output": 9.00},
    "gemini-3.1-flash-lite": {"input": 0.25, "cached": 0.025, "output": 1.50},
}

ENGLISH_STOP_WORDS = frozenset(word.casefold() for word in get_stop_words("english"))


def _dataset_terms(*candidates: str) -> frozenset[str]:
    """Select semantic candidates that exist in the 2025.11.4 stop-word data."""
    return frozenset(word for word in candidates if word.casefold() in ENGLISH_STOP_WORDS)


# The source package does not label semantic categories, so candidate sets stay narrow.
# Dataset membership prevents a generic all-stop-words pass from destroying prompt meaning.
GREETINGS = _dataset_terms("hello", "hi", "greetings", "welcome") | {"hey"}
COURTESY_WORDS = _dataset_terms("please", "thank", "thanks", "dear", "regards") | {
    "kindly",
    "cheers",
}
HONORIFICS = _dataset_terms("mr", "mrs", "ms", "miss") | {
    "sir",
    "madam",
    "ma'am",
    "dr",
    "doctor",
    "professor",
}
REQUEST_AUXILIARIES = _dataset_terms("can", "could", "would")


def _alternation(words: set[str] | frozenset[str]) -> str:
    return "|".join(re.escape(word) for word in sorted(words, key=len, reverse=True))


_greeting_pattern = _alternation(GREETINGS)
_courtesy_pattern = _alternation(COURTESY_WORDS)
_honorific_pattern = _alternation(HONORIFICS)
_request_pattern = _alternation(REQUEST_AUXILIARIES)

# Removes direct-address wrappers such as “Hello John,” and “Dear Dr. Smith,”.
DIRECT_ADDRESS = re.compile(
    rf"^\s*(?:(?:dear)\s+)?(?:{_greeting_pattern}|{_honorific_pattern})\.?"
    rf"(?:\s+[\w'’-]+){{0,3}}\s*[,!:;\-–—]\s*",
    re.IGNORECASE,
)
# Removes low-information request particles such as “could you please”.
LEADING_REQUEST_PARTICLES = re.compile(
    rf"^\s*(?:{_request_pattern})\s+you(?:\s+please)?(?:\s*[,!:;\-–—]\s*|\s+)",
    re.IGNORECASE,
)
LEADING_PLEASANTRY = re.compile(
    rf"^\s*(?:{_greeting_pattern}|{_courtesy_pattern})(?:\s+there)?"
    rf"(?:\s*[,!:.\-–—]\s*|\s+|$)",
    re.IGNORECASE,
)
TRAILING_PLEASANTRY = re.compile(
    rf"(?:^|\s*[,;:]?\s+)(?:thank\s+you|thank-you|{_courtesy_pattern})[.!?\s]*$",
    re.IGNORECASE,
)


def clean_prompt(prompt: str) -> str:
    """Remove stop-word-backed boundary politeness without rewriting prompt content."""
    cleaned = prompt.strip()
    previous = None
    while cleaned and cleaned != previous:
        previous = cleaned
        cleaned = DIRECT_ADDRESS.sub("", cleaned, count=1).strip()
        cleaned = LEADING_REQUEST_PARTICLES.sub("", cleaned, count=1).strip()
        cleaned = LEADING_PLEASANTRY.sub("", cleaned, count=1).strip()
        cleaned = TRAILING_PLEASANTRY.sub("", cleaned, count=1).strip()
    return re.sub(r"[ \t]+", " ", cleaned)


def estimate_tokens(text: str) -> int:
    """Approximate subword tokens locally from words, numbers, and punctuation."""
    pieces = re.findall(r"[\w]+|[^\w\s]", text, flags=re.UNICODE)
    total = 0
    for piece in pieces:
        if piece.isalnum() or "_" in piece:
            # Most current tokenizers average roughly 3–4 characters per text token.
            total += max(1, (len(piece) + 3) // 4)
        else:
            total += 1
    return total


def _money(value: float) -> str:
    return f"${value:.8f}"


def _usage_value(usage: dict[str, Any], key: str) -> int:
    value = usage.get(key, 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    provider: str,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            error = body.get("error", {})
            detail = error.get("message") if isinstance(error, dict) else str(error)
        except (json.JSONDecodeError, AttributeError, UnicodeDecodeError):
            detail = None
        raise gr.Error(detail or f"{provider} returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise gr.Error(f"Could not reach {provider}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise gr.Error(f"The {provider} request timed out.") from exc


def _call_deepseek(
    prompt: str, api_key: str, model: str, max_tokens: int, temperature: float
) -> tuple[str, int, int, int]:
    result = _post_json(
        "https://api.deepseek.com/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        },
        {"Authorization": f"Bearer {api_key}"},
        "DeepSeek",
    )
    try:
        answer = result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise gr.Error("DeepSeek returned an unexpected response.") from exc
    usage = result.get("usage", {})
    input_tokens = _usage_value(usage, "prompt_tokens")
    output_tokens = _usage_value(usage, "completion_tokens")
    cached_tokens = _usage_value(usage, "prompt_cache_hit_tokens")
    return answer, input_tokens, output_tokens, cached_tokens


def _call_openai(
    prompt: str, api_key: str, model: str, max_tokens: int, _temperature: float
) -> tuple[str, int, int, int]:
    result = _post_json(
        "https://api.openai.com/v1/responses",
        {"model": model, "input": prompt, "max_output_tokens": max_tokens},
        {"Authorization": f"Bearer {api_key}"},
        "OpenAI",
    )
    text_parts: list[str] = []
    for item in result.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                text_parts.append(content["text"])
    if not text_parts:
        raise gr.Error("OpenAI returned no text response.")
    usage = result.get("usage", {})
    input_tokens = _usage_value(usage, "input_tokens")
    output_tokens = _usage_value(usage, "output_tokens")
    details = usage.get("input_tokens_details", {})
    cached_tokens = _usage_value(details, "cached_tokens") if isinstance(details, dict) else 0
    return "\n".join(text_parts), input_tokens, output_tokens, cached_tokens


def _call_gemini(
    prompt: str, api_key: str, model: str, max_tokens: int, temperature: float
) -> tuple[str, int, int, int]:
    result = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature": temperature,
            },
        },
        {"x-goog-api-key": api_key},
        "Gemini",
    )
    try:
        parts = result["candidates"][0]["content"]["parts"]
        answer = "\n".join(
            part["text"] for part in parts if part.get("text") and not part.get("thought", False)
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise gr.Error("Gemini returned an unexpected response.") from exc
    if not answer:
        raise gr.Error("Gemini returned no text response.")
    usage = result.get("usageMetadata", {})
    input_tokens = _usage_value(usage, "promptTokenCount")
    visible_tokens = _usage_value(usage, "candidatesTokenCount")
    thinking_tokens = _usage_value(usage, "thoughtsTokenCount")
    cached_tokens = _usage_value(usage, "cachedContentTokenCount")
    return answer, input_tokens, visible_tokens + thinking_tokens, cached_tokens


CALLERS = {
    "DeepSeek": _call_deepseek,
    "ChatGPT / OpenAI": _call_openai,
    "Gemini": _call_gemini,
}


def provider_settings(provider: str) -> tuple[gr.Textbox, gr.Dropdown]:
    """Update the key field and model list when the provider changes."""
    settings = PROVIDERS[provider]
    return (
        gr.Textbox(
            label=settings["key_label"],
            type="password",
            placeholder="Leave blank to estimate input cost only",
        ),
        gr.Dropdown(
            choices=settings["models"],
            value=settings["models"][0][1],
            label="Model",
            info="Token pricing updates automatically with the selected model.",
        ),
    )


def send_prompt(
    prompt: str,
    provider: str,
    api_key_field: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> tuple[str, str, int, int, str, str, str]:
    """Clean a prompt, call the selected provider, and report usage and cost."""
    cleaned = clean_prompt(prompt)
    if not cleaned:
        raise gr.Error("Enter a prompt with more than a greeting or sign-off.")
    if provider not in PROVIDERS:
        raise gr.Error("Choose a supported AI provider.")

    settings = PROVIDERS[provider]
    allowed_models = {value for _, value in settings["models"]}
    if model not in allowed_models:
        raise gr.Error(f"Choose a valid {provider} model.")
    api_key = api_key_field.strip()
    if not api_key:
        input_tokens = estimate_tokens(cleaned)
        input_cost_value = input_tokens * PRICING[model]["input"] / 1_000_000
        return (
            cleaned,
            "*Estimate only — add an API key to send the prompt and receive a response.*",
            input_tokens,
            0,
            f"{_money(input_cost_value)}  ·  estimated locally",
            _money(0),
            _money(input_cost_value),
        )

    answer, input_tokens, output_tokens, cached_tokens = CALLERS[provider](
        cleaned, api_key, model, int(max_tokens), float(temperature)
    )
    cached_tokens = min(cached_tokens, input_tokens)
    uncached_tokens = input_tokens - cached_tokens
    rates = PRICING[model]
    input_cost_value = (
        cached_tokens * rates["cached"] + uncached_tokens * rates["input"]
    ) / 1_000_000
    output_cost_value = output_tokens * rates["output"] / 1_000_000
    input_detail = (
        f"{_money(input_cost_value)}  ·  {cached_tokens:,} cached / {uncached_tokens:,} uncached"
    )

    return (
        cleaned,
        answer,
        input_tokens,
        output_tokens,
        input_detail,
        _money(output_cost_value),
        _money(input_cost_value + output_cost_value),
    )


CSS = """
.gradio-container { max-width: 1080px !important; }
.hero { text-align: center; margin: 1.2rem auto 1.8rem; }
.hero h1 { font-size: 2.25rem; margin-bottom: .35rem; }
.hero p { color: var(--body-text-color-subdued); }
.metric textarea, .metric input { font-variant-numeric: tabular-nums; }
.run-button { min-height: 46px; }
"""


with gr.Blocks(title="Prompt Sifter · Multi-AI") as demo:
    gr.HTML(
        """<div class="hero"><h1>Prompt Sifter</h1>
        <p>Trim the courtesies, choose your AI, and see exactly what the call cost.</p></div>"""
    )

    with gr.Row():
        with gr.Column(scale=3):
            prompt = gr.Textbox(
                label="Your prompt",
                placeholder="Hello, please explain why the sky is blue. Thank you!",
                lines=8,
                autofocus=True,
            )
            with gr.Accordion("Request settings", open=True):
                provider = gr.Dropdown(
                    choices=list(PROVIDERS), value="DeepSeek", label="AI provider"
                )
                api_key = gr.Textbox(
                    label="DeepSeek API key",
                    type="password",
                    placeholder="Leave blank to estimate input cost only",
                )
                model = gr.Dropdown(
                    choices=PROVIDERS["DeepSeek"]["models"],
                    value="deepseek-v4-flash",
                    label="Model",
                    info="Token pricing updates automatically with the selected model.",
                )
                max_tokens = gr.Slider(1, 8192, value=1024, step=1, label="Maximum output tokens")
                temperature = gr.Slider(0, 2, value=0.7, step=0.1, label="Temperature")
            submit = gr.Button("Clean & send", variant="primary", elem_classes="run-button")

        with gr.Column(scale=2):
            cleaned_prompt = gr.Textbox(label="Prompt sent", lines=8, interactive=False)

    response = gr.Markdown(label="AI response")

    gr.Markdown("### Usage & estimated cost")
    with gr.Row():
        input_count = gr.Number(label="Input tokens", precision=0, interactive=False, elem_classes="metric")
        output_count = gr.Number(label="Output tokens", precision=0, interactive=False, elem_classes="metric")
        input_cost = gr.Textbox(label="Input cost (USD)", interactive=False, elem_classes="metric")
        output_cost = gr.Textbox(label="Output cost (USD)", interactive=False, elem_classes="metric")
        total_cost = gr.Textbox(label="Total cost (USD)", interactive=False, elem_classes="metric")

    gr.Markdown(
        "Costs use provider-reported token usage and standard paid-tier list prices stored in "
        "`app.py`. Your actual charge may differ because of free tiers, special processing modes, "
        "or provider price changes. Without an API key, the input token count and cost are local estimates."
    )

    provider.change(fn=provider_settings, inputs=provider, outputs=[api_key, model])
    event_inputs = [prompt, provider, api_key, model, max_tokens, temperature]
    event_outputs = [
        cleaned_prompt,
        response,
        input_count,
        output_count,
        input_cost,
        output_cost,
        total_cost,
    ]
    submit.click(fn=send_prompt, inputs=event_inputs, outputs=event_outputs)
    prompt.submit(fn=send_prompt, inputs=event_inputs, outputs=event_outputs)


if __name__ == "__main__":
    demo.launch(css=CSS)
