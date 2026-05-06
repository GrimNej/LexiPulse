"""
Email rendering and sending for mofa-letter.

The renderer builds the complete HTML email in Python using the component library
for maximum visual control and email-client compatibility.
"""
from typing import List, Dict, Any
from uuid import UUID

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from services.components import render_component
from services.themes import get_theme, build_inline_styles

RESEND_URL = "https://api.resend.com/emails"


def render_newsletter_email(
    user_name: str,
    user_id: UUID,
    title: str,
    subtitle: str,
    mood: str,
    sections: List[Dict[str, Any]],
    closing: str,
    token: str,
    send_date: str,
    unsubscribe_token: str,
    sources: List[Dict[str, str]] = None,
) -> str:
    """
    Build a complete, beautiful HTML email using the Adaptive Component Matrix.
    """
    # Load theme and build inline styles
    theme = get_theme(mood)
    light_styles = build_inline_styles(theme, is_dark=False)
    dark_styles = build_inline_styles(theme, is_dark=True)

    # Render all content sections
    # If first section is a hero with no heading, inject the newsletter title
    processed_sections = list(sections)
    if processed_sections and processed_sections[0].get("component") == "hero":
        if not processed_sections[0].get("heading", "").strip():
            processed_sections[0] = dict(processed_sections[0])
            processed_sections[0]["heading"] = title
    
    body_sections_html = ""
    for section in processed_sections:
        body_sections_html += render_component(
            component_type=section.get("component", "content_card"),
            style=section.get("style", "bordered"),
            heading=section.get("heading", ""),
            content=section.get("content", ""),
            styles=light_styles,
            source_url=section.get("source_url", ""),
        )

    # Build sources section — deduplicate by URL
    sources = sources or []
    seen = set()
    unique_sources = []
    for src in sources:
        url = src.get("url", "")
        if url and url.lower() not in seen:
            seen.add(url.lower())
            unique_sources.append(src)
    
    sources_html = ""
    if unique_sources:
        source_items = ""
        for src in unique_sources:
            source_title = src.get("title", "Source")
            source_url = src.get("url", "")
            if source_url:
                source_items += f'<tr><td style="padding:0 0 8px 0;font-family:system-ui,-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;font-size:14px;color:{light_styles["body_text"]};"><a href="{source_url}" style="color:{light_styles["accent_color"]};text-decoration:none;">&bull; {source_title}</a></td></tr>'
        sources_html = f'''<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
  <tr>
    <td style="padding:24px 0;border-top:1px solid {light_styles['border_color']};">
      <p style="font-family:{light_styles['header_font']};font-size:12px;font-weight:600;letter-spacing:0.15em;text-transform:uppercase;color:{light_styles['muted_color']};margin:0 0 12px 0;">Sources</p>
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        {source_items}
      </table>
    </td>
  </tr>
</table>'''
    closing_html = ""
    if closing and closing.strip():
        closing_html = f'''<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
  <tr>
    <td style="padding:{light_styles['section_pad']} 0;">
      <p style="font-family:Georgia,'Times New Roman',serif;font-size:16px;font-style:italic;line-height:1.7;color:{light_styles['body_text']};margin:0;">{closing}</p>
    </td>
  </tr>
</table>'''

    # Build change-topic + send-more CTA section
    change_topic_url = f"{settings.app_base_url.rstrip('/')}/change-topic?token={unsubscribe_token}"
    want_more_url = f"{settings.app_base_url.rstrip('/')}/feedback?t={token}&a=want_more"

    cta_html = f'''<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
  <tr>
    <td style="padding:24px 0;border-top:1px solid {light_styles['border_color']};">
      <!-- Change Topic button -->
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto 12px auto;">
        <tr>
          <td align="center">
            <a href="{change_topic_url}" style="display:inline-block;padding:10px 24px;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;font-weight:500;color:{light_styles['muted_color']};background-color:transparent;border:1px solid {light_styles['border_color']};border-radius:9999px;text-decoration:none;">
              Change Topic
            </a>
          </td>
        </tr>
      </table>
      <!-- Send Me More button -->
      <table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto 8px auto;">
        <tr>
          <td align="center">
            <a href="{want_more_url}" style="display:inline-block;padding:10px 24px;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:13px;font-weight:500;color:{light_styles['accent_color']};background-color:transparent;border:1px solid {light_styles['accent_color']};border-radius:9999px;text-decoration:none;">
              Send Me More
            </a>
          </td>
        </tr>
      </table>
      <!-- Limit note -->
      <p style="margin:0;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:12px;text-align:center;color:{light_styles['muted_color']};">
        You can receive up to 3 extra emails per day
      </p>
    </td>
  </tr>
</table>'''

    # Build footer
    footer_html = f'''<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
  <tr>
    <td style="padding-top:24px;border-top:1px solid {light_styles['border_color']};">
      <p style="margin:0;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:12px;text-align:center;color:{light_styles['muted_color']};line-height:1.6;">
        mofa-letter &middot; Sent to you daily
      </p>
      <p style="margin:8px 0 0 0;font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:11px;text-align:center;color:{light_styles['muted_color']};">
        <a href="{settings.app_base_url.rstrip('/')}/unsubscribe?token={unsubscribe_token}" style="color:{light_styles['muted_color']};text-decoration:underline;">Unsubscribe</a>
      </p>
    </td>
  </tr>
</table>'''

    # Build dark mode styles
    dark_mode_css = _build_dark_mode_css(dark_styles)

    # Assemble full HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    {dark_mode_css}
  </style>
</head>
<body style="margin:0;padding:0;background-color:{light_styles['body_bg']};" class="mofa-dark-bg">
  <!-- Preheader -->
  <div style="display:none;font-size:1px;color:{light_styles['body_bg']};line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
    {title} — {subtitle if subtitle else 'Your daily briefing'}
  </div>

  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:{light_styles['body_bg']};" class="mofa-dark-bg">
    <tr>
      <td align="center" style="padding: 32px 16px;">
        <table role="presentation" width="100%" maxwidth="600" style="max-width:600px;width:100%;" cellspacing="0" cellpadding="0" border="0">

          <!-- Header -->
          <tr>
            <td style="padding-bottom:20px;border-bottom:1px solid {light_styles['border_color']};">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                  <td style="font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:12px;font-weight:600;letter-spacing:0.18em;text-transform:uppercase;color:{light_styles['accent_color']};">
                    mofa-letter
                  </td>
                  <td align="right" style="font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:12px;color:{light_styles['muted_color']};">
                    {send_date}
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body Sections -->
          {body_sections_html}

          <!-- Closing -->
          {closing_html}

          <!-- Sources -->
          {sources_html}

          <!-- CTA -->
          {cta_html}

          <!-- Footer -->
          {footer_html}

        </table>
      </td>
    </tr>
  </table>
</body>
</html>'''

    return html


def _build_dark_mode_css(dark_styles: Dict[str, str]) -> str:
    """Build dark mode media query CSS."""
    return f"""
    @media (prefers-color-scheme: dark) {{
      .mofa-dark-bg {{ background-color: {dark_styles['body_bg']} !important; }}
      .mofa-dark-text {{ color: {dark_styles['body_text']} !important; }}
      .mofa-dark-muted {{ color: {dark_styles['muted']} !important; }}
      .mofa-dark-accent {{ color: {dark_styles['accent_color']} !important; }}
      .mofa-dark-border {{ border-color: {dark_styles['border_color']} !important; }}
      .mofa-dark-card {{ background-color: {dark_styles['card_bg']} !important; border-color: {dark_styles['card_border']} !important; }}
    }}
"""


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
