import logging
from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models import User, Newsletter
from services.email_service import render_newsletter_email, send_email
from services.token_service import create_feedback_token, generate_unsubscribe_token
from services.content_agent import generate_newsletter_with_qa
from services.web_search import search_web, format_search_context, is_time_sensitive_prompt, build_search_query


logger = logging.getLogger(__name__)

DEFAULT_PROMPT = "A concise, engaging daily newsletter with interesting insights, key developments, and actionable takeaways tailored to today's world."


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
    Generate content via AI creative director, design layout, render email, send.
    """
    # Idempotency
    if source == "scheduled" and not force:
        already_sent = await has_scheduled_newsletter_today(db, user.id)
        if already_sent:
            return None

    # Daily cap check
    if source in ("scheduled", "on_demand"):
        today_count = await count_newsletters_today(db, user.id)
        if today_count >= 3:
            return None
        sequence_num = today_count + 1
    else:
        sequence_num = await count_newsletters_today(db, user.id) + 1

    # Get user's prompt
    user_prompt = user.newsletter_prompt or DEFAULT_PROMPT

    # Stage 1: Web search (conditional)
    today = date.today()
    date_str = today.strftime("%B %d, %Y")
    search_context = ""
    if is_time_sensitive_prompt(user_prompt):
        try:
            search_query = build_search_query(user_prompt, date_str)
            search_results = await search_web(search_query, max_results=5, use_news=True)
            search_context = format_search_context(search_results)
        except Exception:
            search_context = ""

    # Stage 2 & 3: Generate with QA review loop
    try:
        content = await generate_newsletter_with_qa(user_prompt, date_str, search_context=search_context)
    except Exception as exc:
        import traceback
        logger.error(f"Newsletter generation failed for user {user.id}: {exc}")
        traceback.print_exc()
        # Fallback apology newsletter
        content = {
            "title": "Your Daily Brief",
            "subtitle": date_str,
            "mood": "minimal",
            "sections": [
                {
                    "heading": "",
                    "content": "We encountered an issue generating your custom newsletter today. Our creative director is being retrained. Your next edition will arrive on schedule.",
                    "component": "content_card",
                    "style": "bordered",
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
        prompt_used=user_prompt,
        content_structure=content,
        design_metadata={"mood": content.get("mood", "minimal")},
        source=source,
        sent_at=datetime.now(timezone.utc),
    )
    db.add(newsletter)
    await db.flush()

    # Create feedback token
    token = await create_feedback_token(db, user.id, newsletter.id)

    # Ensure unsubscribe token
    if not user.unsubscribe_token:
        user.unsubscribe_token = generate_unsubscribe_token()
        await db.flush()

    # Render and send email
    send_date_str = today.strftime("%B %d")
    subject = content.get("title", "Your Daily Brief")
    html_body = render_newsletter_email(
        user_name=user.name,
        user_id=user.id,
        title=content.get("title", "Your Daily Brief"),
        subtitle=content.get("subtitle", send_date_str),
        mood=content.get("mood", "minimal"),
        sections=content.get("sections", []),
        closing=content.get("closing", "Until tomorrow."),
        token=token,
        send_date=send_date_str,
        unsubscribe_token=user.unsubscribe_token,
        sources=content.get("sources", []),
    )
    await send_email(user.email, subject, html_body)

    return newsletter
