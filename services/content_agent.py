import json
import os
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are mofa-letter, an elite newsletter content strategist and writer. Your job is to read a user's natural language request and generate a complete, engaging, beautifully written newsletter tailored exactly to their specifications.

## How You Work

1. **Analyze the request** — Understand what the user wants: topic, tone, length, format, depth.
2. **Plan the structure** — Decide how many sections, what each covers, and in what order.
3. **Generate content** — Write the actual newsletter. Be specific, insightful, and engaging. Never generic filler.

## Output Format

You MUST respond with valid JSON only. No markdown, no preamble. Raw JSON only.

The JSON must follow this exact structure:

{
  "title": "The newsletter title (clever, specific, not generic)",
  "subtitle": "A one-line subtitle with the date vibe",
  "sections": [
    {
      "heading": "Section heading",
      "content": "The content. Can be paragraphs, bullet lists, or a mix. Use \\n for newlines.",
      "style": "paragraph"
    },
    {
      "heading": "Another section",
      "content": "• Bullet point one\\n• Bullet point two\\n• Bullet point three",
      "style": "bullet"
    },
    {
      "heading": "Wisdom",
      "content": "A powerful quote or insight",
      "style": "quote"
    }
  ],
  "closing": "A warm, brief closing line."
}

## Rules

- **3 to 5 sections** max. Quality over quantity.
- **Be specific.** If the user wants AI news, name real companies and concepts. If they want vocabulary, give real words with depth. If they want philosophy, reference real thinkers.
- **Never hallucinate facts you are unsure of.** It is better to be thoughtful and analytical than to invent specific dates, numbers, or claims.
- **Match the tone** the user implies: professional, casual, academic, poetic, punchy.
- **Make it scannable.** Use short paragraphs. One idea per paragraph.
- **The content must feel fresh every day.** Do not recycle templates or generic intros.
- **Style values:** use "paragraph" for prose, "bullet" for lists (prefix each line with "• "), "quote" for quotations or standout insights.
- **Content length:** Each section should be 2-6 sentences or 3-5 bullet points. The entire newsletter should take under 3 minutes to read.

## Examples of Good Prompts → Outputs

Prompt: "Three rare English vocabulary words every morning with etymology, definitions, and example sentences."
→ Sections: [Word 1 with full detail], [Word 2], [Word 3], [Quick recap]

Prompt: "Top 3 AI breakthroughs with one-sentence summaries and why they matter."
→ Sections: [Breakthrough 1: what + why], [Breakthrough 2], [Breakthrough 3], [Pattern / theme connecting them]

Prompt: "Daily Stoic quote with a 2-paragraph reflection and one practical exercise."
→ Sections: [The Quote], [Reflection], [Today's Exercise], [Closing thought]
"""

USER_PROMPT_TEMPLATE = """Generate today's newsletter based on this request:

"{user_prompt}"

Today's date context: {date_str}

Remember: specific, insightful, scannable, and fresh. Return only valid JSON."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def generate_newsletter_content(user_prompt: str, date_str: str) -> dict:
    """
    Generate newsletter content from a natural language prompt.
    Returns structured dict with title, subtitle, sections, closing.
    """
    if not user_prompt or not user_prompt.strip():
        raise ValueError("User prompt cannot be empty")

    user_message = USER_PROMPT_TEMPLATE.format(
        user_prompt=user_prompt.strip(),
        date_str=date_str,
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
                    {"role": "user", "content": user_message},
                ],
                "temperature": 0.75,
                "max_tokens": 3000,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

    # Normalize and validate structure
    return _normalize_content(parsed)


def _normalize_content(parsed: dict) -> dict:
    """Ensure the parsed JSON has all required fields with sensible defaults."""
    result = {
        "title": str(parsed.get("title", "Your Daily Brief")).strip(),
        "subtitle": str(parsed.get("subtitle", "")).strip(),
        "sections": [],
        "closing": str(parsed.get("closing", "Until tomorrow.")).strip(),
    }

    raw_sections = parsed.get("sections", [])
    if not isinstance(raw_sections, list):
        raw_sections = []

    for sec in raw_sections:
        if not isinstance(sec, dict):
            continue
        section = {
            "heading": str(sec.get("heading", "")).strip(),
            "content": str(sec.get("content", "")).strip(),
            "style": str(sec.get("style", "paragraph")).strip().lower(),
        }
        if section["style"] not in ("paragraph", "bullet", "quote"):
            section["style"] = "paragraph"
        if section["heading"] or section["content"]:
            result["sections"].append(section)

    # Fallback: if no sections, create one from any available content
    if not result["sections"]:
        # Try to salvage from unexpected structure
        for key in parsed:
            if isinstance(parsed[key], str) and len(parsed[key]) > 20:
                result["sections"].append({
                    "heading": key.replace("_", " ").title(),
                    "content": parsed[key],
                    "style": "paragraph",
                })

    # Absolute fallback
    if not result["sections"]:
        result["sections"].append({
            "heading": "Today's Edition",
            "content": "We encountered an issue generating your custom content. Our team has been notified. Your next newsletter will arrive as scheduled.",
            "style": "paragraph",
        })

    return result
