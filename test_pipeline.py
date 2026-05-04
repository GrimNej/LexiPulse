"""Quick local test of the web search + content pipeline."""
import asyncio
import sys
sys.path.insert(0, '.')

from services.web_search import search_web, format_search_context, is_time_sensitive_prompt, build_search_query

async def test_web_search():
    prompt = "latest AI industry news"
    print(f"Prompt: {prompt}")
    print(f"Is time-sensitive: {is_time_sensitive_prompt(prompt)}")
    
    query = build_search_query(prompt, "April 25, 2026")
    print(f"\nSearch query: {query}")
    
    results = await search_web(query, max_results=3)
    print(f"\nFound {len(results)} results:")
    for r in results:
        print(f"  - {r['title']}")
        print(f"    {r['url']}")
    
    ctx = format_search_context(results)
    print(f"\nContext length: {len(ctx)} chars")
    print("Context preview:")
    print(ctx[:800])

if __name__ == "__main__":
    asyncio.run(test_web_search())
