COMMAND = "/remember"
ALIAS = ["/notes", "/clear_notes"]

_notes: list[str] = []

def run(arg: str, context: dict) -> str:
    # If the command used was /remember, save note
    cmd_used = context.get("command")

    if cmd_used == "/remember":
        text = arg.strip()
        if not text:
            return "Usage: /remember <text>"
        _notes.append(text)
        return "✅ Saved."

    if cmd_used == "/notes":
        if not _notes:
            return "No notes saved yet."
        return "🗒️ Notes:\n" + "\n".join(f"{i+1}) {n}" for i, n in enumerate(_notes))

    if cmd_used == "/clear_notes":
        _notes.clear()
        return "✅ Notes cleared."

    return "Unknown notes action."
