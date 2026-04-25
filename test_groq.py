import asyncio
import httpx
from config import settings


async def test():
    print(f"Key present: {bool(settings.groq_api_key)}")
    print(f"Key length: {len(settings.groq_api_key)}")
    print(f"Model: {settings.groq_model}")

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_model,
                "messages": [{"role": "user", "content": "Say hello in JSON"}],
                "max_tokens": 50,
                "response_format": {"type": "json_object"},
            },
        )
        print(f"Status: {resp.status_code}")
        print(f"Body: {resp.text[:500]}")


if __name__ == "__main__":
    asyncio.run(test())
