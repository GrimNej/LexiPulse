import logging

from fastapi import APIRouter, Request, Depends, HTTPException, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import User, Newsletter, FeedbackToken
from services.newsletter_service import create_and_send_newsletter
from services.token_service import get_valid_token, check_rate_limit

router = APIRouter(prefix="/feedback", tags=["feedback"])
logger = logging.getLogger(__name__)


@router.get("")
async def handle_feedback(
    request: Request,
    t: str,
    a: str,
    db: AsyncSession = Depends(get_db),
):
    action = a.lower().strip()
    if action not in ("too_easy", "just_right", "too_hard", "want_more"):
        return None  # silent 204 effectively handled by empty response

    # Rate limit check
    if not check_rate_limit(t):
        logger.warning(f"Rate limited feedback token {t[:8]}...")
        return None

    # Validate token
    token = await get_valid_token(db, t)
    if not token:
        logger.info(f"Invalid or expired token: {t[:8]}...")
        return None

    # Load user
    user_result = await db.execute(select(User).where(User.id == token.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        return None

    if action in ("too_easy", "just_right", "too_hard"):
        if token.level_adjusted:
            logger.info(f"Token {t[:8]}... level_adjusted already, ignoring {action}")
            return None

        if action == "too_easy":
            user.level = min(user.level + 1, 10)
        elif action == "too_hard":
            user.level = max(user.level - 1, 1)
        # just_right: no level change

        token.level_adjusted = True
        logger.info(f"User {user.id} level adjusted to {user.level} via {action}")

    elif action == "want_more":
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
            return None

        try:
            newsletter = await create_and_send_newsletter(db, user, source="on_demand")
            if newsletter:
                logger.info(f"On-demand newsletter sent to user {user.id}")
            else:
                logger.info(f"On-demand newsletter skipped for user {user.id}")
        except Exception as exc:
            logger.exception(f"Failed on-demand send for user {user.id}: {exc}")

    await db.commit()
    return Response(status_code=204)
