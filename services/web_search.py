"""
Web search integration for real-time news and information.
Uses DuckDuckGo (free, no API key). Swappable for Tavily/Perplexity.
"""

import asyncio
from typing import List, Dict, Any, Optional

from ddgs import DDGS


async def search_web(query: str, max_results: int = 5, use_news: bool = False) -> List[Dict[str, str]]:
    """
    Search the web and return results with title, snippet, and URL.
    Runs in thread pool since DDGS is synchronous.
    use_news=True uses DDG's news-specific search for better article URLs.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_sync, query, max_results, use_news)


def _search_sync(query: str, max_results: int, use_news: bool = False) -> List[Dict[str, str]]:
    """Synchronous DDGS search with credibility filtering."""
    try:
        with DDGS() as ddgs:
            if use_news:
                raw_results = list(ddgs.news(query, max_results=max_results * 3))
            else:
                raw_results = list(ddgs.text(query, max_results=max_results * 3))
            # Filter and rank by credibility
            credible = [r for r in raw_results if _is_credible_result({
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            })]
            # If too few credible results, include some non-credible but warn
            results = credible if len(credible) >= 3 else raw_results[:max_results]
            return [
                {
                    "title": r.get("title", "").strip(),
                    "snippet": r.get("body", "").strip(),
                    "url": r.get("href", "").strip(),
                }
                for r in results[:max_results]
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


# Credibility filtering
CREDIBLE_DOMAINS = {
    "reuters.com", "bloomberg.com", "techcrunch.com", "theverge.com",
    "wired.com", "arstechnica.com", "engadget.com", "theguardian.com",
    "nytimes.com", "wsj.com", "ft.com", "cnbc.com", "forbes.com",
    "venturebeat.com", "zdnet.com", "cnet.com", "bbc.com", "bbc.co.uk",
    "economist.com", "mit.edu", "stanford.edu", "arxiv.org",
    "openai.com", "anthropic.com", "deepmind.google", "blog.google",
    "microsoft.com", "meta.ai", "nvidia.com", "intel.com",
    "nature.com", "science.org", "techradar.com", "tomshardware.com",
    "anandtech.com", "theinformation.com", "axios.com", "politico.com",
}

SPAM_INDICATORS = [
    "10-trillion", "mythos", "secret", "shocking", "you won't believe",
    "exposed", " conspiracy ", "they don't want you to know",
]


def _is_credible_result(result: Dict[str, str]) -> bool:
    """Check if a search result is from a credible source."""
    url = result.get("url", "").lower()
    title = result.get("title", "").lower()
    snippet = result.get("snippet", "").lower()
    
    # Check domain
    domain = url.split("/")[2] if len(url.split("/")) > 2 else ""
    if any(cd in domain for cd in CREDIBLE_DOMAINS):
        return True
    
    # Check for spam indicators
    full_text = f"{title} {snippet}"
    for indicator in SPAM_INDICATORS:
        if indicator in full_text:
            return False
    
    return True


def build_search_query(user_prompt: str, date_str: str) -> str:
    """Build a focused search query from the user's prompt."""
    # Remove instruction words and fluff
    instruction_words = {
        "give me", "tell me", "i want", "send me", "a newsletter about",
        "newsletter about", "with the most", "include", "and engaging",
        "relevant", "updates", "key statistics", "funding rounds",
        "new model releases", "concrete action item", "clear explanation",
    }
    query = user_prompt.strip().lower()
    for word in instruction_words:
        query = query.replace(word, "")
    
    # Clean up and extract core topic words (max ~8 words)
    # Preserve short acronyms like AI, ML, VR, AR, NFT, DAO
    stop_words = {
        "about", "with", "from", "that", "have", "this", "will",
        "your", "you", "for", "are", "the", "and", "but", "not",
        "was", "had", "has", "been", "being", "can", "could",
    }
    words = []
    for w in query.split():
        if w in stop_words:
            continue
        if len(w) > 2 or w in {"ai", "ml", "vr", "ar", "nft", "dao", "gpu", "api", "llm"}:
            words.append(w)
    query = " ".join(words[:8]).strip(".!? ")
    
    # Add recency qualifier if not present
    if "today" not in query and "latest" not in query:
        query = f"latest {query}"
    
    # Add month from date_str
    month = date_str.split()[0] if date_str else ""
    return f"{query} {month}"
