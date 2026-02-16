from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Dict, Any
from pypdf import PdfReader
import re

_STORE: Dict[str, Dict[str, Any]] = {}

def set_active_pdf(session_id: str, source_id: str) -> None:
    _STORE.setdefault(session_id, {"chunks": [], "sources": [], "active_pdf": None})
    _STORE[session_id]["active_pdf"] = source_id

def get_active_pdf(session_id: str) -> Optional[str]:
    data = _STORE.get(session_id)
    if not data:
        return None
    return data.get("active_pdf")

def _clean_text(t: str) -> str:
    t = t.replace("\x00", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        chunk = text[i:i+chunk_size]
        chunks.append(chunk)
        i += max(1, chunk_size - overlap)
    return chunks

def index_pdf(session_id: str, file_path: str, source_id: Optional[str] = None) -> int:
    p = Path(file_path)
    src = source_id or p.name

    reader = PdfReader(str(p))
    full_text = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        page_text = _clean_text(page_text)
        if page_text:
            full_text.append(page_text)

    text = "\n".join(full_text)
    chunks = _chunk_text(text)

    _STORE.setdefault(session_id, {"chunks": [], "sources": [], "active_pdf": None})
    # store tuples: (source_id, chunk_text)
    _STORE[session_id]["chunks"] = [(src, c) for c in chunks]
    _STORE[session_id]["sources"] = [src]
    set_active_pdf(session_id, src)

    return len(chunks)

def retrieve_context(session_id: str, question: str, k: int = 4, source_id: Optional[str] = None) -> List[str]:
    data = _STORE.get(session_id)
    if not data:
        return []

    if source_id is None:
        source_id = get_active_pdf(session_id)

    chunks: List[tuple] = data.get("chunks", [])
    if source_id:
        chunks = [x for x in chunks if x[0] == source_id]

    if not chunks:
        return []

    q_words = set(re.findall(r"[a-zA-Z0-9]+", (question or "").lower()))
    scored = []
    for _, c in chunks:
        c_words = set(re.findall(r"[a-zA-Z0-9]+", c.lower()))
        score = len(q_words.intersection(c_words))
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)

    # if top score is 0, return most recent chunks instead of irrelevant ones
    if scored and scored[0][0] == 0:
        return [c for _, c in chunks[:k]]

    # normal top-k
    top = [c for score, c in scored][:k]
    return top

def ask_pdf(session_id: str, question: str, llm, k: int = 4, source_id: Optional[str] = None) -> str:
    chunks = retrieve_context(session_id=session_id, question=question, k=k, source_id=source_id)

    if not chunks:
        active = get_active_pdf(session_id)
        if not active:
            return " No PDF uploaded yet. Upload a PDF first."
        return f" I couldn’t find relevant text in the active PDF ({active}). Try a more specific question."

    context = "\n\n---\n\n".join(chunks)

    prompt = (
        "You are Jarvis. Answer using ONLY the context from the uploaded PDF.\n"
        "If the answer is not in the context, say: 'I don't know from this PDF.'\n\n"
        f"Context:\n{context}\n\n"
        f"Question:\n{question}\n\n"
        "Answer:"
    )

    res = llm.invoke(prompt)
    return res.content if hasattr(res, "content") else str(res)
