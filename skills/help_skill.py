COMMAND = "/help"

def run(arg: str, context: dict) -> str:
    cmds = "\n".join(sorted(context.get("commands", [])))
    return f"Commands:\n{cmds}\n\n/exit - quit\n/clear - clear chat"
