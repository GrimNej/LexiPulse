from datetime import datetime
from typing import List, Optional
from uuid import UUID

import httpx
from jinja2 import Environment, FileSystemLoader, select_autoescape
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings

# Jinja2 setup
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

template = env.get_template("newsletter.html")

RESEND_URL = "https://api.resend.com/emails"


def render_newsletter_email(
    user_name: str,
    user_id: UUID,
    level: int,
    words: List[dict],
    token: str,
    send_date: str,
    unsubscribe_token: str,
) -> str:
    """Legacy renderer for vocabulary-style newsletters."""
    html = template.render(
        user_name=user_name,
        user_id=user_id,
        level=level,
        words=words,
        token=token,
        send_date=send_date,
        base_url=settings.app_base_url.rstrip("/"),
        unsubscribe_token=unsubscribe_token,
    )
    return html


def render_dynamic_newsletter_email(
    user_name: str,
    user_id: UUID,
    title: str,
    subtitle: str,
    sections: List[dict],
    closing: str,
    token: str,
    send_date: str,
    unsubscribe_token: str,
) -> str:
    """Render a dynamic newsletter from agent-generated content."""
    html = template.render(
        user_name=user_name,
        user_id=user_id,
        title=title,
        subtitle=subtitle,
        sections=sections,
        closing=closing,
        token=token,
        send_date=send_date,
        base_url=settings.app_base_url.rstrip("/"),
        unsubscribe_token=unsubscribe_token,
    )
    return html


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
async def send_email(to_email: str, subject: str, html_body: str) -> str:
    """Send email via Resend. Returns the Resend message ID."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            RESEND_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{settings.from_name} <{settings.from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("id", "")
