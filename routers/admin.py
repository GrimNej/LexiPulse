import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db
from models import User, Newsletter, SentWord
from schemas import UserCreate, UserUpdate, UserRead, UserStats
from services.newsletter_service import create_and_send_newsletter
from services.token_service import generate_unsubscribe_token

router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


def verify_admin(request: Request):
    key = request.headers.get("X-Admin-Key")
    if key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Forbidden")
    return True


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    request: Request,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        level=data.level,
        is_active=data.is_active,
        timezone=data.timezone,
        topic=data.topic,
        unsubscribe_token=generate_unsubscribe_token(),
    )
    db.add(user)
    await db.flush()
    await db.commit()
    return user


@router.get("/users", response_model=List[UserStats])
async def list_users(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()

    # Gather stats efficiently
    user_ids = [u.id for u in users]

    # Newsletter counts
    nl_counts = {}
    if user_ids:
        nl_result = await db.execute(
            select(Newsletter.user_id, func.count(Newsletter.id))
            .where(Newsletter.user_id.in_(user_ids))
            .group_by(Newsletter.user_id)
        )
        for uid, cnt in nl_result.all():
            nl_counts[uid] = cnt

    # Word counts
    word_counts = {}
    if user_ids:
        word_result = await db.execute(
            select(SentWord.user_id, func.count(SentWord.id))
            .where(SentWord.user_id.in_(user_ids))
            .group_by(SentWord.user_id)
        )
        for uid, cnt in word_result.all():
            word_counts[uid] = cnt

    response = []
    for user in users:
        response.append(
            UserStats(
                id=user.id,
                name=user.name,
                email=user.email,
                level=user.level,
                is_active=user.is_active,
                timezone=user.timezone,
                topic=user.topic,
                created_at=user.created_at,
                total_newsletters=nl_counts.get(user.id, 0),
                total_words=word_counts.get(user.id, 0),
                current_level=user.level,
            )
        )
    return response


@router.get("/users/{user_id}", response_model=UserStats)
async def get_user(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    nl_result = await db.execute(
        select(func.count(Newsletter.id)).where(Newsletter.user_id == user_id)
    )
    word_result = await db.execute(
        select(func.count(SentWord.id)).where(SentWord.user_id == user_id)
    )

    return UserStats(
        id=user.id,
        name=user.name,
        email=user.email,
        level=user.level,
        is_active=user.is_active,
        timezone=user.timezone,
        topic=user.topic,
        created_at=user.created_at,
        total_newsletters=nl_result.scalar_one(),
        total_words=word_result.scalar_one(),
        current_level=user.level,
    )


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    request: Request,
    user_id: UUID,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.name is not None:
        user.name = data.name
    if data.email is not None:
        existing = await db.execute(select(User).where(User.email == data.email))
        if existing.scalar_one_or_none() and data.email != user.email:
            raise HTTPException(status_code=409, detail="Email already registered")
        user.email = data.email
    if data.level is not None:
        user.level = data.level
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.timezone is not None:
        user.timezone = data.timezone
    if data.topic is not None:
        user.topic = data.topic

    await db.commit()
    return user


@router.delete("/users/{user_id}", status_code=204)
async def deactivate_user(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.commit()
    return None


@router.post("/users/{user_id}/send-now", status_code=202)
async def send_now(
    request: Request,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin),
):
    """Manually trigger a newsletter send for a user. Does not count toward daily cap."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")

    try:
        newsletter = await create_and_send_newsletter(db, user, source="admin_manual", force=True)
        if newsletter:
            await db.commit()
            logger.info(f"Admin manual send completed for user {user.id}")
            return {"status": "sent", "newsletter_id": str(newsletter.id)}
        else:
            return {"status": "skipped", "detail": "Could not generate newsletter"}
    except Exception as exc:
        logger.exception(f"Admin manual send failed for user {user.id}: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
