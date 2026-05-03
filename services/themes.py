"""
Theme system for mofa-letter newsletters.

Each theme defines a complete visual identity: colors, typography, spacing.
Themes are email-client-safe: no CSS variables, no external fonts.
"""

from typing import Dict, Any


# ── Theme Definitions ─────────────────────────────────────────

THEMES: Dict[str, Dict[str, Any]] = {
    "professional": {
        "name": "Professional",
        "description": "Trust, authority, clarity — for business, finance, consulting",
        "colors": {
            "bg": "#f8fafc",
            "bg_dark": "#0f172a",
            "text": "#1e293b",
            "text_dark": "#f1f5f9",
            "muted": "#64748b",
            "muted_dark": "#94a3b8",
            "accent": "#d97706",       # Gold
            "accent_secondary": "#b45309",
            "border": "#e2e8f0",
            "border_dark": "#334155",
            "card_bg": "#ffffff",
            "card_bg_dark": "#1e293b",
            "card_border": "#cbd5e1",
            "card_border_dark": "#475569",
            "insight_tip": "#dbeafe",      # Light blue
            "insight_tip_dark": "#1e3a5f",
            "insight_warning": "#fef3c7",  # Light amber
            "insight_warning_dark": "#78350f",
            "insight_fact": "#dcfce7",     # Light green
            "insight_fact_dark": "#14532d",
        },
        "fonts": {
            "header": "Georgia, 'Times New Roman', serif",
            "body": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        },
        "spacing": {
            "section_pad": "36px",
            "card_pad": "24px",
            "border_radius": "6px",
            "line_height": "1.7",
        },
        "mood_keywords": ["business", "finance", "consulting", "corporate", "serious", "investment", "market", "professional"],
    },

    "creative": {
        "name": "Creative",
        "description": "Energy, warmth, inspiration — for design, arts, innovation",
        "colors": {
            "bg": "#fff7ed",           # Warm cream
            "bg_dark": "#1c1917",      # Warm dark
            "text": "#292524",
            "text_dark": "#fafaf9",
            "muted": "#78716c",
            "muted_dark": "#a8a29e",
            "accent": "#0f766e",       # Deep teal
            "accent_secondary": "#f97316",  # Coral
            "border": "#e7e5e4",
            "border_dark": "#44403c",
            "card_bg": "#ffffff",
            "card_bg_dark": "#292524",
            "card_border": "#d6d3d1",
            "card_border_dark": "#57534e",
            "insight_tip": "#ccfbf1",
            "insight_tip_dark": "#134e4a",
            "insight_warning": "#ffedd5",
            "insight_warning_dark": "#7c2d12",
            "insight_fact": "#dcfce7",
            "insight_fact_dark": "#14532d",
        },
        "fonts": {
            "header": "Georgia, 'Times New Roman', serif",
            "body": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        },
        "spacing": {
            "section_pad": "40px",
            "card_pad": "28px",
            "border_radius": "10px",
            "line_height": "1.75",
        },
        "mood_keywords": ["creative", "design", "art", "innovation", "startup", "culture", "aesthetic", "inspiring"],
    },

    "playful": {
        "name": "Playful",
        "description": "Fun, youth, excitement — for gaming, hobbies, casual content",
        "colors": {
            "bg": "#ffffff",
            "bg_dark": "#18181b",      # Zinc dark
            "text": "#27272a",
            "text_dark": "#f4f4f5",
            "muted": "#71717a",
            "muted_dark": "#a1a1aa",
            "accent": "#7c3aed",       # Violet
            "accent_secondary": "#84cc16",  # Lime
            "border": "#e4e4e7",
            "border_dark": "#3f3f46",
            "card_bg": "#fafafa",
            "card_bg_dark": "#27272a",
            "card_border": "#d4d4d8",
            "card_border_dark": "#52525b",
            "insight_tip": "#ede9fe",
            "insight_tip_dark": "#4c1d95",
            "insight_warning": "#ecfccb",
            "insight_warning_dark": "#3f6212",
            "insight_fact": "#d1fae5",
            "insight_fact_dark": "#065f46",
        },
        "fonts": {
            "header": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            "body": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        },
        "spacing": {
            "section_pad": "32px",
            "card_pad": "24px",
            "border_radius": "16px",
            "line_height": "1.6",
        },
        "mood_keywords": ["fun", "gaming", "hobby", "casual", "entertainment", "pop culture", "meme", "playful", "lighthearted"],
    },

    "academic": {
        "name": "Academic",
        "description": "Wisdom, tradition, depth — for research, history, literature, philosophy",
        "colors": {
            "bg": "#faf6f1",           # Parchment
            "bg_dark": "#1a1612",      # Dark parchment
            "text": "#29221c",         # Dark brown
            "text_dark": "#f5f0e8",
            "muted": "#78716c",
            "muted_dark": "#a8a29e",
            "accent": "#b45309",       # Brass
            "accent_secondary": "#1e3a5f",  # Oxford Blue
            "border": "#e7e5e4",
            "border_dark": "#44403c",
            "card_bg": "#ffffff",
            "card_bg_dark": "#29221c",
            "card_border": "#d6d3d1",
            "card_border_dark": "#57534e",
            "insight_tip": "#e0e7ff",
            "insight_tip_dark": "#312e81",
            "insight_warning": "#fef9c3",
            "insight_warning_dark": "#713f12",
            "insight_fact": "#dcfce7",
            "insight_fact_dark": "#14532d",
        },
        "fonts": {
            "header": "Georgia, 'Times New Roman', serif",
            "body": "Georgia, 'Times New Roman', serif",
        },
        "spacing": {
            "section_pad": "40px",
            "card_pad": "28px",
            "border_radius": "4px",
            "line_height": "1.8",
        },
        "mood_keywords": ["academic", "philosophy", "history", "literature", "research", "science", "scholarly", "intellectual", "stoic"],
    },

    "minimal": {
        "name": "Minimal",
        "description": "Clean, modern, focus — for tech, productivity, modern living",
        "colors": {
            "bg": "#ffffff",
            "bg_dark": "#111827",
            "text": "#111827",
            "text_dark": "#f9fafb",
            "muted": "#6b7280",
            "muted_dark": "#9ca3af",
            "accent": "#111827",
            "accent_secondary": "#6b7280",
            "border": "#e5e7eb",
            "border_dark": "#374151",
            "card_bg": "#f9fafb",
            "card_bg_dark": "#1f2937",
            "card_border": "#e5e7eb",
            "card_border_dark": "#374151",
            "insight_tip": "#f3f4f6",
            "insight_tip_dark": "#374151",
            "insight_warning": "#fef3c7",
            "insight_warning_dark": "#78350f",
            "insight_fact": "#f0fdf4",
            "insight_fact_dark": "#14532d",
        },
        "fonts": {
            "header": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            "body": "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        },
        "spacing": {
            "section_pad": "48px",
            "card_pad": "32px",
            "border_radius": "0px",
            "line_height": "1.65",
        },
        "mood_keywords": ["minimal", "tech", "productivity", "modern", "clean", "simple", "focus", "startup", "developer"],
    },
}


# ── Helpers ───────────────────────────────────────────────────

def get_theme(mood: str) -> Dict[str, Any]:
    """Get theme by mood keyword. Falls back to minimal if no match."""
    mood_lower = mood.lower().strip()
    for theme_key, theme in THEMES.items():
        if mood_lower == theme_key:
            return theme
        if mood_lower in theme.get("mood_keywords", []):
            return theme
    return THEMES["minimal"]  # Default fallback


def resolve_color(theme: Dict[str, Any], color_key: str, is_dark: bool = False) -> str:
    """Resolve a color key, preferring dark variant if requested."""
    colors = theme["colors"]
    dark_key = f"{color_key}_dark"
    if is_dark and dark_key in colors:
        return colors[dark_key]
    return colors.get(color_key, "#000000")


def build_inline_styles(theme: Dict[str, Any], is_dark: bool = False) -> Dict[str, str]:
    """Build a flat dict of inline style strings for common elements."""
    c = lambda k: resolve_color(theme, k, is_dark)
    s = theme["spacing"]
    f = theme["fonts"]

    return {
        "body_bg": c("bg"),
        "body_text": c("text"),
        "body_font": f"font-family:{f['body']};font-size:15px;line-height:{s['line_height']};color:{c('text')};",
        "header_font": f"font-family:{f['header']};",
        "h1": f"font-family:{f['header']};font-size:28px;font-weight:400;color:{c('text')};letter-spacing:-0.01em;margin:0;",
        "h2": f"font-family:{f['header']};font-size:20px;font-weight:500;color:{c('text')};margin:0 0 12px 0;",
        "h3": f"font-family:{f['header']};font-size:16px;font-weight:600;color:{c('accent')};margin:0 0 10px 0;text-transform:uppercase;letter-spacing:0.08em;",
        "paragraph": f"font-family:{f['body']};font-size:15px;line-height:{s['line_height']};color:{c('text')};margin:0 0 16px 0;",
        "muted": f"font-family:{f['body']};font-size:13px;color:{c('muted')};margin:0;",
        "accent_text": f"color:{c('accent')};",
        "section_pad": s["section_pad"],
        "card_pad": s["card_pad"],
        "border_radius": s["border_radius"],
        "card_bg": c("card_bg"),
        "card_border": c("card_border"),
        "border_color": c("border"),
        "accent_color": c("accent"),
    }
