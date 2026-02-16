import os
import importlib.util
from typing import Callable, Dict, Any

SkillFn = Callable[..., str]

def load_skills(skills_dir: str = "skills") -> Dict[str, SkillFn]:
    registry: Dict[str, SkillFn] = {}
    base_path = os.path.join(os.path.dirname(__file__), skills_dir)

    if not os.path.isdir(base_path):
        print(f" Skills dir not found: {base_path}")
        return registry

    for file in os.listdir(base_path):
        if not file.endswith(".py"):
            continue
        if file.startswith("_") or file == "__init__.py":
            continue

        path = os.path.join(base_path, file)
        module_name = f"{skills_dir}.{file[:-3]}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if not spec or not spec.loader:
                continue

            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            if not hasattr(mod, "COMMAND") or not hasattr(mod, "run"):
                continue

            cmd = getattr(mod, "COMMAND")
            fn = getattr(mod, "run")

            if isinstance(cmd, str) and callable(fn):
                registry[cmd] = fn
                print(f" Loaded skill: {cmd} from {file}")

                aliases = getattr(mod, "ALIAS", [])
                if isinstance(aliases, list):
                    for a in aliases:
                        if isinstance(a, str):
                            registry[a] = fn
                            print(f" Alias: {a} -> {cmd}")

        except Exception as e:
            print(f" Skipping {file} due to import error: {e}")

    print(" Skills registered:", list(registry.keys()))
    return registry


def route_command(text: str, skills, session_id: str, llm=None):
    text = (text or "").strip()
    if not text.startswith("/"):
        return None

    cmd, *rest = text.split(" ", 1)
    arg = rest[0] if rest else ""

    if cmd in {"/exit", "/quit"}:
        return "__EXIT__"
    if cmd == "/clear":
        return "__CLEAR_CHAT__"

    fn = skills.get(cmd)
    if not fn:
        return "Unknown command. Type /help"

    ctx: Dict[str, Any] = {
        "session_id": session_id,
        "command": cmd,
        "commands": list(skills.keys()),
        "llm": llm,
    }
    return fn(arg, ctx)
