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


# --- RAG: keyword-based retrieval (no extra API key needed) -------------------
# RAG knowledge base: loaded from knowledge_base.txt (an open-licensed Google reference doc).
# This is the pre-gathered dataset the AI references when RAG is on. Edit that file — or paste
# your own text in the app — to ask about something else.
def _load_knowledge_base():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base.txt")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Add a document here to ask questions about it (knowledge_base.txt was not found)."


SAMPLE_DOC = _load_knowledge_base()


# The AI's persona: a self-service checkout clerk for the Smart Stickies store.
CLERK_PERSONA = (
    "You are the friendly self-service checkout assistant for Smart Stickies, an RFID-powered "
    "retail store in Singapore. Help the customer check out: identify products, give prices in "
    "Singapore dollars, add up totals, apply 9% GST when asked, and answer questions about "
    "products, payment, membership, and store policies. Keep replies short and helpful."
)


def _chunks(text, size=60, overlap=15):
    """Split the document into overlapping chunks of ~`size` words."""
    words = text.split()
    out, i = [], 0
    while i < len(words):
        out.append(" ".join(words[i:i + size]))
        i += size - overlap
    return [c for c in out if c.strip()]


def retrieve(document, question, k=3):
    """Pick the chunks that share the most meaningful words with the question."""
    sw = _get_stopwords()
    q_words = {w.lower() for w in re.findall(r"\b[\w']+\b", question) if w.lower() not in sw}
    scored = []
    for c in _chunks(document):
        c_words = {w.lower() for w in re.findall(r"\b[\w']+\b", c)}
        scored.append((len(q_words & c_words), c))
    scored.sort(key=lambda x: x[0], reverse=True)
    # Prefer chunks that actually matched; fall back to the first few if none did.
    matched = [c for s, c in scored[:k] if s > 0]
    return matched or [c for s, c in scored[:k]]


def web_search(query, k=4):
    """Live web search (DuckDuckGo) — returns a list of {title, href, body} results.
    This is the 'retrieve from the internet' source for RAG."""
    try:
        from ddgs import DDGS
    except ImportError:  # older package name
        from duckduckgo_search import DDGS
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=k))


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


def chat(provider_name: str, api_key: str, minimize: bool, use_rag: bool, rag_source: str,
         document: str, prompt: str):
    cfg = PROVIDERS[provider_name]
    key = (api_key or "").strip() or os.environ.get(cfg["env"], "")

    if not key:
        return "", f"No API key. Paste one above or set {cfg['env']} in your terminal."
    if not (prompt or "").strip():
        return "", "Enter a prompt first."

    original = prompt.strip()

    # Optionally shrink the question by removing stopwords.
    question = original
    if minimize:
        trimmed = minimize_prompt(original)
        question = trimmed if trimmed else original

    # Optionally turn on RAG: retrieve context, then ask the model to answer from it.
    rag_chunks = None      # context pieces used (web snippets or document chunks)
    rag_sources = None     # list of (title, url) when using web search
    rag_mode = None        # "web" or "document"
    sent = question
    if use_rag:
        if rag_source.startswith("Web"):
            try:
                results = web_search(original, k=4)
            except Exception as e:
                return "", f"Web search error: {e}"
            if not results:
                return "", "Web search returned no results. Try rephrasing the question."
            rag_chunks = [f"{r.get('title','')}: {r.get('body','')}" for r in results]
            rag_sources = [(r.get("title", ""), r.get("href", "")) for r in results]
            rag_mode = "web"
        elif (document or "").strip():
            rag_chunks = retrieve(document, original, k=3)
            rag_mode = "document"

    if rag_chunks is not None:
        context = "\n\n".join(rag_chunks)
        sent = (
            CLERK_PERSONA +
            "\n\nUse the information below (retrieved for this question) to help the customer. "
            "If it is not covered, say you'll call a staff member.\n\n"
            f"Information:\n{context}\n\nCustomer: {question}"
        )
    else:
        # No RAG: still answer in character as the checkout clerk.
        sent = CLERK_PERSONA + f"\n\nCustomer: {question}"

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
        breakdown += (
            "\n\n**NLTK token minimizer (stopword removal)**\n\n"
            f"- Question words: {count_words(original)} → {count_words(question)} after trimming"
        )

    # RAG detail: show the source and how much the retrieved context added to the input cost.
    if rag_chunks is not None:
        ctx_words = count_words("\n\n".join(rag_chunks))
        total_words = count_words(sent)
        est_ctx_tokens = round(in_tok * ctx_words / total_words) if total_words else 0
        est_ctx_cost = est_ctx_tokens / 1_000_000 * in_price
        est_base_tokens = max(in_tok - est_ctx_tokens, 0)
        if rag_mode == "web":
            srcs = "\n".join(f"  {i+1}. [{t}]({u})" for i, (t, u) in enumerate(rag_sources))
            origin = (f"Searched the web and used **{len(rag_chunks)}** result(s) as context:\n{srcs}")
        else:
            origin = f"Retrieved **{len(rag_chunks)}** chunk(s) from the document and used them as context."
        breakdown += (
            f"\n\n**RAG: ON (source: {rag_mode})**\n\n"
            f"- {origin}\n"
            f"- Input tokens this run: **{in_tok}** = your question (~{est_base_tokens}) "
            f"+ retrieved context (~{est_ctx_tokens}).\n"
            f"- Extra cost from the RAG context: **~${est_ctx_cost:.6f}** "
            f"(without RAG the input would be ~{est_base_tokens} tokens)."
        )

    return text, breakdown


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Free LLM Chat") as demo:
        with gr.Row():
            provider = gr.Dropdown(
                choices=list(PROVIDERS.keys()),
                value=list(PROVIDERS.keys())[0],
                label="Model",
            )
            api_key = gr.Textbox(label="API key", type="password",
                                 placeholder="Paste key (or set it as an environment variable)")
        minimize = gr.Checkbox(label="Minimize tokens (NLTK stopword removal)", value=False)
        use_rag = gr.Checkbox(label="Use RAG (retrieve context, then answer from it)", value=False)
        rag_source = gr.Radio(
            ["Web search (live internet)", "Document (the box below)"],
            value="Web search (live internet)",
            label="RAG source (used when RAG is on)",
        )
        hide_doc = gr.Checkbox(label="Hide document box", value=False)
        document = gr.Textbox(label="Knowledge document (only used if RAG source = Document)",
                              lines=6, value=SAMPLE_DOC)
        # Toggle just hides/shows the box in the UI — the document text is still used.
        hide_doc.change(lambda h: gr.update(visible=not h), hide_doc, document)
        prompt = gr.Textbox(label="Prompt", placeholder="Ask something…", lines=6)
        submit = gr.Button("Send", variant="primary")
        out = gr.Textbox(label="Response", lines=12)
        cost = gr.Markdown(label="Token & cost breakdown")

        inputs = [provider, api_key, minimize, use_rag, rag_source, document, prompt]
        submit.click(fn=chat, inputs=inputs, outputs=[out, cost])
        prompt.submit(fn=chat, inputs=inputs, outputs=[out, cost])
    return demo


if __name__ == "__main__":
    build_ui().launch()
