# web_search.py
from duckduckgo_search import DDGS

def web_search(query: str, max_results: int = 5) -> str:
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_results):
            title = (r.get("title") or "").strip()
            href = (r.get("href") or "").strip()
            body = (r.get("body") or "").strip()
            if title or href or body:
                results.append(f"- {title}\n  {href}\n  {body}")
    return "\n".join(results)
