import json
import os
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from services.themes import THEMES

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are mofa-letter, an elite newsletter creative director and writer. You do not just write content — you DESIGN the entire newsletter experience. You decide what goes where, how it looks, and how it feels.

## Your Job

1. **Analyze the user's request** — Understand topic, tone, depth, format.
2. **Classify the mood** — Pick the visual mood that matches the content.
3. **Generate content** — Write engaging, specific, scannable content.
4. **Design the layout** — For each section, decide WHICH visual component best presents it.

## Mood Options (pick exactly one)

- **professional**: Business, finance, consulting, serious analysis. Navy + Gold palette.
- **creative**: Design, arts, innovation, culture. Teal + Coral palette.  
- **playful**: Gaming, hobbies, casual, fun. Violet + Lime palette.
- **academic**: Philosophy, history, literature, research. Oxford Blue + Brass palette.
- **minimal**: Tech, productivity, modern living. Black + White palette.

## Visual Components (pick the right one for each section)

- **hero**: The main title/introduction. Styles: `bold` (strong, with accent line), `minimal` (clean, quiet), `centered` (centered, elegant).
- **content_card**: A block of information that should feel highlighted. Styles: `bordered` (subtle border), `filled` (soft background), `left_accent` (left colored border).
- **quote**: A quotation, insight, or standout line. Styles: `elegant` (serif, decorative), `modern` (bold left bar), `minimal_line` (thin line, subtle).
- **bullet_list**: A list of items, points, or features. Styles: `dots` (• bullets), `numbered` (1. 2. 3.), `checkmarks` (✓ items), `arrows` (→ items).
- **divider**: Visual separation. Styles: `line` (thin line), `spacing` (empty space), `decorative` (line with accent dot).
- **insight_box**: A colored callout — tip, warning, or interesting fact. Styles: `tip` (blue-tinted), `warning` (amber-tinted), `fact` (green-tinted).
- **two_column**: Side-by-side comparison or paired ideas. Styles: `equal` (50/50), `left_heavy` (60/40), `right_heavy` (40/60). Use `---` in content to separate left and right.

## Layout Rules

- Start with a **hero** (always).
- Use 3-6 content sections total (hero + 2-5 body sections + optional closing).
- Alternate section types for visual rhythm. Never use the same component 3 times in a row.
- Match component to content:
  - A profound quote → `quote` (elegant)
  - A list of tips → `bullet_list` (checkmarks)
  - An important warning → `insight_box` (warning)
  - A deep explanation → `content_card` (left_accent)
  - Two contrasting ideas → `two_column` (equal)
  - A key takeaway → `insight_box` (fact)
- End with a `divider` (spacing) before the closing if the body is long.

## Content Rules

- 3-6 sections max. Quality over quantity.
- Be SPECIFIC. Name real concepts, thinkers, companies, ideas.
- Never hallucinate facts you're unsure of.
- Short paragraphs (2-4 sentences). One idea per paragraph.
- Use bullet lists for scannable points.
- Make it feel fresh every day. No recycled intros.
- Content length: under 3 minutes to read.

## Output Format

You MUST respond with valid JSON only. No markdown, no preamble.

```json
{
  "title": "Clever, specific title",
  "subtitle": "One-line subtitle with date vibe",
  "mood": "professional",
  "sections": [
    {
      "heading": "Section heading or empty string",
      "content": "The content text. Use \\n for newlines. For bullet_list, put each item on its own line starting with • or just plain text. For two_column, separate sides with ---",
      "component": "content_card",
      "style": "left_accent"
    }
  ],
  "closing": "Warm closing line."
}
```
"""

USER_PROMPT_TEMPLATE = """Create today's newsletter based on this request:

"{user_prompt}"

Today's date context: {date_str}

Remember: you are the creative director. Choose the perfect mood, write compelling content, and design a visually stunning layout. Return only valid JSON."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def generate_newsletter_content(user_prompt: str, date_str: str) -> dict:
    """
    Generate newsletter content + design metadata from a natural language prompt.
    Returns structured dict with title, subtitle, mood, sections, closing.
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

    return _normalize_content(parsed)


def _normalize_content(parsed: dict) -> dict:
    """Ensure the parsed JSON has all required fields with sensible defaults."""
    result = {
        "title": str(parsed.get("title", "Your Daily Brief")).strip(),
        "subtitle": str(parsed.get("subtitle", "")).strip(),
        "mood": str(parsed.get("mood", "minimal")).strip().lower(),
        "sections": [],
        "closing": str(parsed.get("closing", "Until tomorrow.")).strip(),
    }

    # Validate mood
    valid_moods = set(THEMES.keys())
    if result["mood"] not in valid_moods:
        # Try keyword matching
        matched = False
        mood_lower = result["mood"]
        for theme_key, theme in THEMES.items():
            if mood_lower in theme.get("mood_keywords", []):
                result["mood"] = theme_key
                matched = True
                break
        if not matched:
            result["mood"] = "minimal"

    raw_sections = parsed.get("sections", [])
    if not isinstance(raw_sections, list):
        raw_sections = []

    for sec in raw_sections:
        if not isinstance(sec, dict):
            continue
        section = {
            "heading": str(sec.get("heading", "")).strip(),
            "content": str(sec.get("content", "")).strip(),
            "component": str(sec.get("component", "content_card")).strip().lower(),
            "style": str(sec.get("style", "bordered")).strip().lower(),
        }
        # Validate component
        valid_components = {"hero", "content_card", "quote", "bullet_list", "divider", "insight_box", "two_column"}
        if section["component"] not in valid_components:
            section["component"] = "content_card"
        # Validate style
        valid_styles = {
            "bold", "minimal", "centered",           # hero
            "bordered", "filled", "left_accent",     # content_card
            "elegant", "modern", "minimal_line",     # quote
            "dots", "numbered", "checkmarks", "arrows",  # bullet_list
            "line", "spacing", "decorative",         # divider
            "tip", "warning", "fact",                # insight_box
            "equal", "left_heavy", "right_heavy",    # two_column
        }
        if section["style"] not in valid_styles:
            # Map to default for component
            defaults = {
                "hero": "bold",
                "content_card": "bordered",
                "quote": "modern",
                "bullet_list": "dots",
                "divider": "line",
                "insight_box": "tip",
                "two_column": "equal",
            }
            section["style"] = defaults.get(section["component"], "bordered")

        if section["heading"] or section["content"]:
            result["sections"].append(section)

    # Fallback: if no sections, create one
    if not result["sections"]:
        result["sections"].append({
            "heading": "Today's Edition",
            "content": "We encountered an issue generating your custom content. Our creative director is being retrained. Your next newsletter will arrive as scheduled.",
            "component": "content_card",
            "style": "bordered",
        })

    return result
