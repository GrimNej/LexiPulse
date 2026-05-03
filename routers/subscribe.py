import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import SubscribeRequest, SubscribeResponse
from services.token_service import generate_unsubscribe_token

router = APIRouter(prefix="/subscribe", tags=["subscribe"])
logger = logging.getLogger(__name__)


@router.post("", response_model=SubscribeResponse, status_code=201)
async def subscribe(data: SubscribeRequest, db: AsyncSession = Depends(get_db)):
    """Public endpoint for users to subscribe to the newsletter."""
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == data.email))
    user = existing.scalar_one_or_none()

    if user:
        if user.is_active:
            return SubscribeResponse(
                status="already_subscribed",
                message="This email is already subscribed to the newsletter.",
                user_id=user.id,
            )
        else:
            # Reactivate
            user.is_active = True
            user.name = data.name
            user.topic = data.topic
            user.timezone = data.timezone
            if data.newsletter_prompt:
                user.newsletter_prompt = data.newsletter_prompt
            await db.commit()
            logger.info(f"User reactivated via subscribe: {user.email}")
            return SubscribeResponse(
                status="reactivated",
                message="Welcome back! Your subscription has been reactivated.",
                user_id=user.id,
            )

    # Create new user
    new_user = User(
        name=data.name,
        email=data.email,
        level=5,
        is_active=True,
        timezone=data.timezone,
        topic=data.topic,
        newsletter_prompt=data.newsletter_prompt,
        unsubscribe_token=generate_unsubscribe_token(),
    )
    db.add(new_user)
    await db.commit()
    logger.info(f"New subscriber: {new_user.email}")

    return SubscribeResponse(
        status="subscribed",
        message="Welcome! You've successfully subscribed to the newsletter.",
        user_id=new_user.id,
    )
