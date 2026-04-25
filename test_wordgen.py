import asyncio
import sys

sys.path.insert(0, "/home/ubuntu/LexiPulse")

from database import get_db
from services.word_generator import generate_unique_words
from uuid import UUID


async def test():
    user_id = UUID("626a220c-4dc9-418a-9d5a-208d32eef339")
    async for db in get_db():
        words = await generate_unique_words(db, user_id, level=5, count=3)
        for w in words:
            source = "GROQ" if w.get("word") not in [
                "Velleity", "Fugacious", "Tmesis", "Apothegm", "Hebdomadal",
                "Eleemosynary", "Noctilucent", "Hiraeth", "Callipygian", "Sesquipedalian",
                "Ephemeral", "Lucid", "Tenacious", "Resilient", "Pragmatic",
                "Magnanimous", "Perfidious", "Sycophant", "Melancholy", "Cacophony",
                "Propinquity", "Mendacious", "Lachrymose", "Loquacious", "Obdurate",
                "Solecism", "Tendentious", "Pellucid", "Recondite", "Perspicacious"
            ] else "FALLBACK"
            print(f"[{source}] {w.get('word')}: {w.get('definitions',[{}])[0]}")
        break


if __name__ == "__main__":
    asyncio.run(test())
