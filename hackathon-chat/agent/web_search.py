"""DuckDuckGo web search wrapper — no API key required."""
from __future__ import annotations

from typing import Any


def search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web using DuckDuckGo.

    Returns a list of dicts with keys: title, url, snippet.
    Falls back gracefully if duckduckgo-search is not installed.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return [{"title": "Error", "url": "", "snippet": "duckduckgo-search package not installed. Run: pip install duckduckgo-search"}]

    results: list[dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception as exc:
        return [{"title": "Search error", "url": "", "snippet": str(exc)}]

    return results
