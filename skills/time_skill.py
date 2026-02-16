from datetime import datetime
import json
from typing import Any, Dict

COMMAND = "/time"

def _format_now(now: datetime, spec: Dict[str, Any]) -> str:
    # Defaults (your preferred)
    date_fmt = spec.get("date_fmt", "DD/MM/YYYY")
    hour_fmt = spec.get("hour_fmt", "12h")          # "12h" or "24h"
    seconds = bool(spec.get("seconds", False))
    ampm = bool(spec.get("ampm", True))

    # Date
    if date_fmt == "DD/MM/YYYY":
        date_str = now.strftime("%d/%m/%Y")
    else:
        date_str = now.strftime("%d/%m/%Y")

    # Time
    if hour_fmt == "24h":
        time_str = now.strftime("%H:%M:%S" if seconds else "%H:%M")
        return f"{date_str} {time_str}"

    # 12-hour
    if seconds:
        time_str = now.strftime("%I:%M:%S %p" if ampm else "%I:%M:%S").lstrip("0")
    else:
        time_str = now.strftime("%I:%M %p" if ampm else "%I:%M").lstrip("0")

    return f"{date_str} {time_str}"

def _decide_format_spec(llm, user_text: str) -> Dict[str, Any]:
    """
    Ask LLM ONLY for formatting, not the time itself.
    Must return JSON only.
    """
    prompt = (
        "You are a strict formatter router for a time tool.\n"
        "Return ONLY a JSON object (no backticks, no explanation) with keys:\n"
        '  date_fmt: must be "DD/MM/YYYY"\n'
        '  hour_fmt: "12h" or "24h"\n'
        "  seconds: true/false\n"
        "  ampm: true/false\n"
        "\n"
        "User request:\n"
        f"{user_text}\n"
        "\n"
        "JSON:"
    )

    raw = llm.invoke(prompt).content.strip()

    # Safe parse with fallback
    try:
        spec = json.loads(raw)
        if not isinstance(spec, dict):
            raise ValueError("spec not dict")
        return spec
    except Exception:
        # Fallback to your preferred format: DD/MM/YYYY + 12h + seconds + AM/PM
        return {"date_fmt": "DD/MM/YYYY", "hour_fmt": "12h", "seconds": True, "ampm": True}

def run(arg: str, context: dict) -> str:
    """
    Plugin entrypoint.
    context expects:
      - llm: ChatOpenAI instance
    """
    llm = context.get("llm", None)

    # What user asked (if called by auto-router, we pass original text as arg)
    user_text = (arg or "").strip() or "what is the time right now"

    # Decide formatting via "agent"
    if llm is not None:
        spec = _decide_format_spec(llm, user_text)
    else:
        spec = {"date_fmt": "DD/MM/YYYY", "hour_fmt": "12h", "seconds": True, "ampm": True}

    now = datetime.now()
    return _format_now(now, spec)
