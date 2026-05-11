import asyncio
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import User
from schemas import SchedulerResult
from services.newsletter_service import create_and_send_newsletter

router = APIRouter(prefix="/scheduler", tags=["scheduler"])
logger = logging.getLogger(__name__)

# In-memory lock to prevent duplicate scheduled runs within a 23-hour window
_LAST_SCHEDULER_RUN: datetime | None = None
_MIN_SCHEDULER_INTERVAL_HOURS = 23


@router.post("/run", response_model=SchedulerResult)
async def run_scheduler(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    global _LAST_SCHEDULER_RUN

    # 1. Authenticate
    key = request.headers.get("X-Scheduler-Key")
    if key != settings.scheduler_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 2. Idempotency lock — reject duplicate runs within 23 hours
    if _LAST_SCHEDULER_RUN is not None:
        elapsed = datetime.now(timezone.utc) - _LAST_SCHEDULER_RUN
        if elapsed < timedelta(hours=_MIN_SCHEDULER_INTERVAL_HOURS):
            logger.info(f"Scheduler rejected: last run was {elapsed.total_seconds()/3600:.1f} hours ago")
            return {"sent": 0, "failed": 0, "total": 0}
    _LAST_SCHEDULER_RUN = datetime.now(timezone.utc)

    # 3. Fetch all active users
    result = await db.execute(select(User).where(User.is_active == True))
    users = result.scalars().all()

    # 3. Process users sequentially with delay to avoid rate limits
    sent = 0
    failed = 0
    for user in users:
        try:
            newsletter = await create_and_send_newsletter(db, user, source="scheduled")
            if newsletter:
                logger.info(f"Scheduled newsletter sent to user {user.id} ({user.email})")
                sent += 1
            else:
                logger.info(f"Skipped scheduled newsletter for user {user.id} (already sent today)")
        except Exception as exc:
            logger.exception(f"Failed to send scheduled newsletter to user {user.id}: {exc}")
            failed += 1
        # Small delay between users to stay well under Groq rate limits
        await asyncio.sleep(3)

    await db.commit()

    return {"sent": sent, "failed": failed, "total": len(users)}
