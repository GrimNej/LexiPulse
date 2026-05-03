from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import User, Newsletter, SentWord
from services.word_generator import generate_unique_words, WordGenerationError
from services.email_service import render_newsletter_email, send_email
from services.token_service import create_feedback_token, generate_unsubscribe_token


async def count_newsletters_today(db: AsyncSession, user_id: UUID) -> int:
    today = date.today()
    result = await db.execute(
        select(func.count(Newsletter.id)).where(
            Newsletter.user_id == user_id,
            Newsletter.send_date == today,
        )
    )
    return result.scalar_one()


async def has_scheduled_newsletter_today(db: AsyncSession, user_id: UUID) -> bool:
    today = date.today()
    result = await db.execute(
        select(Newsletter.id).where(
            Newsletter.user_id == user_id,
            Newsletter.send_date == today,
            Newsletter.sequence_num == 1,
        )
    )
    return result.scalar_one_or_none() is not None


async def create_and_send_newsletter(
    db: AsyncSession,
    user: User,
    source: str = "scheduled",
    force: bool = False,
) -> Optional[Newsletter]:
    """
    Generate words, create newsletter record, send email, store sent_words.
    
    Args:
        db: Database session
        user: Target user
        source: 'scheduled', 'on_demand', or 'admin_manual'
        force: If True, bypass the daily duplicate check (used for admin manual send)
    """
    # Idempotency: if scheduled newsletter already exists for today, skip
    if source == "scheduled" and not force:
        already_sent = await has_scheduled_newsletter_today(db, user.id)
        if already_sent:
            return None

    # Daily cap check (skip for admin_manual)
    if source in ("scheduled", "on_demand"):
        today_count = await count_newsletters_today(db, user.id)
        if today_count >= 5:
            return None
        sequence_num = today_count + 1
    else:
        # admin_manual: does not count toward cap
        sequence_num = await count_newsletters_today(db, user.id) + 1

    # Generate words
    try:
        words_data = await generate_unique_words(db, user.id, user.level, count=3)
    except WordGenerationError:
        raise

    # Create newsletter record
    today = date.today()
    newsletter = Newsletter(
        user_id=user.id,
        send_date=today,
        sequence_num=sequence_num,
        level_at_send=user.level,
        words=words_data,
        source=source,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(newsletter)
    await db.flush()  # Get newsletter.id

    # Create feedback token
    token = await create_feedback_token(db, user.id, newsletter.id)

    # Ensure user has an unsubscribe token
    if not user.unsubscribe_token:
        user.unsubscribe_token = generate_unsubscribe_token()
        await db.flush()

    # Write sent_words
    for word_data in words_data:
        sent_word = SentWord(
            user_id=user.id,
            word=word_data["word"],
            newsletter_id=newsletter.id,
            level_at_send=user.level,
            sent_at=datetime.now(timezone.utc),
        )
        db.add(sent_word)

    await db.flush()

    # Render and send email
    send_date_str = today.strftime("%B %d")
    subject = f"Three words for {send_date_str}"
    html_body = render_newsletter_email(
        user_name=user.name,
        user_id=user.id,
        level=user.level,
        words=words_data,
        token=token,
        send_date=send_date_str,
        unsubscribe_token=user.unsubscribe_token,
    )
    await send_email(user.email, subject, html_body)

    return newsletter
