import logging

from fastapi import APIRouter, Request, Depends, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, Newsletter, FeedbackToken
from services.newsletter_service import create_and_send_newsletter
from services.token_service import get_valid_token, check_rate_limit

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger(__name__)

AUTO_CLOSE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>mofa-letter</title>
  <style>
    body { margin: 0; display: flex; align-items: center; justify-content: center; height: 100vh;
           font-family: system-ui, -apple-system, sans-serif; background: #111827; color: #e6f4f1; }
    .box { text-align: center; padding: 40px; }
    h1 { font-size: 22px; font-weight: 500; margin-bottom: 8px; }
    p { font-size: 14px; color: #9ca3af; }
  </style>
</head>
<body>
  <div class="box">
    <h1>Thanks.</h1>
    <p>This tab will close automatically.</p>
  </div>
  <script>setTimeout(() => window.close(), 800);</script>
</body>
</html>
"""


@router.get("")
async def handle_feedback(
    request: Request,
    t: str,
    a: str,
    db: AsyncSession = Depends(get_db),
):
    action = a.lower().strip()
    if action not in ("want_more",):
        return Response(content=AUTO_CLOSE_HTML, media_type="text/html")

    # Rate limit check
    if not check_rate_limit(t):
        logger.warning(f"Rate limited feedback token {t[:8]}...")
        return Response(content=AUTO_CLOSE_HTML, media_type="text/html")

    # Validate token
    token = await get_valid_token(db, t)
    if not token:
        logger.info(f"Invalid or expired token: {t[:8]}...")
        return Response(content=AUTO_CLOSE_HTML, media_type="text/html")

    # Load user
    user_result = await db.execute(select(User).where(User.id == token.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        return Response(content=AUTO_CLOSE_HTML, media_type="text/html")

    if action == "want_more":
        # Count today's newsletters
        today = func.current_date()
        count_result = await db.execute(
            select(func.count(Newsletter.id)).where(
                Newsletter.user_id == user.id,
                Newsletter.send_date == today,
            )
        )
        today_count = count_result.scalar_one()

        if today_count >= 5:
            logger.info(f"User {user.id} daily cap reached ({today_count}), ignoring want_more")
            return Response(content=AUTO_CLOSE_HTML, media_type="text/html")

        try:
            newsletter = await create_and_send_newsletter(db, user, source="on_demand")
            if newsletter:
                logger.info(f"On-demand newsletter sent to user {user.id}")
            else:
                logger.info(f"On-demand newsletter skipped for user {user.id}")
        except Exception as exc:
            logger.exception(f"Failed on-demand send for user {user.id}: {exc}")

    await db.commit()
    return Response(content=AUTO_CLOSE_HTML, media_type="text/html")
