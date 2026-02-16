from memory_store import get_memories

COMMAND = "/recall"
DESCRIPTION = "Recall saved memories"

def run(arg: str, context: dict) -> str:
    session_id = context.get("session_id", "default")
    llm = context.get("llm")

    memories = get_memories(session_id)
    if not memories:
        return "I don’t have any saved memories about you yet."

    question = arg.strip().lower()

    # If user asked generally
    if not question or "everything" in question or "remember" in question:
        return "Here’s what I remember about you:\n" + "\n".join(
            f"- {m}" for m in memories
        )

    # Ask LLM to select relevant memory
    prompt = (
        "You are a memory assistant.\n"
        "From the list of memories below, answer the user's question.\n"
        "If none are relevant, say you don't know.\n\n"
        "Memories:\n"
        + "\n".join(f"- {m}" for m in memories)
        + f"\n\nQuestion: {question}\nAnswer:"
    )

    answer = llm.invoke(prompt).content.strip()
    return answer
