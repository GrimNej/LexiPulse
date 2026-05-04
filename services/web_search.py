"""
Web search integration for real-time news and information.
Uses DuckDuckGo (free, no API key). Swappable for Tavily/Perplexity.
"""

import asyncio
from typing import List, Dict, Any, Optional

from ddgs import DDGS


async def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web and return results with title, snippet, and URL.
    Runs in thread pool since DDGS is synchronous.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_sync, query, max_results)


def _search_sync(query: str, max_results: int) -> List[Dict[str, str]]:
    """Synchronous DDGS search."""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return [
                {
                    "title": r.get("title", "").strip(),
                    "snippet": r.get("body", "").strip(),
                    "url": r.get("href", "").strip(),
                }
                for r in results
                if r.get("href")
            ]
    except Exception:
        return []


def format_search_context(results: List[Dict[str, str]]) -> str:
    """Format search results as context string for the LLM."""
    if not results:
        return ""
    lines = ["## Latest Web Search Results\n"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r['title']}")
        lines.append(f"URL: {r['url']}")
        lines.append(f"Snippet: {r['snippet']}")
        lines.append("")
    return "\n".join(lines)


NEWS_KEYWORDS = {
    "news", "latest", "today", "update", "breaking", "just announced",
    "recent", "this week", "this month", "new release", "launch",
    "announced", "unveiled", "revealed", "trend", "development",
}


def is_time_sensitive_prompt(prompt: str) -> bool:
    """Heuristic: does the prompt ask for time-sensitive content?"""
    prompt_lower = prompt.lower()
    return any(kw in prompt_lower for kw in NEWS_KEYWORDS)


def build_search_query(user_prompt: str, date_str: str) -> str:
    """Build a focused search query from the user's prompt."""
    # Strip fluff words
    fluff = {"give me", "tell me", "i want", "send me", "a newsletter about", "newsletter about"}
    query = user_prompt.strip()
    for f in fluff:
        query = query.lower().replace(f, "")
    query = query.strip(".!? ")
    # Add recency qualifier if not present
    if "today" not in query.lower() and "latest" not in query.lower():
        query = f"latest {query}"
    return f"{query} {date_str}"
