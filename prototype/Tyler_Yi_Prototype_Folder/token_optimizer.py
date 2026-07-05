"""
token_optimizer.py — reusable token-reduction toolkit for LLM apps.

Drop this file into any project. It has no UI dependencies (no gradio), just:
  pip install tiktoken sentence-transformers llmlingua nltk

Methods included (each can be used independently):

  INPUT SIDE (make the prompt smaller)
    normalize(text)                  — collapse whitespace/formatting. Zero quality risk.
    compress(text, rate)             — LLMLingua-2 learned compression. Keeps meaning,
                                       drops filler. Strongest input-side method.
    strip_stopwords(text)            — NLTK stopword removal. Cheapest, but riskiest
                                       (can drop negations); off by default.

  CALL AVOIDANCE (skip the LLM entirely)
    ResponseCache                    — exact + semantic cache. If the same (or a very
                                       similar) question was answered before, reuse the
                                       answer: 100% of that call's tokens saved.

  RAG SIDE (send less context)
    filter_chunks(scored_chunks)     — adaptive RAG: only keep chunks that are actually
                                       relevant instead of always sending top-k.

  OUTPUT SIDE (the expensive side — output tokens cost ~3x input)
    CONCISE_INSTRUCTION              — one line to append to a prompt.
    suggest_max_tokens(question)     — a sane max_tokens cap by question type.

  MEASUREMENT
    count_tokens(text)               — tiktoken pre-count (approximate for non-OpenAI
                                       models, but consistent for before/after deltas).
    SavingsTracker                   — accumulates tokens/$ saved per method per session.
"""

import re
import time
import hashlib

# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------
_enc = None


def count_tokens(text: str) -> int:
    """Approximate token count (tiktoken cl100k). Exact counts vary per provider,
    but before/after deltas measured with the same tokenizer are meaningful."""
    global _enc
    if _enc is None:
        import tiktoken
        _enc = tiktoken.get_encoding("cl100k_base")
    return len(_enc.encode(text or ""))


class SavingsTracker:
    """Running total of tokens saved per method. One instance per session."""

    def __init__(self):
        self.saved = {}      # method -> tokens saved
        self.cache_hits = 0
        self.calls = 0

    def add(self, method: str, tokens: int):
        if tokens > 0:
            self.saved[method] = self.saved.get(method, 0) + tokens

    def report(self, in_price_per_m: float = 0.20) -> str:
        if not self.saved and not self.cache_hits:
            return "No savings recorded yet."
        lines = [f"- {m}: **{t:,} tokens** (~${t / 1e6 * in_price_per_m:.6f})"
                 for m, t in sorted(self.saved.items(), key=lambda x: -x[1])]
        total = sum(self.saved.values())
        lines.append(f"- **Session total: {total:,} tokens saved**, "
                     f"{self.cache_hits} cache hit(s) across {self.calls} request(s)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Input side
# ---------------------------------------------------------------------------
def normalize(text: str) -> str:
    """Collapse runs of spaces/newlines and trim. Free savings, zero risk."""
    text = re.sub(r"[ \t]+", " ", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_compressor = None


def compress(text: str, rate: float = 0.6) -> str:
    """LLMLingua-2 learned prompt compression. `rate` = fraction of tokens to KEEP
    (0.6 keeps ~60%). Trained to preserve meaning — much safer than stopword removal.
    Downloads a ~500MB model on first use; falls back to the input on any failure."""
    global _compressor
    try:
        if _compressor is None:
            from llmlingua import PromptCompressor
            _compressor = PromptCompressor(
                model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
                use_llmlingua2=True,
                device_map="cpu",
            )
        result = _compressor.compress_prompt(text, rate=rate, force_tokens=["!", ".", "?", "\n"])
        out = result.get("compressed_prompt", "").strip()
        return out or text
    except Exception:
        return text  # never break the app over an optimization


_stopwords = None


def strip_stopwords(text: str) -> str:
    """NLTK stopword removal. Cheapest input trim, but can drop meaning-bearing words
    ('not', 'of'). Use only for open-ended prompts, not precise instructions."""
    global _stopwords
    if _stopwords is None:
        import nltk
        from nltk.corpus import stopwords as sw
        try:
            _stopwords = set(sw.words("english"))
        except LookupError:
            nltk.download("stopwords")
            _stopwords = set(sw.words("english"))
    kept = [w for w in re.findall(r"\b[\w']+\b", text) if w.lower() not in _stopwords]
    return " ".join(kept) or text


# ---------------------------------------------------------------------------
# Call avoidance: exact + semantic response cache
# ---------------------------------------------------------------------------
class ResponseCache:
    """Reuses previous answers.
    - Exact hit: same normalized question text.
    - Semantic hit: embedding similarity >= threshold (same meaning, different words).
    A hit saves 100% of that call's input AND output tokens."""

    def __init__(self, threshold: float = 0.92):
        self.threshold = threshold
        self.exact = {}          # md5(question) -> entry
        self.entries = []        # [{question, answer, in_tok, out_tok, emb}]
        self._model = None

    def _embed(self, text):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model.encode([text])[0]

    @staticmethod
    def _key(q):
        return hashlib.md5(normalize(q).lower().encode()).hexdigest()

    def get(self, question: str):
        """Returns (entry, kind) where kind is 'exact' | 'semantic' | None."""
        k = self._key(question)
        if k in self.exact:
            return self.exact[k], "exact"
        if self.entries:
            try:
                import numpy as np
                q = self._embed(question)
                qn = q / (np.linalg.norm(q) + 1e-8)
                best, best_sim = None, 0.0
                for e in self.entries:
                    en = e["emb"] / (np.linalg.norm(e["emb"]) + 1e-8)
                    sim = float(qn @ en)
                    if sim > best_sim:
                        best, best_sim = e, sim
                if best is not None and best_sim >= self.threshold:
                    return best, "semantic"
            except Exception:
                pass
        return None, None

    def put(self, question: str, answer: str, in_tok: int, out_tok: int):
        entry = {"question": question, "answer": answer,
                 "in_tok": in_tok, "out_tok": out_tok, "time": time.time()}
        try:
            entry["emb"] = self._embed(question)
            self.entries.append(entry)
        except Exception:
            pass
        self.exact[self._key(question)] = entry


# ---------------------------------------------------------------------------
# RAG side: adaptive context
# ---------------------------------------------------------------------------
def filter_chunks(scored_chunks, min_ratio: float = 0.35, max_keep: int = 3):
    """Adaptive RAG. `scored_chunks` = [(score, chunk)] sorted desc.
    Instead of always sending top-k, keep only chunks scoring at least `min_ratio`
    of the best score — irrelevant filler context is the biggest hidden token cost."""
    if not scored_chunks:
        return []
    best = scored_chunks[0][0]
    if best <= 0:
        return [c for _, c in scored_chunks[:1]]  # nothing matched; send one, not three
    kept = [c for s, c in scored_chunks[:max_keep] if s >= best * min_ratio]
    return kept or [scored_chunks[0][1]]


# ---------------------------------------------------------------------------
# Output side — the expensive tokens
# ---------------------------------------------------------------------------
CONCISE_INSTRUCTION = "Answer in at most 3 short sentences unless the customer asks for detail."

_SHORT_PATTERNS = re.compile(
    r"^(how much|what is the price|price of|do you|can i|is there|when|where|who|what time)", re.I)


def suggest_max_tokens(question: str) -> int:
    """Cap output length by question type. Output tokens cost ~3x input, so this is
    usually the single biggest cost lever."""
    if _SHORT_PATTERNS.match((question or "").strip()):
        return 150   # factual/price questions need a sentence or two
    return 400       # everything else still gets a reasonable ceiling
