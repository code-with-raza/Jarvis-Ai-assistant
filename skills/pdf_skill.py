from rag_pdf import ask_pdf

COMMAND = "/pdf"
ALIAS = ["/doc"]

def run(arg: str, ctx: dict) -> str:
    llm = ctx.get("llm")
    session_id = ctx.get("session_id", "default")

    if llm is None:
        return "❌ LLM not provided."

    question = (arg or "").strip()
    if not question:
        return "Usage: /pdf <your question>"

    return ask_pdf(
        session_id=session_id,
        question=question,
        llm=llm,
        k=4,
        source_id=None,
    )
