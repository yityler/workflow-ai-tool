"""A Gradio prompt cleaner for DeepSeek, OpenAI, and Gemini."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from html import escape
from pathlib import Path
from typing import Any

import gradio as gr
from stop_words import get_stop_words


DEV_PASSWORD = "sifter-dev-2026"
BASE_DIR = Path(__file__).resolve().parent
LAYOUT_CONFIG_PATH = BASE_DIR / "layout_config.json"
RAG_SOURCE_FILES = ("app.py", "README.md", "requirements.txt", "layout_config.json")

DEFAULT_LAYOUT = {
    "site_title": "Prompt Sifter",
    "site_subtitle": "Trim the courtesies, choose your AI, and see exactly what the call cost.",
    "button_text": "Clean & send",
    "accent_color": "#5b6cff",
    "max_width": 1080,
    "prompt_lines": 8,
    "output_lines": 8,
    "left_column_scale": 3,
    "right_column_scale": 2,
    "custom_css": "",
}

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


def _load_layout_config() -> dict[str, Any]:
    """Load safe layout settings from disk, falling back to defaults."""
    if not LAYOUT_CONFIG_PATH.exists():
        return DEFAULT_LAYOUT.copy()
    try:
        loaded = json.loads(LAYOUT_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_LAYOUT.copy()
    if not isinstance(loaded, dict):
        return DEFAULT_LAYOUT.copy()
    try:
        return _validate_layout_config(loaded)
    except ValueError:
        return DEFAULT_LAYOUT.copy()


def _validate_layout_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep generated layout changes inside a small, safe design surface."""
    allowed = DEFAULT_LAYOUT.copy()
    allowed.update({key: value for key, value in raw.items() if key in allowed})

    for key in ("site_title", "site_subtitle", "button_text"):
        allowed[key] = str(allowed[key]).strip()[:140] or DEFAULT_LAYOUT[key]

    accent_color = str(allowed["accent_color"]).strip()
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent_color):
        raise ValueError("accent_color must be a hex color like #5b6cff.")
    allowed["accent_color"] = accent_color

    allowed["max_width"] = max(820, min(1600, int(allowed["max_width"])))
    allowed["prompt_lines"] = max(3, min(20, int(allowed["prompt_lines"])))
    allowed["output_lines"] = max(3, min(20, int(allowed["output_lines"])))
    allowed["left_column_scale"] = max(1, min(5, int(allowed["left_column_scale"])))
    allowed["right_column_scale"] = max(1, min(5, int(allowed["right_column_scale"])))

    custom_css = str(allowed["custom_css"]).strip()[:1500]
    blocked_css_bits = ("<script", "</script", "@import", "url(", "javascript:")
    if any(bit in custom_css.casefold() for bit in blocked_css_bits):
        raise ValueError("custom_css cannot include scripts, imports, URLs, or javascript.")
    allowed["custom_css"] = custom_css
    return allowed


LAYOUT = _load_layout_config()


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


def _layout_preview(config: dict[str, Any]) -> str:
    """Render a small preview of the saved or proposed layout."""
    return f"""
    <div class="dev-preview" style="border-color:{escape(config['accent_color'])};">
      <h2>{escape(config['site_title'])}</h2>
      <p>{escape(config['site_subtitle'])}</p>
      <button style="background:{escape(config['accent_color'])};">{escape(config['button_text'])}</button>
      <small>Max width: {config['max_width']}px · Columns:
      {config['left_column_scale']}:{config['right_column_scale']}</small>
    </div>
    """


def _collect_rag_documents() -> list[Any]:
    """Load project files as LangChain documents for layout-aware retrieval."""
    try:
        from langchain_core.documents import Document
    except ImportError as exc:
        raise gr.Error(
            "LangChain is not installed yet. Run `pip install -r requirements.txt`, "
            "then restart the app."
        ) from exc

    documents = []
    for file_name in RAG_SOURCE_FILES:
        path = BASE_DIR / file_name
        if not path.exists():
            continue
        documents.append(
            Document(
                page_content=path.read_text(encoding="utf-8", errors="ignore"),
                metadata={"source": file_name},
            )
        )
    return documents


def _retrieve_layout_context(request: str) -> str:
    """Use LangChain splitting, then retrieve the chunks most related to the request."""
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError as exc:
        raise gr.Error(
            "LangChain text splitters are missing. Run `pip install -r requirements.txt`, "
            "then restart the app."
        ) from exc

    splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=160)
    chunks = splitter.split_documents(_collect_rag_documents())
    if not chunks:
        raise gr.Error("No project files were available for retrieval.")

    query_terms = set(re.findall(r"[a-z0-9_]+", request.casefold()))

    def score(chunk: Any) -> tuple[int, int]:
        text = chunk.page_content.casefold()
        token_overlap = sum(1 for term in query_terms if term in text)
        layout_hits = sum(
            text.count(term)
            for term in (
                "layout",
                "css",
                "hero",
                "column",
                "button",
                "gradio",
                "textbox",
                "theme",
            )
        )
        return token_overlap + layout_hits, len(text)

    chosen = sorted(chunks, key=score, reverse=True)[:5]
    return "\n\n".join(
        f"Source: {chunk.metadata.get('source', 'unknown')}\n{chunk.page_content}"
        for chunk in chosen
    )


def _layout_rag_prompt(request: str, context: str) -> str:
    """Build the RAG prompt with LangChain's prompt template."""
    try:
        from langchain_core.prompts import PromptTemplate
    except ImportError as exc:
        raise gr.Error(
            "LangChain prompt tools are missing. Run `pip install -r requirements.txt`, "
            "then restart the app."
        ) from exc

    template = PromptTemplate.from_template(
        """
You are helping redesign a Gradio website layout.
Use the retrieved project context to return ONLY valid JSON for this exact schema:
{{
  "site_title": "short page title",
  "site_subtitle": "short page subtitle",
  "button_text": "short primary button label",
  "accent_color": "#RRGGBB",
  "max_width": integer from 820 to 1600,
  "prompt_lines": integer from 3 to 20,
  "output_lines": integer from 3 to 20,
  "left_column_scale": integer from 1 to 5,
  "right_column_scale": integer from 1 to 5,
  "custom_css": "optional CSS only, no scripts, no imports, no external URLs"
}}

Developer request:
{request}

Current/default layout:
{current_layout}

Retrieved project context:
{context}
"""
    )
    return template.format(
        request=request.strip(),
        current_layout=json.dumps(LAYOUT, indent=2),
        context=context,
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    """Parse a model response that may wrap JSON in Markdown fences."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text
    if "{" in candidate and "}" in candidate:
        candidate = candidate[candidate.find("{") : candidate.rfind("}") + 1]
    parsed = json.loads(candidate)
    if not isinstance(parsed, dict):
        raise ValueError("The model did not return a JSON object.")
    return parsed


def unlock_developer_page(password: str) -> tuple[Any, str]:
    """Show the developer layout tools when the password is correct."""
    if password.strip() != DEV_PASSWORD:
        return gr.update(visible=False), "Wrong password."
    return gr.update(visible=True), "Unlocked."


def generate_layout_proposal(
    password: str,
    request: str,
    provider: str,
    api_key_field: str,
    model: str,
    max_tokens: int,
    temperature: float,
) -> tuple[str, str, str]:
    """Generate a safe layout JSON proposal using LangChain RAG plus the selected LLM."""
    if password.strip() != DEV_PASSWORD:
        raise gr.Error("Enter the developer password first.")
    if not request.strip():
        raise gr.Error("Describe the layout change you want.")
    api_key = api_key_field.strip()
    if not api_key:
        raise gr.Error("The developer RAG tool needs an API key because it calls an LLM.")
    if provider not in PROVIDERS:
        raise gr.Error("Choose a supported AI provider.")
    allowed_models = {value for _, value in PROVIDERS[provider]["models"]}
    if model not in allowed_models:
        raise gr.Error(f"Choose a valid {provider} model.")

    context = _retrieve_layout_context(request)
    rag_prompt = _layout_rag_prompt(request, context)
    answer, *_usage = CALLERS[provider](
        rag_prompt, api_key, model, int(max_tokens), float(temperature)
    )
    try:
        proposed = _validate_layout_config(_extract_json_object(answer))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise gr.Error(f"The LLM did not return usable layout JSON: {exc}") from exc

    proposal_json = json.dumps(proposed, indent=2)
    return (
        proposal_json,
        _layout_preview(proposed),
        "Generated a layout proposal. Review it, then click Apply if you like it.",
    )


def apply_layout_proposal(password: str, proposal_json: str) -> tuple[str, str]:
    """Save the approved layout config for the next app launch."""
    if password.strip() != DEV_PASSWORD:
        raise gr.Error("Enter the developer password first.")
    try:
        proposed = _validate_layout_config(json.loads(proposal_json))
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise gr.Error(f"Cannot apply this layout JSON: {exc}") from exc

    LAYOUT_CONFIG_PATH.write_text(json.dumps(proposed, indent=2) + "\n", encoding="utf-8")
    return (
        _layout_preview(proposed),
        "Applied. Restart the Gradio server to load the full layout everywhere.",
    )


CSS = """
.gradio-container { max-width: __MAX_WIDTH__px !important; }
.hero { text-align: center; margin: 1.2rem auto 1.8rem; }
.hero h1 { font-size: 2.25rem; margin-bottom: .35rem; }
.hero p { color: var(--body-text-color-subdued); }
.run-button button, button.run-button { background: __ACCENT_COLOR__ !important; border-color: __ACCENT_COLOR__ !important; }
.metric textarea, .metric input { font-variant-numeric: tabular-nums; }
.run-button { min-height: 46px; }
.dev-preview { border: 2px solid; border-radius: 14px; padding: 1rem; margin: .5rem 0; }
.dev-preview h2 { margin-top: 0; }
.dev-preview button { color: white; border: 0; border-radius: 10px; padding: .55rem .9rem; }
.dev-preview small { display: block; color: var(--body-text-color-subdued); margin-top: .8rem; }
""".replace("__MAX_WIDTH__", str(LAYOUT["max_width"])).replace(
    "__ACCENT_COLOR__", LAYOUT["accent_color"]
) + f"\n{LAYOUT['custom_css']}\n"


with gr.Blocks(title=f"{LAYOUT['site_title']} · Multi-AI") as demo:
    with gr.Tabs():
        with gr.Tab("Prompt tool"):
            gr.HTML(
                f"""<div class="hero"><h1>{escape(LAYOUT['site_title'])}</h1>
                <p>{escape(LAYOUT['site_subtitle'])}</p></div>"""
            )

            with gr.Row():
                with gr.Column(scale=LAYOUT["left_column_scale"]):
                    prompt = gr.Textbox(
                        label="Your prompt",
                        placeholder="Hello, please explain why the sky is blue. Thank you!",
                        lines=LAYOUT["prompt_lines"],
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
                        max_tokens = gr.Slider(
                            1, 8192, value=1024, step=1, label="Maximum output tokens"
                        )
                        temperature = gr.Slider(0, 2, value=0.7, step=0.1, label="Temperature")
                    submit = gr.Button(
                        LAYOUT["button_text"], variant="primary", elem_classes="run-button"
                    )

                with gr.Column(scale=LAYOUT["right_column_scale"]):
                    cleaned_prompt = gr.Textbox(
                        label="Prompt sent",
                        lines=LAYOUT["output_lines"],
                        interactive=False,
                    )

            response = gr.Markdown(label="AI response")

            gr.Markdown("### Usage & estimated cost")
            with gr.Row():
                input_count = gr.Number(
                    label="Input tokens", precision=0, interactive=False, elem_classes="metric"
                )
                output_count = gr.Number(
                    label="Output tokens", precision=0, interactive=False, elem_classes="metric"
                )
                input_cost = gr.Textbox(
                    label="Input cost (USD)", interactive=False, elem_classes="metric"
                )
                output_cost = gr.Textbox(
                    label="Output cost (USD)", interactive=False, elem_classes="metric"
                )
                total_cost = gr.Textbox(
                    label="Total cost (USD)", interactive=False, elem_classes="metric"
                )

            gr.Markdown(
                "Costs use provider-reported token usage and standard paid-tier list prices stored in "
                "`app.py`. Your actual charge may differ because of free tiers, special processing modes, "
                "or provider price changes. Without an API key, the input token count and cost are local estimates."
            )

        with gr.Tab("Developer Layout Lab"):
            gr.Markdown(
                "Password-protected developer page. It uses LangChain retrieval over the local project "
                "files, asks your chosen LLM for a safe layout JSON, then saves it after you approve."
            )
            dev_password = gr.Textbox(label="Developer password", type="password")
            unlock_button = gr.Button("Unlock developer tools")
            unlock_status = gr.Markdown()

            with gr.Group(visible=False) as developer_tools:
                dev_request = gr.Textbox(
                    label="Layout change request",
                    placeholder="Example: Make the site feel more futuristic, wider, and give the button a green accent.",
                    lines=4,
                )
                with gr.Accordion("Developer LLM settings", open=True):
                    dev_provider = gr.Dropdown(
                        choices=list(PROVIDERS), value="DeepSeek", label="AI provider"
                    )
                    dev_api_key = gr.Textbox(
                        label="DeepSeek API key",
                        type="password",
                        placeholder="Required for developer RAG layout generation",
                    )
                    dev_model = gr.Dropdown(
                        choices=PROVIDERS["DeepSeek"]["models"],
                        value="deepseek-v4-flash",
                        label="Model",
                    )
                    dev_max_tokens = gr.Slider(
                        256, 8192, value=1200, step=1, label="Maximum output tokens"
                    )
                    dev_temperature = gr.Slider(
                        0, 2, value=0.2, step=0.1, label="Temperature"
                    )

                generate_layout = gr.Button("Generate layout proposal", variant="primary")
                proposal_json = gr.Code(
                    label="Proposed layout_config.json",
                    language="json",
                    lines=18,
                    interactive=True,
                )
                proposal_preview = gr.HTML(value=_layout_preview(LAYOUT), label="Layout preview")
                dev_status = gr.Markdown()
                apply_layout = gr.Button("Apply proposed layout")

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

    unlock_button.click(
        fn=unlock_developer_page,
        inputs=dev_password,
        outputs=[developer_tools, unlock_status],
    )
    dev_provider.change(fn=provider_settings, inputs=dev_provider, outputs=[dev_api_key, dev_model])
    generate_layout.click(
        fn=generate_layout_proposal,
        inputs=[
            dev_password,
            dev_request,
            dev_provider,
            dev_api_key,
            dev_model,
            dev_max_tokens,
            dev_temperature,
        ],
        outputs=[proposal_json, proposal_preview, dev_status],
    )
    apply_layout.click(
        fn=apply_layout_proposal,
        inputs=[dev_password, proposal_json],
        outputs=[proposal_preview, dev_status],
    )


if __name__ == "__main__":
    demo.launch(css=CSS)
