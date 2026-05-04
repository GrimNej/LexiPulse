"""
Email-safe component library for mofa-letter.

Each component returns a string of table-based HTML with inline styles.
All styles come from the theme dict to ensure mood-aware rendering.
"""

import re
from typing import Dict, Any


def render_component(
    component_type: str,
    style: str,
    heading: str,
    content: str,
    styles: Dict[str, str],
    source_url: str = "",
) -> str:
    """Route to the correct component renderer."""
    renderers = {
        "hero": _render_hero,
        "content_card": _render_content_card,
        "quote": _render_quote,
        "bullet_list": _render_bullet_list,
        "divider": _render_divider,
        "insight_box": _render_insight_box,
        "highlight_stat": _render_highlight_stat,
    }
    renderer = renderers.get(component_type, _render_content_card)
    return renderer(style, heading, content, styles, source_url)


# ── Hero ──────────────────────────────────────────────────────

def _render_hero(style: str, heading: str, content: str, styles: Dict[str, str], source_url: str = "") -> str:
    accent = styles["accent_color"]
    h1_style = styles["h1"]
    muted_color = styles["muted_color"]
    body_font = styles["body_font"]
    pad = styles["section_pad"]
    heading_esc = _escape_html(heading)
    content_esc = _escape_html(content) if content else ""

    if style == "bold":
        subtitle_html = f'<p style="{body_font};font-size:14px;color:{muted_color};margin-top:8px;">{content_esc}</p>' if content_esc else ""
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:{pad} 0 16px 0;"><h1 style="{h1_style}">{heading_esc}</h1><table role="presentation" cellspacing="0" cellpadding="0" border="0" style="margin:12px 0 16px 0;"><tr><td style="width:48px;height:3px;background-color:{accent};font-size:0;line-height:0;">&nbsp;</td></tr></table>{subtitle_html}</td></tr></table>'

    elif style == "centered":
        subtitle_html = f'<p style="{body_font};font-size:14px;color:{muted_color};margin-top:8px;text-align:center;">{content_esc}</p>' if content_esc else ""
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:{pad} 0 16px 0;text-align:center;"><h1 style="{h1_style};text-align:center;">{heading_esc}</h1>{subtitle_html}</td></tr></table>'

    else:  # minimal
        subtitle_html = f'<p style="{body_font};font-size:14px;color:{muted_color};margin-top:8px;">{content_esc}</p>' if content_esc else ""
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:{pad} 0 8px 0;"><h1 style="{h1_style};font-size:26px;">{heading_esc}</h1>{subtitle_html}</td></tr></table>'


# ── Content Card ──────────────────────────────────────────────

def _render_content_card(style: str, heading: str, content: str, styles: Dict[str, str], source_url: str = "") -> str:
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
    source_html = _source_link_html(source_url, styles)

    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:0 0 4px 0;"><tr><td style="padding:{pad};{border_attr}{bg_attr}border-radius:{radius};">{heading_html}{content_html}{source_html}</td></tr></table>'


# ── Quote ─────────────────────────────────────────────────────

def _render_quote(style: str, heading: str, content: str, styles: Dict[str, str], source_url: str = "") -> str:
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
        source_html = _source_link_html(source_url, styles)
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding:20px 24px;background-color:{card_bg};border-radius:{radius};border:1px solid {card_border};"><p style="font-family:Georgia,serif;font-size:18px;font-style:italic;line-height:1.8;color:{text_color};margin:0;">&ldquo;{content_esc}&rdquo;</p>{source_html}</td></tr></table></td></tr></table>'

    elif style == "modern":
        source_html = _source_link_html(source_url, styles)
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding-left:16px;border-left:4px solid {accent};"><p style="font-family:{styles["header_font"]};font-size:16px;font-weight:500;line-height:1.7;color:{text_color};margin:0;">{content_esc}</p>{source_html}</td></tr></table></td></tr></table>'

    else:  # minimal_line
        source_html = _source_link_html(source_url, styles)
        return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"><tr><td style="padding-left:14px;border-left:2px solid {styles["border_color"]};"><p style="font-family:Georgia,serif;font-size:15px;font-style:italic;line-height:1.7;color:{muted_color};margin:0;">{content_esc}</p>{source_html}</td></tr></table></td></tr></table>'


# ── Bullet List ───────────────────────────────────────────────

def _render_bullet_list(style: str, heading: str, content: str, styles: Dict[str, str], source_url: str = "") -> str:
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
        # Strip common bullet prefixes but preserve numbers that are part of content
        clean_item = re.sub(r'^[\s•\-\→✓]+\s*', '', item).strip()
        clean_item = re.sub(r'^\d+\.\s+', '', clean_item)
        rows += f'<tr><td style="padding:0 10px 10px 0;vertical-align:top;font-size:15px;color:{accent_color};font-weight:600;line-height:1.6;">{pfx}</td><td style="padding:0 0 10px 0;font-family:{body_font};font-size:15px;line-height:1.6;color:{text_color};">{_escape_html(clean_item)}</td></tr>'

    source_html = _source_link_html(source_url, styles)
    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad} 0;">{heading_html}<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">{rows}</table>{source_html}</td></tr></table>'


# ── Divider ───────────────────────────────────────────────────

def _render_divider(style: str, heading: str, content: str, styles: Dict[str, str], source_url: str = "") -> str:
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

def _render_insight_box(style: str, heading: str, content: str, styles: Dict[str, str], source_url: str = "") -> str:
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
    source_html = _source_link_html(source_url, styles)

    return f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;"><tr><td style="padding:{pad};background-color:{bg};border-left:3px solid {accent};border-radius:{radius};">{heading_html}{content_html}{source_html}</td></tr></table>'


# ── Highlight Stat ────────────────────────────────────────────

def _render_highlight_stat(style: str, heading: str, content: str, styles: Dict[str, str], source_url: str = "") -> str:
    """Big bold number or fact callout — handles single or multiple stats."""
    accent = styles["accent_color"]
    text_color = styles["body_text"]
    card_bg = styles["card_bg"]
    card_border = styles["card_border"]
    pad = styles["card_pad"]
    radius = styles["border_radius"]
    header_font = styles["header_font"]
    paragraph = styles["paragraph"]
    body_font = styles["body_font"]

    heading_html = f'<p style="{styles["h3"]}">{_escape_html(heading)}</p>' if heading else ""
    source_html = _source_link_html(source_url, styles)

    # Split content into stat blocks (separated by double newlines)
    # Each block is "stat value\nstat description"
    stat_blocks = [b.strip() for b in content.split('\n\n') if b.strip()]
    
    if not stat_blocks:
        stat_blocks = [content.strip()]

    stat_rows = ""
    for block in stat_blocks:
        lines = block.split('\n', 1)
        stat_val = lines[0].strip()
        stat_desc = lines[1].strip() if len(lines) > 1 else ""
        
        if style == "big_number":
            val_style = f"font-family:{header_font};font-size:36px;font-weight:700;color:{accent};letter-spacing:-0.02em;line-height:1.1;margin:0;"
        elif style == "percentage":
            val_style = f"font-family:{header_font};font-size:36px;font-weight:700;color:{accent};letter-spacing:-0.02em;line-height:1.1;margin:0;"
        else:  # milestone
            val_style = f"font-family:{header_font};font-size:20px;font-weight:600;color:{text_color};line-height:1.3;margin:0;"
        
        desc_html = f'<p style="{body_font};font-size:13px;color:{styles["muted_color"]};margin:4px 0 0 0;">{_escape_html(stat_desc)}</p>' if stat_desc else ""
        
        stat_rows += f'''<tr>
    <td style="padding:16px 0;border-bottom:1px solid {card_border};">
      <p style="{val_style}">{_escape_html(stat_val)}</p>
      {desc_html}
    </td>
  </tr>'''
    
    # Remove border from last row
    if stat_rows:
        stat_rows = stat_rows.replace(f'border-bottom:1px solid {card_border};', '', stat_rows.count('border-bottom:1px solid') - 1)

    return f'''<table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin:8px 0;">
  <tr>
    <td style="padding:{pad};background-color:{card_bg};border:1px solid {card_border};border-radius:{radius};text-align:center;">
      {heading_html}
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        {stat_rows}
      </table>
      {source_html}
    </td>
  </tr>
</table>'''


def _source_link_html(source_url: str, styles: Dict[str, str]) -> str:
    """Render a small source link below content."""
    if not source_url:
        return ""
    muted = styles["muted"]
    accent = styles["accent_color"]
    return f'<p style="margin:12px 0 0 0;font-family:system-ui,-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif;font-size:12px;text-align:right;"><a href="{_escape_html(source_url)}" style="color:{accent};text-decoration:none;">Source &rarr;</a></p>'


# ── Shared Helpers ────────────────────────────────────────────

def _paragraph_block(content: str, styles: Dict[str, str]) -> str:
    if not content or not content.strip():
        return ""
    # Split on double newlines for paragraph breaks
    # Single newlines are treated as part of the same paragraph for email client safety
    blocks = content.split('\n\n')
    html = ""
    paragraph_style = styles["paragraph"]
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        html += f'<p style="{paragraph_style}">{_escape_html(block)}</p>'
    return html


def _escape_html(text: str) -> str:
    """Escape HTML entities for safe email rendering."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
