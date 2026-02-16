from memory_store import add_note, get_notes, clear_notes

COMMAND = "/notes"
ALIAS = ["/clear_notes"]

def run(arg: str, context: dict) -> str:
    session_id = context.get("session_id", "default")
    cmd = context.get("command", COMMAND)

    if cmd == "/clear_notes":
        clear_notes(session_id)
        return "✅ All notes cleared."

    notes = get_notes(session_id)
    if not notes:
        return "🗒️ No notes saved yet."
    return "🗒️ Notes:\n" + "\n".join(f"{i+1}) {n}" for i, n in enumerate(notes))
