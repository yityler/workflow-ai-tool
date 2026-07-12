

import os
import re

from ..Tyler_Yi_Prototype_Folder import token_optimizer as topt

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
TEXT_EXTENSIONS = (".txt", ".md")

_CAPTION_MODEL = "gemini-3.5-flash"
_caption_client = None
_caption_cache = {}  # path -> caption, so re-uploading/regenerating doesn't re-call the model


def _get_caption_client():
    global _caption_client
    if _caption_client is None:
        from google import genai
        _caption_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _caption_client


def _file_path(f):
    """Gradio gr.File entries are tempfile-like objects with a .name path;
    plain strings are accepted too (useful for tests)."""
    return getattr(f, "name", None) or (f if isinstance(f, str) else None)


def _read_text_file(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except Exception:
        return ""


def _read_pdf_file(path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""


def _caption_image(path):
    if path in _caption_cache:
        return _caption_cache[path]

    if not os.environ.get("GEMINI_API_KEY"):
        _caption_cache[path] = ""
        return ""

    try:
        from google.genai import types

        with open(path, "rb") as fh:
            image_bytes = fh.read()

        ext = os.path.splitext(path)[1].lstrip(".").lower()
        mime = f"image/{'jpeg' if ext == 'jpg' else ext}"

        response = _get_caption_client().models.generate_content(
            model=_CAPTION_MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime),
                "Describe this image in 1-2 short sentences for a designer building a "
                "product web page: what it shows, its style/mood, and any colors that "
                "stand out. " + topt.CONCISE_INSTRUCTION,
            ],
        )
        caption = (response.text or "").strip()
    except Exception:
        caption = ""

    _caption_cache[path] = caption
    return caption


def _chunk_text(text):
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def analyze_files(query, files):
    if not files:
        return {"text_context": "", "image_paths": [], "image_captions": {}, "tokens": 0}

    text_chunks = []
    image_paths = []

    for f in files:
        path = _file_path(f)
        if not path:
            continue
        ext = os.path.splitext(path)[1].lower()
        if ext in IMAGE_EXTENSIONS:
            image_paths.append(path)
        elif ext == ".pdf":
            text_chunks.extend(_chunk_text(_read_pdf_file(path)))
        elif ext in TEXT_EXTENSIONS:
            text_chunks.extend(_chunk_text(_read_text_file(path)))
        # other extensions: silently skipped (not a supported doc type)

    image_captions = {p: _caption_image(p) for p in image_paths}

    text_context = ""
    if text_chunks:
        try:
            from rank_bm25 import BM25Okapi

            tokenize = lambda s: re.findall(r"[a-z0-9']+", s.lower())
            bm25 = BM25Okapi([tokenize(c) for c in text_chunks])
            scores = bm25.get_scores(tokenize(query or ""))
            scored = sorted(zip(scores, text_chunks), key=lambda x: x[0], reverse=True)
            # token_optimizer: keep only chunks that actually score well, not a fixed top-k
            selected = topt.filter_chunks(scored, min_ratio=0.35, max_keep=5)
        except Exception:
            selected = text_chunks[:3]  # fallback if rank_bm25 isn't available

        combined = "\n\n".join(selected)
        # token_optimizer: learned compression on the input side for long context blocks
        if topt.count_tokens(combined) > 400:
            combined = topt.compress(combined, rate=0.6)
        text_context = topt.normalize(combined)

    caption_lines = [f"- {os.path.basename(p)}: {c}" for p, c in image_captions.items() if c]
    if caption_lines:
        caption_block = "Uploaded reference image(s):\n" + "\n".join(caption_lines)
        text_context = f"{text_context}\n\n{caption_block}".strip() if text_context else caption_block

    return {
        "text_context": text_context,
        "image_paths": image_paths,
        "image_captions": image_captions,
        "tokens": topt.count_tokens(text_context),
    }


def retrieve_context(query, files):
    return analyze_files(query, files)["text_context"]
