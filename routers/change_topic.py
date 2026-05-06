"""
Change Topic — lets users update their newsletter prompt via natural language.

Uses the unsubscribe token for authentication (persistent, per-user).
Rate limited to 1 change per hour.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from services.prompt_rewriter import rewrite_prompt

router = APIRouter(prefix="/change-topic", tags=["change-topic"])
logger = logging.getLogger(__name__)

# Rate limiting: token -> last_change_timestamp
_change_rate_limits: dict[str, datetime] = {}
_RATE_LIMIT_SECONDS = 3600  # 1 hour


def _check_rate_limit(token_str: str) -> bool:
    """Returns True if allowed, False if rate limited."""
    now = datetime.now(timezone.utc)
    last_change = _change_rate_limits.get(token_str)
    if last_change and (now - last_change).total_seconds() < _RATE_LIMIT_SECONDS:
        return False
    _change_rate_limits[token_str] = now
    return True


def _render_form_page(current_prompt: str, error: Optional[str] = None) -> str:
    error_html = f'<p style="color:#ef4444;font-size:14px;margin:0 0 16px 0;">{error}</p>' if error else ""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Change Your Topic — mofa-letter</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #111827; color: #f9fafb; line-height: 1.6;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; padding: 24px;
    }}
    .container {{ max-width: 520px; width: 100%; }}
    .brand {{
      font-size: 12px; font-weight: 600; letter-spacing: 0.15em;
      text-transform: uppercase; color: #d97706; margin-bottom: 12px;
    }}
    h1 {{ font-size: 28px; font-weight: 600; margin-bottom: 8px; letter-spacing: -0.01em; }}
    .subtitle {{ color: #9ca3af; font-size: 15px; margin-bottom: 28px; }}
    .current-box {{
      background: #1f2937; border: 1px solid #374151; border-radius: 10px;
      padding: 16px 20px; margin-bottom: 24px;
    }}
    .current-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.1em; color: #6b7280; margin-bottom: 6px; }}
    .current-text {{ font-size: 14px; color: #d1d5db; font-style: italic; }}
    label {{ display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; color: #e5e7eb; }}
    textarea {{
      width: 100%; min-height: 120px; padding: 14px 16px;
      background: #1f2937; border: 1px solid #374151; border-radius: 8px;
      color: #f9fafb; font-size: 15px; font-family: inherit; line-height: 1.5;
      resize: vertical; outline: none; transition: border-color 0.2s;
    }}
    textarea:focus {{ border-color: #d97706; }}
    .hint {{ font-size: 13px; color: #6b7280; margin-top: 6px; }}
    button {{
      margin-top: 20px; width: 100%; padding: 12px 24px;
      background: #d97706; color: #fff; border: none; border-radius: 9999px;
      font-size: 15px; font-weight: 600; cursor: pointer; transition: background 0.2s;
    }}
    button:hover {{ background: #b45309; }}
    .footer {{ text-align: center; margin-top: 24px; font-size: 12px; color: #4b5563; }}
  </style>
</head>
<body>
  <div class="container">
    <p class="brand">mofa-letter</p>
    <h1>Change Your Topic</h1>
    <p class="subtitle">Tell us what you want differently. We'll rewrite your newsletter prompt.</p>
    {error_html}
    <div class="current-box">
      <p class="current-label">Current Prompt</p>
      <p class="current-text">{current_prompt}</p>
    </div>
    <form method="post" action="">
      <label for="request">What would you like to change?</label>
      <textarea id="request" name="request" placeholder="e.g. 'Also include cybersecurity news' or 'I want cooking tips instead'" required></textarea>
      <p class="hint">Be specific — the more detail, the better your newsletter.</p>
      <button type="submit">Update My Newsletter</button>
    </form>
    <p class="footer">Changes take effect on your next newsletter. Limited to 1 change per hour.</p>
  </div>
</body>
</html>'''


def _render_success_page(old_prompt: str, new_prompt: str, change_summary: str) -> str:
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Topic Updated — mofa-letter</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #111827; color: #f9fafb; line-height: 1.6;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; padding: 24px;
    }}
    .container {{ max-width: 520px; width: 100%; text-align: center; }}
    .check {{ font-size: 48px; margin-bottom: 16px; }}
    h1 {{ font-size: 26px; font-weight: 600; margin-bottom: 8px; }}
    .subtitle {{ color: #9ca3af; font-size: 15px; margin-bottom: 32px; }}
    .box {{
      background: #1f2937; border: 1px solid #374151; border-radius: 10px;
      padding: 20px; text-align: left; margin-bottom: 16px;
    }}
    .box-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.1em; color: #6b7280; margin-bottom: 6px; }}
    .old {{ color: #9ca3af; font-style: italic; text-decoration: line-through; }}
    .new {{ color: #f9fafb; }}
    .arrow {{ text-align: center; color: #d97706; font-size: 20px; margin: 8px 0; }}
    .summary {{ color: #d97706; font-size: 14px; font-weight: 500; margin-top: 4px; }}
    .footer {{ font-size: 13px; color: #6b7280; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="check">✓</div>
    <h1>Your Topic Has Been Updated</h1>
    <p class="subtitle">Your next newsletter will reflect this change.</p>
    <div class="box">
      <p class="box-label">Before</p>
      <p class="old">{old_prompt}</p>
    </div>
    <div class="arrow">↓</div>
    <div class="box">
      <p class="box-label">After</p>
      <p class="new">{new_prompt}</p>
      <p class="summary">{change_summary}</p>
    </div>
    <p class="footer">This tab will close automatically in 5 seconds.</p>
    <script>setTimeout(() => window.close(), 5000);</script>
  </div>
</body>
</html>'''


def _render_rate_limited_page() -> str:
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Rate Limited — mofa-letter</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #111827; color: #f9fafb; line-height: 1.6;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh; padding: 24px; text-align: center;
    }
    .container { max-width: 400px; }
    h1 { font-size: 22px; font-weight: 600; margin-bottom: 8px; }
    p { color: #9ca3af; font-size: 15px; margin-bottom: 20px; }
    .footer { font-size: 12px; color: #4b5563; }
  </style>
</head>
<body>
  <div class="container">
    <h1>Slow Down</h1>
    <p>You can only change your topic once per hour. Please try again later.</p>
    <p class="footer">This tab will close automatically.</p>
    <script>setTimeout(() => window.close(), 3000);</script>
  </div>
</body>
</html>'''


@router.get("", response_class=HTMLResponse)
async def change_topic_form(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Show the change-topic form with the user's current prompt."""
    result = await db.execute(
        select(User).where(User.unsubscribe_token == token)
    )
    user = result.scalar_one_or_none()
    if not user:
        return HTMLResponse(content="<h1>Invalid link</h1>", status_code=400)

    current_prompt = user.newsletter_prompt or "Default: interesting daily insights"
    return HTMLResponse(content=_render_form_page(current_prompt))


@router.post("", response_class=HTMLResponse)
async def change_topic_submit(
    request: Request,
    token: str,
    request_text: str = Form(..., alias="request"),
    db: AsyncSession = Depends(get_db),
):
    """Process the topic change request, rewrite the prompt, update the user."""
    # Validate token
    result = await db.execute(
        select(User).where(User.unsubscribe_token == token)
    )
    user = result.scalar_one_or_none()
    if not user:
        return HTMLResponse(content="<h1>Invalid link</h1>", status_code=400)

    # Rate limit
    if not _check_rate_limit(token):
        return HTMLResponse(content=_render_rate_limited_page())

    # Validate request
    request_clean = request_text.strip()
    if len(request_clean) < 3:
        current_prompt = user.newsletter_prompt or "Default: interesting daily insights"
        return HTMLResponse(
            content=_render_form_page(current_prompt, error="Please write a bit more about what you want."),
            status_code=400,
        )

    # Rewrite prompt
    current_prompt = user.newsletter_prompt or ""
    try:
        result = await rewrite_prompt(current_prompt, request_clean)
    except Exception as exc:
        logger.exception(f"Prompt rewrite failed for user {user.id}: {exc}")
        current_prompt = user.newsletter_prompt or "Default: interesting daily insights"
        return HTMLResponse(
            content=_render_form_page(current_prompt, error="Something went wrong. Please try again."),
            status_code=500,
        )

    # Update user
    user.newsletter_prompt = result["new_prompt"]
    await db.commit()

    logger.info(f"User {user.id} changed topic: {result['change_summary']}")

    return HTMLResponse(
        content=_render_success_page(
            old_prompt=current_prompt or "(default)",
            new_prompt=result["new_prompt"],
            change_summary=result["change_summary"],
        )
    )
