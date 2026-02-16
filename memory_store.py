import json
import os

DATA_FILE = "memory.json"


def _load():
    if not os.path.exists(DATA_FILE):
        return {"memories": {}, "notes": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # backward-safe defaults
    data.setdefault("memories", {})
    data.setdefault("notes", {})
    return data


def _save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Memories (facts)
def add_memory(session_id: str, text: str):
    data = _load()
    data["memories"].setdefault(session_id, [])
    data["memories"][session_id].append(text.strip())
    _save(data)


def get_memories(session_id: str):
    data = _load()
    return data["memories"].get(session_id, [])


def clear_memories(session_id: str):
    data = _load()
    data["memories"][session_id] = []
    _save(data)

# Notes 
def add_note(session_id: str, text: str):
    data = _load()
    data["notes"].setdefault(session_id, [])
    data["notes"][session_id].append(text.strip())
    _save(data)


def get_notes(session_id: str):
    data = _load()
    return data["notes"].get(session_id, [])


def clear_notes(session_id: str):
    data = _load()
    data["notes"][session_id] = []
    _save(data)
