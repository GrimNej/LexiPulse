"""
Prompt Rewriter — takes a user's casual request and rewrites their newsletter prompt.

Handles two modes:
- EXPAND: User says "also", "add", "include" → merge with existing prompt
- REPLACE: User says "instead", "switch to", "change to" → completely new prompt
"""

import json
from typing import Dict, Any

import httpx

from config import settings

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a prompt engineering assistant for mofa-letter, a universal daily newsletter service.

Users describe changes they want to their newsletter in casual language. Your job is to rewrite their newsletter prompt to be clear, specific, and actionable for an AI creative director.

## Rules

1. **Preserve intent** — Keep the core topic and depth of the existing prompt
2. **Incorporate naturally** — Merge the user's new request smoothly
3. **Remove redundancy** — Strip filler words, instructions, and meta-language
4. **Be specific** — Name concrete topics, formats, or angles when possible
5. **1-3 sentences max** — The prompt should be concise and scannable

## Mode Detection

- EXPAND: If the user says "also", "add", "include", "and", "plus" → merge topics
- REPLACE: If the user says "instead", "switch to", "change to", "now I want", "replace" → completely new topic

## Output Format

Respond with valid JSON only:

```json
{
  "new_prompt": "The rewritten newsletter prompt",
  "change_summary": "One-line description of what changed"
}
```

## Examples

Current: "Latest AI industry news with key statistics and funding rounds"
Request: "Also include cybersecurity"
→ {"new_prompt": "Latest AI industry and cybersecurity news with key statistics, funding rounds, and major security developments", "change_summary": "Added cybersecurity coverage"}

Current: "Latest AI industry news"
Request: "I want cooking tips instead"
→ {"new_prompt": "Daily cooking tips with simple recipes, ingredient substitutions, and kitchen hacks for busy professionals", "change_summary": "Switched to cooking tips"}

Current: "Three interesting science facts with clear explanations"
Request: "Make it more focused on space and astronomy"
→ {"new_prompt": "Daily space and astronomy discoveries with clear explanations of cosmic phenomena, mission updates, and stargazing tips", "change_summary": "Narrowed focus to space and astronomy"}
"""


async def rewrite_prompt(current_prompt: str, user_request: str) -> Dict[str, Any]:
    """
    Rewrite a newsletter prompt based on user's natural language request.
    Returns dict with new_prompt and change_summary.
    """
    if not current_prompt or not current_prompt.strip():
        current_prompt = "A concise, engaging daily newsletter with interesting insights and actionable takeaways."

    user_message = f"""Current newsletter prompt:
"{current_prompt.strip()}"

User's request:
"{user_request.strip()}"

Rewrite the prompt. Return only valid JSON."""

    async with httpx.AsyncClient(timeout=30.0) as client:
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
                "temperature": 0.5,
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        data = response.json()
        result_text = data["choices"][0]["message"]["content"]
        result = json.loads(result_text)

    new_prompt = str(result.get("new_prompt", current_prompt)).strip()
    change_summary = str(result.get("change_summary", "Prompt updated")).strip()

    # Fallback: if new prompt is empty, keep current
    if not new_prompt:
        new_prompt = current_prompt

    return {
        "new_prompt": new_prompt,
        "change_summary": change_summary,
    }
