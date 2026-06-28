import requests
import gradio as gr
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader

MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"
HF_URL = "https://router.huggingface.co/v1/chat/completions"

embedder = SentenceTransformer("all-MiniLM-L6-v2")

docs = []
doc_embs = None


def chunk_text(text, max_len=500):
    parts = text.split(".")
    out, buf = [], ""
    for p in parts:
        if len(buf) + len(p) < max_len:
            buf += p + "."
        else:
            if buf.strip():
                out.append(buf.strip())
            buf = p + "."
    if buf.strip():
        out.append(buf.strip())
    return [c for c in out if c]


def recompute_embeddings():
    global doc_embs
    if docs:
        doc_embs = embedder.encode(docs, normalize_embeddings=True)
    else:
        doc_embs = None


def add_text(text):
    if not text or not text.strip():
        return "nothing to add, paste some text first", doc_count_text()
    chunks = chunk_text(text)
    docs.extend(chunks)
    recompute_embeddings()
    return f"added {len(chunks)} chunks", doc_count_text()


def add_files(files):
    if not files:
        return "no files uploaded", doc_count_text()

    added = 0
    skipped = []

    for f in files:
        path = f.name
        try:
            if path.endswith(".txt") or path.endswith(".md"):
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    chunks = chunk_text(fh.read())

            elif path.endswith(".pdf"):
                reader = PdfReader(path)
                text = ""
                for page in reader.pages:
                    t = page.extract_text()
                    if t:
                        text += t + "\n"
                chunks = chunk_text(text)

            else:
                skipped.append(path)
                continue

            docs.extend(chunks)
            added += len(chunks)

        except Exception as e:
            skipped.append(f"{path} ({e})")

    recompute_embeddings()

    msg = f"added {added} chunks from {len(files)} file(s)"
    if skipped:
        msg += f" -- skipped: {', '.join(skipped)}"
    return msg, doc_count_text()


def doc_count_text():
    return f"{len(docs)} chunks in store"


def clear_docs():
    global docs, doc_embs
    docs = []
    doc_embs = None
    return "cleared", doc_count_text()


def retrieve(query, k=5):
    if not docs or doc_embs is None:
        return []
    q = embedder.encode([query], normalize_embeddings=True)
    scores = cosine_similarity(q, doc_embs)[0]
    idx = np.argsort(scores)[::-1][:k]
    return [(docs[i], float(scores[i])) for i in idx]


def call_llm(prompt, token):
    if not token:
        return "add your HF token in the Token tab first"

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.3,
    }

    r = requests.post(HF_URL, headers=headers, json=payload, timeout=60)

    data = r.json()
    
    if "error" in data:
        return f"HF API error: {data['error']}"

    return data["choices"][0]["message"]["content"]
    

def build_prompt(query, contexts):
    context = "\n".join(f"- {c}" for c in contexts)
    return (
        f"Use the context below to answer the question. Don't quote it directly, "
        f"put it in your own words, and pull together whatever's relevant across "
        f"the different pieces. If it doesn't really cover the question, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    )


def rag_answer(query, token):
    if not query or not query.strip():
        return "type a question first"
    if not docs:
        return "no documents loaded yet, add some on the Data tab"

    retrieved = retrieve(query)
    context = [d for d, _ in retrieved]
    return call_llm(build_prompt(query, context), token)



with gr.Blocks(title="RAG demo") as demo:
    gr.Markdown("# RAG demo\nUpload some docs, then ask questions about them.")

    with gr.Tab("Token"):
        hf_token = gr.Textbox(label="HF API token", type="password", placeholder="hf_...")
        
    with gr.Tab("Data"):
        with gr.Row():
            with gr.Column():
                text_input = gr.Textbox(label="paste text", lines=8)
                add_text_btn = gr.Button("add text")
            with gr.Column():
                file_input = gr.File(label="upload txt / md / pdf", file_count="multiple")
                add_files_btn = gr.Button("upload files")

        status = gr.Textbox(label="status", interactive=False)
        doc_count = gr.Textbox(label="store", value=doc_count_text(), interactive=False)
        clear_btn = gr.Button("clear all docs")

    with gr.Tab("Ask"):
        query = gr.Textbox(label="question")
        ask_btn = gr.Button("get answer", variant="primary")
        answer_out = gr.Textbox(label="answer", lines=14)

    add_text_btn.click(add_text, text_input, [status, doc_count])
    add_files_btn.click(add_files, file_input, [status, doc_count])
    clear_btn.click(clear_docs, outputs=[status, doc_count])

    ask_btn.click(rag_answer, [query, hf_token], answer_out)


if __name__ == "__main__":
    demo.launch()