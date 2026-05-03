from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import User, Newsletter
from services.email_service import render_dynamic_newsletter_email, send_email
from services.token_service import create_feedback_token, generate_unsubscribe_token
from services.content_agent import generate_newsletter_content


DEFAULT_PROMPT = "Three advanced English vocabulary words with pronunciation, etymology, definitions, and example sentences. The words should be genuinely rare and rewarding to learn."


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
    Generate content via AI agent, create newsletter record, send email.

    Args:
        db: Database session
        user: Target user
        source: 'scheduled', 'on_demand', or 'admin_manual'
        force: If True, bypass the daily duplicate check
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

    # Get user's prompt or use default
    user_prompt = user.newsletter_prompt or DEFAULT_PROMPT

    # Generate content via AI agent
    today = date.today()
    date_str = today.strftime("%B %d, %Y")
    try:
        content = await generate_newsletter_content(user_prompt, date_str)
    except Exception as exc:
        # Fallback: create a simple apology newsletter
        content = {
            "title": "Your Daily Brief",
            "subtitle": date_str,
            "sections": [
                {
                    "heading": "We'll Be Right Back",
                    "content": "We encountered an issue generating your custom newsletter today. Our AI agent is being retrained as we speak. Your next edition will arrive on schedule.",
                    "style": "paragraph",
                }
            ],
            "closing": "Thank you for your patience.",
        }

    # Create newsletter record
    newsletter = Newsletter(
        user_id=user.id,
        send_date=today,
        sequence_num=sequence_num,
        level_at_send=user.level or 5,
        words=None,
        prompt_used=user_prompt,
        content_structure=content,
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

    # Render and send email
    send_date_str = today.strftime("%B %d")
    subject = content.get("title", "Your Daily Brief")
    html_body = render_dynamic_newsletter_email(
        user_name=user.name,
        user_id=user.id,
        title=content.get("title", "Your Daily Brief"),
        subtitle=content.get("subtitle", send_date_str),
        sections=content.get("sections", []),
        closing=content.get("closing", "Until tomorrow."),
        token=token,
        send_date=send_date_str,
        unsubscribe_token=user.unsubscribe_token,
    )
    await send_email(user.email, subject, html_body)

    return newsletter
