COMMAND = "/calc"
ALIAS = ["/calculate"]

def run(arg: str, context: dict) -> str:
    if not arg.strip():
        return "Usage: /calc 2+2 or /calc (25*4)/3"

    expr = arg.strip()

    # Safety: allow only numbers + basic operators
    allowed = set("0123456789+-*/().% ")
    if any(ch not in allowed for ch in expr):
        return "❌ Only numbers and + - * / ( ) % . are allowed."

    try:
        result = eval(expr, {"__builtins__": {}})
        return f"✅ {expr} = {result}"
    except Exception as e:
        return f"❌ Invalid expression: {e}"
