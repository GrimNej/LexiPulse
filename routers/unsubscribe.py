import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import UnsubscribeResponse

router = APIRouter(prefix="/unsubscribe", tags=["unsubscribe"])
logger = logging.getLogger(__name__)

UNSUBSCRIBE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Unsubscribed — mofa-letter</title>
  <style>
    body { margin: 0; padding: 0; background: #111827; font-family: system-ui, -apple-system, sans-serif; }
    .container { max-width: 480px; margin: 80px auto; text-align: center; padding: 0 24px; }
    h1 { color: #ffffff; font-size: 28px; margin-bottom: 12px; }
    p { color: #9ca3af; font-size: 16px; line-height: 1.6; }
    .accent { color: #d97706; }
    .btn {
      display: inline-block; margin-top: 24px; padding: 12px 28px;
      background: #0f766e; color: #fff; text-decoration: none;
      border-radius: 9999px; font-size: 14px; font-weight: 500;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>You've been <span class="accent">unsubscribed</span>.</h1>
    <p>We're sorry to see you go. You will no longer receive newsletters from mofa-letter.</p>
    <p style="font-size: 13px; margin-top: 24px;">Changed your mind?</p>
    <a href="https://lexipulse.mofa.ai" class="btn">Resubscribe</a>
  </div>
</body>
</html>
"""


@router.get("", response_class=HTMLResponse)
async def unsubscribe(token: str, db: AsyncSession = Depends(get_db)):
    """Unsubscribe a user via their unique unsubscribe token."""
    result = await db.execute(select(User).where(User.unsubscribe_token == token))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Invalid unsubscribe link")

    user.is_active = False
    await db.commit()
    logger.info(f"User unsubscribed: {user.email}")

    return HTMLResponse(content=UNSUBSCRIBE_HTML)
