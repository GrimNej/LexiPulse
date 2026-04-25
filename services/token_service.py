import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import FeedbackToken

# In-memory rate limit store: token -> last_click_timestamp
_feedback_rate_limits: dict[str, datetime] = {}
_RATE_LIMIT_SECONDS = 5


def generate_feedback_token() -> str:
    return secrets.token_hex(32)


async def create_feedback_token(
    db: AsyncSession,
    user_id: UUID,
    newsletter_id: UUID,
) -> str:
    token_str = generate_feedback_token()
    expires = datetime.now(timezone.utc) + timedelta(hours=48)
    token = FeedbackToken(
        user_id=user_id,
        newsletter_id=newsletter_id,
        token=token_str,
        expires_at=expires,
    )
    db.add(token)
    await db.flush()
    return token_str


async def get_valid_token(db: AsyncSession, token_str: str) -> Optional[FeedbackToken]:
    result = await db.execute(
        select(FeedbackToken).where(
            FeedbackToken.token == token_str,
            FeedbackToken.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


def check_rate_limit(token_str: str) -> bool:
    """Returns True if the request is allowed, False if rate limited."""
    now = datetime.now(timezone.utc)
    last_click = _feedback_rate_limits.get(token_str)
    if last_click and (now - last_click).total_seconds() < _RATE_LIMIT_SECONDS:
        return False
    _feedback_rate_limits[token_str] = now
    return True


def cleanup_old_rate_limits():
    """Remove rate limit entries older than 1 hour to prevent memory growth."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=1)
    to_remove = [k for k, v in _feedback_rate_limits.items() if v < cutoff]
    for k in to_remove:
        del _feedback_rate_limits[k]
