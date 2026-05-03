"""
Email-safe component library for mofa-letter.

Each component returns a string of table-based HTML with inline styles.
All styles come from the theme dict to ensure mood-aware rendering.
"""

from typing import Dict, Any


def render_component(
    component_type: str,
    style: str,
    heading: str,
    content: str,
    styles: Dict[str, str],
) -> str:
    """Route to the correct component renderer."""
    renderers = {
        "hero": _render_hero,
        "content_card": _render_content_card,
        "quote": _render_quote,
        "bullet_list": _render_bullet_list,
        "divider": _render_divider,
        "insight_box": _render_insight_box,
        "two_column": _render_two_column,
    }
    renderer = renderers.get(component_type, _render_content_card)
    return renderer(style, heading, content, styles)


# ── Hero ──────────────────────────────────────────────────────

def _render_hero(style: str, heading: str, content: str, styles: Dict[str, str]) -> str:
    accent = styles["accent_color"]
    h1_style = styles["h1"]
    muted_style = styles["muted"]
    pad = styles["section_pad"]
    heading_esc = _escape_html(heading)
    content_esc = _escape_html(content) if content else ""

    if style == "bold":
        subtitle_html = f'<p style="{muted_style};font-size:14px;margin-top:8px;">{content_esc}</p>' if content_esc else ""
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:{pad} 0 16px 0;"><h1 style="{h1_style}">{heading_esc}</h1><table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:12px 0 16px 0;"><tr><td style="width:48px;height:3px;background-color:{accent};font-size:0;line-height:0;">&nbsp;</td></tr></table>{subtitle_html}</td></tr></table>'

    elif style == "centered":
        subtitle_html = f'<p style="{muted_style};font-size:14px;margin-top:8px;text-align:center;">{content_esc}</p>' if content_esc else ""
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:{pad} 0 16px 0;text-align:center;"><h1 style="{h1_style};text-align:center;">{heading_esc}</h1>{subtitle_html}</td></tr></table>'

    else:  # minimal
        subtitle_html = f'<p style="{muted_style};font-size:14px;margin-top:8px;">{content_esc}</p>' if content_esc else ""
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:{pad} 0 8px 0;"><h1 style="{h1_style};font-size:26px;">{heading_esc}</h1>{subtitle_html}</td></tr></table>'


# ── Content Card ──────────────────────────────────────────────

def _render_content_card(style: str, heading: str, content: str, styles: Dict[str, str]) -> str:
    accent = styles["accent_color"]
    card_bg = styles["card_bg"]
    card_border = styles["card_border"]
    pad = styles["card_pad"]
    radius = styles["border_radius"]
    paragraph = styles["paragraph"]
    h3_style = styles["h3"]

    if style == "bordered":
        border_attr = f"border:1px solid {card_border};"
        bg_attr = f"background-color:{card_bg};"
    elif style == "filled":
        border_attr = ""
        bg_attr = f"background-color:{card_bg};"
    else:  # left_accent
        border_attr = f"border-left:3px solid {accent};"
        bg_attr = ""

    heading_html = f'<p style="{h3_style}">{_escape_html(heading)}</p>' if heading else ""
    content_html = _paragraph_block(content, styles)

    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 4px 0;"><tr><td style="padding:{pad};{border_attr}{bg_attr}border-radius:{radius};">{heading_html}{content_html}</td></tr></table>'


# ── Quote ─────────────────────────────────────────────────────

def _render_quote(style: str, heading: str, content: str, styles: Dict[str, str]) -> str:
    accent = styles["accent_color"]
    text_color = styles["body_text"]
    muted_color = styles["muted"]
    card_bg = styles["card_bg"]
    card_border = styles["card_border"]
    pad = styles["section_pad"]
    radius = styles["border_radius"]
    heading_html = f'<p style="{styles["h3"]}">{_escape_html(heading)}</p>' if heading else ""
    content_esc = _escape_html(content)

    if style == "elegant":
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:20px 24px;background-color:{card_bg};border-radius:{radius};border:1px solid {card_border};"><p style="font-family:Georgia,serif;font-size:18px;font-style:italic;line-height:1.8;color:{text_color};margin:0;">&ldquo;{content_esc}&rdquo;</p></td></tr></table></td></tr></table>'

    elif style == "modern":
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding-left:16px;border-left:4px solid {accent};"><p style="font-family:{styles["header_font"]};font-size:16px;font-weight:500;line-height:1.7;color:{text_color};margin:0;">{content_esc}</p></td></tr></table></td></tr></table>'

    else:  # minimal_line
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding-left:14px;border-left:2px solid {styles["border_color"]};"><p style="font-family:Georgia,serif;font-size:15px;font-style:italic;line-height:1.7;color:{muted_color};margin:0;">{content_esc}</p></td></tr></table></td></tr></table>'


# ── Bullet List ───────────────────────────────────────────────

def _render_bullet_list(style: str, heading: str, content: str, styles: Dict[str, str]) -> str:
    pad = styles["section_pad"]
    text_color = styles["body_text"]
    accent_color = styles["accent_color"]
    body_font = styles["body_font"]
    heading_html = f'<p style="{styles["h3"]}">{_escape_html(heading)}</p>' if heading else ""
    items = [line.strip() for line in content.split('\n') if line.strip()]

    if style == "numbered":
        prefix = lambda i: f"{i+1}."
    elif style == "checkmarks":
        prefix = lambda i: "&#10003;"
    elif style == "arrows":
        prefix = lambda i: "&rarr;"
    else:  # dots
        prefix = lambda i: "&bull;"

    rows = ""
    for i, item in enumerate(items):
        pfx = prefix(i)
        clean_item = item.lstrip("•-→✓1234567890. ").strip()
        rows += f'<tr><td style="padding:0 10px 10px 0;vertical-align:top;font-size:15px;color:{accent_color};font-weight:600;line-height:1.6;">{pfx}</td><td style="padding:0 0 10px 0;font-family:{body_font};font-size:15px;line-height:1.6;color:{text_color};">{_escape_html(clean_item)}</td></tr>'

    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">{rows}</table></td></tr></table>'


# ── Divider ───────────────────────────────────────────────────

def _render_divider(style: str, heading: str, content: str, styles: Dict[str, str]) -> str:
    pad = styles["section_pad"]
    border_color = styles["border_color"]
    accent_color = styles["accent_color"]

    if style == "spacing":
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:{pad} 0;">&nbsp;</td></tr></table>'

    elif style == "decorative":
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:20px 0;text-align:center;"><table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:0 auto;"><tr><td style="width:40px;height:1px;background-color:{border_color};font-size:0;">&nbsp;</td><td style="width:8px;height:8px;background-color:{accent_color};border-radius:50%;font-size:0;margin:0 12px;">&nbsp;</td><td style="width:40px;height:1px;background-color:{border_color};font-size:0;">&nbsp;</td></tr></table></td></tr></table>'

    else:  # line
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:12px 0;border-top:1px solid {border_color};">&nbsp;</td></tr></table>'


# ── Insight Box ───────────────────────────────────────────────

def _render_insight_box(style: str, heading: str, content: str, styles: Dict[str, str]) -> str:
    label_map = {"tip": "Tip", "warning": "Note", "fact": "Did You Know?"}
    label = label_map.get(style, "Insight")
    bg_color_key = f"insight_{style}"
    bg = styles.get(bg_color_key, styles["card_bg"])
    accent = styles["accent_color"]
    pad = styles["card_pad"]
    radius = styles["border_radius"]
    paragraph = styles["paragraph"]

    heading_html = f'<p style="{styles["h3"]}">{_escape_html(heading)}</p>' if heading else f'<p style="font-family:{styles["body_font"]};font-size:11px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:{accent};margin:0 0 8px 0;">{label}</p>'
    content_html = _paragraph_block(content, styles)

    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad};background-color:{bg};border-left:3px solid {accent};border-radius:{radius};">{heading_html}{content_html}</td></tr></table>'


# ── Two Column ────────────────────────────────────────────────

def _render_two_column(style: str, heading: str, content: str, styles: Dict[str, str]) -> str:
    parts = content.split("---", 1)
    if len(parts) < 2:
        return _render_content_card("bordered", heading, content, styles)

    left_text = parts[0].strip()
    right_text = parts[1].strip()

    if style == "left_heavy":
        left_w, right_w = "62%", "38%"
    elif style == "right_heavy":
        left_w, right_w = "38%", "62%"
    else:
        left_w, right_w = "50%", "50%"

    card_bg = styles["card_bg"]
    card_border = styles["card_border"]
    radius = styles["border_radius"]
    paragraph = styles["paragraph"]
    pad = styles["section_pad"]
    heading_html = f'<p style="{styles["h3"]}">{_escape_html(heading)}</p>' if heading else ""

    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td width="{left_w}" valign="top" style="padding-right:12px;"><div style="padding:16px;background-color:{card_bg};border:1px solid {card_border};border-radius:{radius};"><p style="{paragraph};margin:0;">{_escape_html(left_text)}</p></div></td><td width="{right_w}" valign="top" style="padding-left:12px;"><div style="padding:16px;background-color:{card_bg};border:1px solid {card_border};border-radius:{radius};"><p style="{paragraph};margin:0;">{_escape_html(right_text)}</p></div></td></tr></table></td></tr></table>'


# ── Shared Helpers ────────────────────────────────────────────

def _paragraph_block(content: str, styles: Dict[str, str]) -> str:
    if not content or not content.strip():
        return ""
    paragraphs = content.split('\n\n')
    html = ""
    paragraph_style = styles["paragraph"]
    for para in paragraphs:
        para = para.strip()
        if para:
            html += f'<p style="{paragraph_style}">{_escape_html(para)}</p>'
    return html


def _escape_html(text: str) -> str:
    """Escape HTML entities for safe email rendering."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
