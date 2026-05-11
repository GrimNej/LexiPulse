import asyncio
import json
import logging
import os
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from services.themes import THEMES
from services.quality_agent import review_newsletter, quick_validate

logger = logging.getLogger(__name__)

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
- **highlight_stat**: A bold number, percentage, or key fact presented prominently. Styles: `big_number` (large bold number with context), `percentage` (large percentage with explanation), `milestone` (key achievement or milestone). Use for: "73% of AI startups...", "$2B funding round...", "1 million users..."

## Layout Rules

- Start with a **hero** (always).
- Use 3-6 content sections total (hero + 2-5 body sections + optional closing).
- Alternate section types for visual rhythm. Never use the same component 3 times in a row.
- Match component to content:
  - A profound quote → `quote` (elegant)
  - A list of tips → `bullet_list` (checkmarks)
  - An important warning → `insight_box` (warning)
  - A deep explanation → `content_card` (left_accent)
  - A bold stat or number → `highlight_stat` (big_number)
  - A key takeaway → `insight_box` (fact)
- End with a `divider` (spacing) before the closing if the body is long.

## Content Rules

- 3-6 sections max. Quality over quantity.
- Be SPECIFIC. Name real concepts, thinkers, companies, ideas.
- Never hallucinate facts you're unsure of.
- Short paragraphs (2-4 sentences). One idea per paragraph.
- Use bullet lists for scannable points.
- Make it feel fresh every day. No recycled intros.
- NEVER output the literal characters \\n in your text. Use actual line breaks.
- NEVER write generic filler like \"Stay informed\", \"Follow us for more\", or \"The AI landscape continues to evolve.\" Every sentence must deliver actual information.
- Closing: MAXIMUM 12 words. One punchy sentence. Examples: \"See you tomorrow.\" \"Happy learning.\" \"Until next time.\"
- Content length: under 3 minutes to read.

## Source Citations (IMPORTANT)

If you are writing about news, current events, or recent developments, you MUST cite your sources.

- EVERY non-hero section MUST have a `source_url` pointing to the SPECIFIC article (not a homepage)
- Add all sources to the top-level `sources` array
- Minimum 2 distinct sources for news content
- Only include real, verifiable URLs
- If no sources are available, leave the arrays empty

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
      "content": "The content text. Use actual newlines for line breaks. For bullet_list, put ONLY the bullet items — no introductory sentence before the bullets. Each item on its own line. For highlight_stat, put the number/fact on the first line and context below.",
      "component": "content_card",
      "style": "left_accent",
      "source_url": "https://example.com/article"
    }
  ],
  "sources": [
    {"title": "Source Name", "url": "https://example.com/article"}
  ],
  "closing": "Warm closing line."
}
```
"""

USER_PROMPT_TEMPLATE = """Create today's newsletter based on this request:

"{user_prompt}"

Today's date context: {date_str}
{search_context}

Remember: you are the creative director. Choose the perfect mood, write compelling content, and design a visually stunning layout. Return only valid JSON."""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def generate_newsletter_content(user_prompt: str, date_str: str, search_context: str = "", feedback: str = "") -> dict:
    """
    Generate newsletter content + design metadata from a natural language prompt.
    Returns structured dict with title, subtitle, mood, sections, sources, closing.
    """
    if not user_prompt or not user_prompt.strip():
        raise ValueError("User prompt cannot be empty")

    user_message = USER_PROMPT_TEMPLATE.format(
        user_prompt=user_prompt.strip(),
        date_str=date_str,
        search_context=search_context or "",
    )

    if feedback:
        user_message += f"\n\n## Previous Feedback (please address)\n{feedback}\n"
    user_message += "\nReturn only valid JSON."

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
                "max_tokens": 5000,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)

    return _normalize_content(parsed)


def _is_low_quality_url(url: str) -> bool:
    """Reject homepage and category-page URLs that don't point to specific articles."""
    url_lower = url.lower().rstrip("/")
    # Homepages
    if url_lower.count("/") <= 2:
        return True
    # Common category paths
    bad_paths = ["/category/", "/topics/", "/tag/", "/tags/", "/search", "/archive/"]
    if any(bp in url_lower for bp in bad_paths):
        return True
    return False


def _normalize_content(parsed: dict) -> dict:
    """Ensure the parsed JSON has all required fields with sensible defaults."""
    result = {
        "title": str(parsed.get("title", "Your Daily Brief")).strip(),
        "subtitle": str(parsed.get("subtitle", "")).strip(),
        "mood": str(parsed.get("mood", "minimal")).strip().lower(),
        "sections": [],
        "sources": [],
        "closing": str(parsed.get("closing", "Until tomorrow.")).strip(),
    }

    # Parse top-level sources — deduplicate by URL, filter low-quality URLs
    raw_sources = parsed.get("sources", [])
    seen_urls = set()
    if isinstance(raw_sources, list):
        for src in raw_sources:
            if isinstance(src, dict) and src.get("url"):
                url = str(src.get("url", "")).strip()
                # Skip homepage/category URLs
                if _is_low_quality_url(url):
                    continue
                if url.lower() not in seen_urls:
                    seen_urls.add(url.lower())
                    result["sources"].append({
                        "title": str(src.get("title", "")).strip() or "Source",
                        "url": url,
                    })

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
            "heading": str(sec.get("heading", "")).strip().replace("\\n", "\n"),
            "content": str(sec.get("content", "")).strip().replace("\\n", "\n"),
            "component": str(sec.get("component", "content_card")).strip().lower(),
            "style": str(sec.get("style", "bordered")).strip().lower(),
            "source_url": str(sec.get("source_url", "")).strip(),
        }
        # Validate component
        valid_components = {"hero", "content_card", "quote", "bullet_list", "divider", "insight_box", "highlight_stat"}
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
            "big_number", "percentage", "milestone", # highlight_stat
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
                "highlight_stat": "big_number",
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


async def generate_newsletter_with_qa(
    user_prompt: str,
    date_str: str,
    search_context: str = "",
    max_attempts: int = 2,
) -> dict:
    """
    Generate newsletter with QA review loop.
    Attempts generation up to max_attempts times with feedback.
    Returns best-effort content even if QA never fully approves.
    """
    feedback = ""
    best_content = None
    best_score = 0

    is_news = any(kw in user_prompt.lower() for kw in {"news", "update", "latest", "today", "breaking"})
    
    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            await asyncio.sleep(2)  # Rate limit protection between attempts
        content = await generate_newsletter_content(
            user_prompt=user_prompt,
            date_str=date_str,
            search_context=search_context,
            feedback=feedback if attempt > 1 else "",
        )

        # Quick local validation first (fast, no LLM call) — BLOCKING
        quick_issues = quick_validate(content, is_news=is_news)
        if quick_issues:
            logger.info(f"QA attempt {attempt}: quick_validate found {len(quick_issues)} issues: {quick_issues}")
            if attempt < max_attempts:
                feedback = "Quick validation issues (MUST fix): " + "; ".join(quick_issues)
                continue
            # On last attempt, still log but proceed to full QA

        # Small delay before QA review to space out Groq API calls
        await asyncio.sleep(1)
        # Full QA review (LLM call)
        review = await review_newsletter(content, user_prompt)
        logger.info(f"QA attempt {attempt}: score={review['score']}, approved={review['approved']}, issues={review['issues']}")

        if review["score"] > best_score:
            best_score = review["score"]
            best_content = content

        if review["approved"] and not quick_issues:
            logger.info(f"QA approved after {attempt} attempt(s)")
            return content

        if attempt < max_attempts:
            feedback = review["feedback"]
            if quick_issues:
                feedback += "\nAlso: " + "; ".join(quick_issues)

    logger.warning(f"QA never approved after {max_attempts} attempts. Best score: {best_score}")
    # Return best attempt even if never approved
    return best_content or content
