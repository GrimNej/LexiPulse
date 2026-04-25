import asyncio
import logging

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


@router.post("/run", response_model=SchedulerResult)
async def run_scheduler(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # 1. Authenticate
    key = request.headers.get("X-Scheduler-Key")
    if key != settings.scheduler_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 2. Fetch all active users
    result = await db.execute(select(User).where(User.is_active == True))
    users = result.scalars().all()

    # 3. Process all users concurrently
    async def send_for_user(user: User) -> bool:
        try:
            newsletter = await create_and_send_newsletter(db, user, source="scheduled")
            if newsletter:
                logger.info(f"Scheduled newsletter sent to user {user.id} ({user.email})")
            else:
                logger.info(f"Skipped scheduled newsletter for user {user.id} (already sent today)")
            return True
        except Exception as exc:
            logger.exception(f"Failed to send scheduled newsletter to user {user.id}: {exc}")
            return False

    results = await asyncio.gather(
        *[send_for_user(user) for user in users],
        return_exceptions=True,
    )

    sent = sum(1 for r in results if r is True)
    failed = sum(1 for r in results if isinstance(r, Exception) or r is False)

    await db.commit()

    return {"sent": sent, "failed": failed, "total": len(users)}
