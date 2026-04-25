import asyncio
import sys

sys.path.insert(0, "/home/ubuntu/LexiPulse")

from database import get_db
from services.word_generator import generate_unique_words
from uuid import UUID


async def test():
    async for db in get_db():
        words = await generate_unique_words(
            db, UUID("626a220c-4dc9-418a-9d5a-208d32eef339"), level=6, count=3
        )
        for w in words:
            print(f"WORD: {w['word']}")
            print(f"  DEF: {w['definitions'][0]}")
            print(f"  ETY: {w['etymology'][:60]}...")
            print()
        break


if __name__ == "__main__":
    asyncio.run(test())
