import inspect
from rag_pdf import get_active_pdf

PDF_STRONG_TRIGGERS = [
    "this pdf",
    "this document",
    "this file",
    "uploaded pdf",
    "uploaded document",
    "resume",
    "cv",
    "in the pdf",
    "from the pdf",
    "from this document",
]

def looks_like_pdf_question(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in PDF_STRONG_TRIGGERS)

def _get_pdf_skill(skills: dict):
    return skills.get("/pdf") or skills.get("pdf") or skills.get("/doc")

def call_skill(fn, arg, session_id, llm):
    sig = inspect.signature(fn)
    params = sig.parameters

    if len(params) == 2:
        ctx = {"session_id": session_id, "llm": llm}
        return fn(arg, ctx)

    kwargs = {}
    if "session_id" in params:
        kwargs["session_id"] = session_id
    if "llm" in params:
        kwargs["llm"] = llm

    return fn(arg, **kwargs)

def auto_route(text: str, llm, skills, session_id="default"):
    if not text:
        return None

    # explicit /pdf command
    if text.lower().startswith("/pdf"):
        pdf_skill = _get_pdf_skill(skills)
        if not pdf_skill:
            return " PDF skill not registered"
        return call_skill(pdf_skill, text[4:].strip(), session_id, llm)

    # implicit PDF question ONLY if clearly referencing document
    if get_active_pdf(session_id) and looks_like_pdf_question(text):
        pdf_skill = _get_pdf_skill(skills)
        if pdf_skill:
            return call_skill(pdf_skill, text, session_id, llm)

    return None
