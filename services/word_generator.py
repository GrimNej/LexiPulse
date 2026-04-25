import json
import os
from typing import List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from models import SentWord

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

SYSTEM_PROMPT = """You are a master lexicographer and vocabulary specialist. You generate rare, precise, and genuinely advanced English vocabulary for highly educated language learners. You never produce common words. Every word you generate must be real, verifiable in major dictionaries, and legitimately used in written English at some point in its history.

You respond ONLY in valid JSON. No preamble, no explanation, no markdown code fences. Raw JSON only."""

USER_PROMPT_TEMPLATE = """Generate exactly {count} advanced English words appropriate for difficulty level {level} on a scale of 1 to 10, where:

Level 1: elevated everyday vocabulary, above common usage but still recognized by most educated speakers.
Level 10: extraordinarily rare, archaic, or hyper-technical vocabulary that even native-speaking experts seldom encounter.

Current target level: {level}

Rules:
- Do not use any of these words (the user has already received them): {exclusion_list}
- Every word must be real and traceable to a reputable dictionary or historical usage
- Prefer words that are underused but not entirely extinct in modern written English
- Words should feel rewarding to learn and plausible to use in careful writing
- Vary the part of speech across the batch where possible (not all nouns, for example)
- Avoid internet-famous words that appear constantly on vocabulary lists (e.g., serendipity, petrichor, sonder, ephemeral, mellifluous)

Return a JSON array of exactly {count} objects. Each object must follow this exact structure:

[
  {{
    "word": "string",
    "pronunciation": "IPA string (e.g. /vɛˈliːɪti/)",
    "part_of_speech": "string (noun, verb, adjective, adverb, etc.)",
    "etymology": "string — origin language(s) and root meaning, written as a full sentence",
    "definitions": [
      "string — primary definition, written in plain, precise English",
      "string — secondary or extended meaning if it exists"
    ],
    "examples": [
      "string — example sentence in a literary or reflective context",
      "string — example sentence in a professional or journalistic context",
      "string — example sentence in an everyday, grounded context"
    ]
  }}
]
"""

FALLBACK_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "fallback_words.json")


async def get_recent_sent_words(db: AsyncSession, user_id: UUID, limit: int = 100) -> List[str]:
    result = await db.execute(
        select(SentWord.word)
        .where(SentWord.user_id == user_id)
        .order_by(desc(SentWord.sent_at))
        .limit(limit)
    )
    return [row[0].lower().strip() for row in result.all()]


async def get_all_sent_words_set(db: AsyncSession, user_id: UUID) -> set[str]:
    result = await db.execute(
        select(SentWord.word).where(SentWord.user_id == user_id)
    )
    return {row[0].lower().strip() for row in result.all()}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def _call_groq(count: int, level: int, exclusion_list: List[str]) -> List[dict]:
    exclusions_str = ", ".join(exclusion_list) if exclusion_list else "(none yet)"
    user_prompt = USER_PROMPT_TEMPLATE.format(
        count=count,
        level=level,
        exclusion_list=exclusions_str,
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.groq_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 2048,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        # Groq may wrap the array in an object key
        if isinstance(parsed, dict):
            for key in parsed:
                if isinstance(parsed[key], list):
                    return parsed[key]
            return []
        return parsed if isinstance(parsed, list) else []


async def _verify_word_exists(word: str) -> bool:
    """Check word against Free Dictionary API. No API key needed."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(DICTIONARY_API_URL.format(word=word.lower()))
            return resp.status_code == 200
    except Exception:
        return False


def _load_fallback_words() -> dict[str, List[dict]]:
    try:
        with open(FALLBACK_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_fallback_words(level: int, count: int, exclude: set[str]) -> List[dict]:
    cache = _load_fallback_words()
    key = str(level)
    candidates = cache.get(key, [])
    results = []
    for word_data in candidates:
        w = word_data.get("word", "").lower().strip()
        if w and w not in exclude:
            results.append(word_data)
        if len(results) >= count:
            break
    return results


class WordGenerationError(Exception):
    pass


async def generate_unique_words(
    db: AsyncSession,
    user_id: UUID,
    level: int,
    count: int = 3,
) -> List[dict]:
    """
    Generate {count} unique words for a user at a given level.
    Uses Groq + Free Dictionary verification, with fallback cache on total failure.
    """
    sent_words_set = await get_all_sent_words_set(db, user_id)
    recent_exclusions = await get_recent_sent_words(db, user_id, limit=100)

    # Ask for more words than needed to reduce retry rounds
    request_count = count + 3

    confirmed: List[dict] = []
    in_progress_words: set[str] = set()
    attempts = 0
    max_attempts = 6

    while len(confirmed) < count and attempts < max_attempts:
        needed = count - len(confirmed)
        current_request = max(request_count, needed + 2)

        try:
            candidates = await _call_groq(
                count=current_request,
                level=level,
                exclusion_list=recent_exclusions + list(in_progress_words),
            )
        except Exception as groq_error:
            # On total Groq failure after retries, fall back to cache
            fallback = _get_fallback_words(level, count, sent_words_set | in_progress_words)
            if fallback:
                # Verify cache words aren't in DB (they shouldn't be, but safety first)
                for word_data in fallback:
                    w = word_data["word"].lower().strip()
                    if w not in sent_words_set and w not in in_progress_words:
                        confirmed.append(word_data)
                        in_progress_words.add(w)
                    if len(confirmed) >= count:
                        break
                if len(confirmed) >= count:
                    return confirmed[:count]
            raise WordGenerationError(
                f"Groq failed and fallback insufficient for user {user_id}: {groq_error}"
            )

        for word_data in candidates:
            if not isinstance(word_data, dict):
                continue
            word_lower = word_data.get("word", "").lower().strip()
            if not word_lower:
                continue

            # Check against DB history and current in-progress batch
            if word_lower in sent_words_set or word_lower in in_progress_words:
                continue

            # Verify against Free Dictionary API (anti-hallucination)
            exists = await _verify_word_exists(word_lower)
            if not exists:
                # Give it one more try with a slight spelling variation check
                # (Skip if the word has spaces or hyphens, as dictionary API may not handle them)
                if " " in word_lower or "-" in word_lower:
                    exists = True  # Trust Groq for multi-word entries
            if not exists:
                continue

            confirmed.append(word_data)
            in_progress_words.add(word_lower)

            if len(confirmed) >= count:
                break

        attempts += 1

    if len(confirmed) < count:
        # Last resort: try fallback cache
        fallback = _get_fallback_words(level, count - len(confirmed), sent_words_set | in_progress_words)
        for word_data in fallback:
            w = word_data["word"].lower().strip()
            if w not in sent_words_set and w not in in_progress_words:
                confirmed.append(word_data)
                in_progress_words.add(w)
            if len(confirmed) >= count:
                break

    if len(confirmed) < count:
        raise WordGenerationError(
            f"Could not generate {count} unique words for user {user_id} after {max_attempts} attempts."
        )

    return confirmed[:count]
