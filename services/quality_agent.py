"""
QA Agent — validates newsletter content before sending.
Checks layout validity, content accuracy signals, source completeness, and tone.
"""

import json
from typing import Dict, Any, List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

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

Approval threshold: score >= 80 AND no critical issues. Critical issues include: missing sources for news, obvious hallucinations, generic filler text, literal escape sequences.
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
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
                "model": settings.groq_qa_model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(review_input, ensure_ascii=False)},
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
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


def quick_validate(content: Dict[str, Any], is_news: bool = False) -> List[str]:
    """
    Fast local validation — catches obvious problems without an LLM call.
    Returns list of issues found. ANY issue triggers a regeneration.
    """
    issues = []
    sections = content.get("sections", [])
    
    full_text = " ".join(
        f"{sec.get('heading', '')} {sec.get('content', '')}" for sec in sections
    )
    full_text_lower = full_text.lower()

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
    for phrase in hallucination_phrases:
        if phrase in full_text_lower:
            issues.append(f"Vague attribution detected: '{phrase.strip()}'")

    # Check for literal escape sequences
    if "\\n" in full_text:
        issues.append("Literal \\n escape sequences found in content")
    if "\\t" in full_text:
        issues.append("Literal \\t escape sequences found in content")

    # Check for generic filler
    filler_phrases = [
        "stay informed", "follow us for more", "stay ahead of the",
        "stay tuned", "keep updated", "for more insights",
        "see you tomorrow", "until next time", "thanks for reading",
    ]
    for phrase in filler_phrases:
        if phrase in full_text_lower:
            issues.append(f"Generic filler text detected: '{phrase}'")

    # Check closing length
    closing = content.get("closing", "").lower()
    if len(closing.split()) > 15:
        issues.append("Closing is too long (>15 words), must be brief and punchy")
    for phrase in filler_phrases:
        if phrase in closing:
            issues.append(f"Closing contains generic filler: '{phrase}'")

    # Check bullet list item count
    for sec in sections:
        if sec.get("component") == "bullet_list":
            items = [l for l in sec.get("content", "").split('\n') if l.strip()]
            if len(items) < 2:
                issues.append(f"bullet_list '{sec.get('heading', '')}' has only {len(items)} item(s), needs at least 2")

    # Check for source URLs on news content — EVERY non-hero, non-divider section must have one
    if is_news:
        for sec in sections:
            comp = sec.get("component", "")
            if comp not in ("hero", "divider") and not sec.get("source_url", "").strip():
                heading = sec.get("heading", "Untitled")
                issues.append(f"Section '{heading}' missing source_url — all news sections must cite sources")
        
        # Also check top-level sources exist
        sources = content.get("sources", [])
        if len(sources) < 2:
            issues.append(f"News content must have at least 2 distinct sources, found {len(sources)}")

    return issues
