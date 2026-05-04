"""
QA Agent — validates newsletter content before sending.
Checks layout validity, content accuracy signals, source completeness, and tone.
"""

import json
from typing import Dict, Any, List

import httpx

from config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a meticulous quality assurance editor for mofa-letter newsletters.

Your job is to REVIEW a newsletter draft and decide if it's good enough to send.

## Checks to Perform

1. **Layout Validity**
   - No empty sections (both heading AND content empty)
   - Component choices make sense for the content type
   - No duplicate components used 3+ times in a row

2. **Content Quality**
   - Content is specific and concrete (names real companies, people, products)
   - No obvious hallucination signals (vague phrases like "some experts say" without naming them, dates that seem made up, products that sound fictional)
   - NO generic filler text: "Stay informed", "Follow us for more", "Stay ahead of the curve" — these are meaningless and must be rejected
   - NO literal escape sequences like `\n` or `\t` visible in the text
   - Short, scannable paragraphs
   - Under 3 minutes read time

3. **Source Completeness (CRITICAL for news topics)**
   - If the topic is news/current events, at least 2 distinct source URLs must be present
   - Sources should be credible (major publications, official blogs, reputable tech sites)
   - No placeholder or example URLs

4. **Tone Consistency**
   - Mood matches content (playful for gaming, professional for business, etc.)

## Scoring

- 90-100: Excellent, ready to send
- 70-89: Good, minor issues
- 50-69: Okay, notable issues
- 0-49: Poor, should not send

## Output Format

Respond with valid JSON only:

```json
{
  "approved": true/false,
  "score": 85,
  "issues": ["brief issue 1", "brief issue 2"],
  "feedback": "Specific, actionable feedback for the creative director to fix the issues. Be concise."
}
```

Approval threshold: score >= 75 AND no critical issues (missing sources for news, obvious hallucinations).
"""


async def review_newsletter(content: Dict[str, Any], original_prompt: str) -> Dict[str, Any]:
    """
    Review newsletter content. Returns dict with approved, score, issues, feedback.
    """
    review_input = {
        "original_prompt": original_prompt,
        "draft": content,
    }

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
                    {"role": "user", "content": json.dumps(review_input, ensure_ascii=False)},
                ],
                "temperature": 0.3,
                "max_tokens": 1500,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()
        review_text = data["choices"][0]["message"]["content"]
        review = json.loads(review_text)

    return _normalize_review(review)


def _normalize_review(review: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure review has all required fields."""
    score = review.get("score", 50)
    try:
        score = int(score)
    except (ValueError, TypeError):
        score = 50

    issues = review.get("issues", [])
    if not isinstance(issues, list):
        issues = []

    return {
        "approved": bool(review.get("approved", score >= 75)),
        "score": max(0, min(100, score)),
        "issues": [str(i) for i in issues if i],
        "feedback": str(review.get("feedback", "Please review and improve.")).strip(),
    }


def quick_validate(content: Dict[str, Any]) -> List[str]:
    """
    Fast local validation — catches obvious problems without an LLM call.
    Returns list of issues found.
    """
    issues = []
    sections = content.get("sections", [])

    # Check for empty sections
    empty_count = 0
    for sec in sections:
        if not sec.get("heading", "").strip() and not sec.get("content", "").strip():
            empty_count += 1
    if empty_count > 0:
        issues.append(f"{empty_count} empty section(s) found")

    # Check for hallucination signals
    hallucination_phrases = [
        "some experts say", "many believe", "it is said that", "rumored to",
        "widely expected", " reportedly ", " speculated ", " allegedly ",
    ]
    full_text = " ".join(
        f"{sec.get('heading', '')} {sec.get('content', '')}" for sec in sections
    ).lower()
    for phrase in hallucination_phrases:
        if phrase in full_text:
            issues.append(f"Vague attribution detected: '{phrase.strip()}'")

    # Check for literal escape sequences
    raw_text = " ".join(
        f"{sec.get('heading', '')} {sec.get('content', '')}" for sec in sections
    )
    if "\\n" in raw_text:
        issues.append("Literal \\n escape sequences found in content — must use actual newlines")
    if "\\t" in raw_text:
        issues.append("Literal \\t escape sequences found in content")

    # Check for generic filler
    filler_phrases = [
        "stay informed", "follow us for more", "stay ahead of the curve",
        "stay tuned", "keep updated", "for more insights",
    ]
    for phrase in filler_phrases:
        if phrase in full_text:
            issues.append(f"Generic filler text detected: '{phrase}'")

    # Check for source URLs on news content
    sources = content.get("sources", [])
    has_source_urls = any(s.get("url") for s in sources)
    section_urls = any(sec.get("source_url") for sec in sections)
    if not has_source_urls and not section_urls:
        # Only flag if prompt seems news-related
        title = content.get("title", "").lower()
        if any(k in title for k in {"news", "update", "latest", "this week", "today"}):
            issues.append("No source URLs found for news content")

    return issues
