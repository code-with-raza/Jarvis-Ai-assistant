from memory_store import add_memory

COMMAND = "/remember"
DESCRIPTION = "Save a memory"

def run(arg: str, context: dict) -> str:
    session_id = context.get("session_id", "default")
    text = arg.strip()

    if not text:
        return "Usage: /remember <text> (or say: remember <text>)"

    add_memory(session_id, text)
    return "✅ Saved to memory."
