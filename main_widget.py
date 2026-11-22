from aqt import mw, gui_hooks
from aqt.theme import theme_manager
from aqt.utils import tooltip
from .config import manager
from .tea_data import get_tea_by_id
from .settings import SenchadoSettings
from .timer import tea_timer, TimerState
from . import bento_integration
import html
import json
import os
import base64

# Global caches
cached_widget_html = None
_tea_image_b64_cache = {}
_live_refresh_timer = None

# Official Lucide icon inner paths (24x24, stroke-based)
_LUCIDE_PATHS = {
    "coffee": (
        '<path d="M10 2v2"/><path d="M14 2v2"/>'
        '<path d="M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1"/>'
        '<path d="M6 2v2"/>'
    ),
    "settings": (
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>'
        '<circle cx="12" cy="12" r="3"/>'
    ),
    "flame": '<path d="M12 3q1 4 4 6.5t3 5.5a1 1 0 0 1-14 0 5 5 0 0 1 1-3 1 1 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4"/>',
    "snowflake": (
        '<path d="m10 20-1.25-2.5L6 18"/><path d="M10 4 8.75 6.5 6 6"/>'
        '<path d="m14 20 1.25-2.5L18 18"/><path d="m14 4 1.25 2.5L18 6"/>'
        '<path d="m17 21-3-6h-4"/><path d="m17 3-3 6 1.5 3"/>'
        '<path d="M2 12h6.5L10 9"/><path d="m20 10-1.5 2 1.5 2"/>'
        '<path d="M22 12h-6.5L14 15"/><path d="m4 10 1.5 2L4 14"/>'
        '<path d="m7 21 3-6-1.5-3"/><path d="m7 3 3 6h4"/>'
    ),
    "thermometer": '<path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/>',
    "timer": (
        '<line x1="10" x2="14" y1="2" y2="2"/>'
        '<line x1="12" x2="15" y1="14" y2="11"/>'
        '<circle cx="12" cy="14" r="8"/>'
    ),
    "repeat": (
        '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/>'
        '<path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>'
    ),
    "play": '<polygon points="6 3 20 12 6 21 6 3"/>',
    "pause": (
        '<rect x="14" y="4" width="4" height="16" rx="1"/>'
        '<rect x="6" y="4" width="4" height="16" rx="1"/>'
    ),
    "rotate-ccw": (
        '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
        '<path d="M3 3v5h5"/>'
    ),
    "check": '<path d="M20 6 9 17l-5-5"/>',
}

_STATE_LABELS = {
    "IDLE": "Ready",
    "PREPARATION": "Prep",
    "BREWING": "Brew",
    "PAUSED": "Paused",
    "DONE": "Done",
}


def _lucide_svg(name: str, size: int = 14) -> str:
    inner = _LUCIDE_PATHS.get(name, "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{inner}</svg>'
    )


def _temp_icon_name(temp_c: int) -> str:
    if temp_c <= 39:
        return "snowflake"
    if temp_c >= 110:
        return "flame"
    return "thermometer"

def get_zen_palette(is_dark=None):
    """
    Returns the Zen/Natural color palette matching settings.py.
    """
    if is_dark is None:
        is_dark = bento_integration.effective_is_dark()
    if is_dark:
        return {
            "bg": "#1A1C19",       # Background
            "card_bg": "#262925",  # Card
            "fg": "#E1E6DF",       # Foreground / Text
            "subtle": "#8F9E91",   # Subtext
            "border": "#3A3F39",   # Border
            "accent": "#3F6D49",   # Accent
            "accent_sec": "#9FBCA1" # Secondary Accent (Hover/Light)
        }
    else:
        return {
            "bg": "#FAFAF5",       # Background
            "card_bg": "#FFFFFF",  # Card
            "fg": "#2C3E2D",       # Foreground / Text
            "subtle": "#5D6F5E",   # Subtext
            "border": "#D8DED0",   # Border
            "accent": "#3F6D49",   # Accent
            "accent_sec": "#6B8E6D" # Secondary Accent
        }

def get_tea_image_b64(tea_id):
    """Encodes the tea image as base64 for embedding in HTML (cached)."""
    if tea_id in _tea_image_b64_cache:
        return _tea_image_b64_cache[tea_id]
    addon_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(addon_dir, "tea_gallery", f"{tea_id}.png")
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
            _tea_image_b64_cache[tea_id] = encoded
            return encoded
    _tea_image_b64_cache[tea_id] = None
    return None

def generate_widget_html(progress=None, tea_config=None, ui_settings=None, is_dark=None):
    """Builds the Tea Room widget's HTML. Used both by the real deck-browser
    render (all args default to live manager/theme state) and by the
    settings-dialog live preview (which passes in-progress/sample values),
    so the two can never visually drift apart.
    """
    if progress is None:
        progress = manager.get_progress()
    if tea_config is None:
        tea_config = manager.get_current_tea()
    if ui_settings is None:
        ui_settings = manager.get_ui_settings()
    if is_dark is None:
        is_dark = bento_integration.effective_is_dark()

    config = tea_config
    tea = get_tea_by_id(config.get("flavor_id", "sencha"))
    colors = get_zen_palette(is_dark)
    custom_card_color = ui_settings.get("widget_card_color_dark" if is_dark else "widget_card_color_light")
    if custom_card_color:
        colors["card_bg"] = custom_card_color

    widget_style = str(ui_settings.get("widget_style", "zen") or "zen").lower()
    if widget_style not in ("zen", "compact", "minimal", "classic"):
        widget_style = "zen"

    show_xp = bool(ui_settings.get("widget_show_xp", True))
    show_task = bool(ui_settings.get("widget_show_task", True))
    show_brew = bool(ui_settings.get("widget_show_brew_details", True))
    tea_accent = bool(ui_settings.get("widget_tea_accent", False))

    opacity = float(ui_settings.get("widget_opacity", 100)) / 100.0
    glass_strength = float(ui_settings.get("widget_glass_strength", 0) or 0)
    glass = bool(ui_settings.get("widget_glass", False) or glass_strength > 0)

    level = max(1, int(progress.get("level", 1) or 1))
    xp = max(0, int(progress.get("xp", 0) or 0))
    next_level_xp = level * 100
    xp_percent = min(100.0, max(0.0, (xp / next_level_xp) * 100.0)) if next_level_xp > 0 else 0.0

    default_dim = 300

    def hex_to_rgb(hex_color):
        raw = str(hex_color or "").strip()
        if raw.startswith("rgb"):
            inner = raw[raw.find("(") + 1:raw.rfind(")")].split(",")
            if len(inner) >= 3:
                try:
                    return (int(float(inner[0].strip())), int(float(inner[1].strip())), int(float(inner[2].strip())))
                except Exception:
                    pass
        raw = raw.lstrip('#')
        if len(raw) == 3:
            raw = "".join(ch * 2 for ch in raw)
        elif len(raw) == 8:
            raw = raw[2:]
        if len(raw) == 6:
            try:
                return tuple(int(raw[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                pass
        return (38, 41, 37) if is_dark else (255, 255, 255)

    r, g, b = hex_to_rgb(colors['card_bg'])
    accent_primary = tea.color_start if tea_accent and getattr(tea, "color_start", None) else colors['accent']
    accent_fg = accent_primary if (tea_accent or not is_dark) else colors['accent_sec']
    ar, ag, ab = hex_to_rgb(accent_primary)

    if glass and glass_strength > 0:
        border_color = "rgba(255, 255, 255, 0.16)" if is_dark else "rgba(0, 0, 0, 0.08)"
        backdrop_filter = f"backdrop-filter: blur({glass_strength}px); -webkit-backdrop-filter: blur({glass_strength}px);"
    else:
        border_color = colors['border']
        backdrop_filter = ""

    bg_color = f"rgba({r}, {g}, {b}, {opacity})"
    chip_bg = "rgba(255, 255, 255, 0.06)" if is_dark else "rgba(44, 62, 45, 0.055)"
    accent_soft = f"rgba({ar}, {ag}, {ab}, {0.20 if is_dark else 0.12})"
    track_bg = "rgba(255, 255, 255, 0.10)" if is_dark else "rgba(44, 62, 45, 0.10)"
    card_shadow = "0 10px 30px rgba(0,0,0,0.28)" if is_dark else "0 8px 28px rgba(34, 48, 36, 0.07)"

    temp_c = int(config.get("temperature", 80) or 80)
    prep_m = max(1, int(round(float(config.get("prep_time", 1500)) / 60)))
    brew_m = max(1, int(round(float(config.get("brew_time", 300)) / 60)))
    cycles_n = max(1, int(config.get("cycles", 1) or 1))
    task_text = html.escape(str(config.get("task_name", "Study Session") or "Study Session"))
    tea_name = html.escape(tea.name)

    coffee_svg = _lucide_svg("coffee", 14)
    gear_svg = _lucide_svg("settings", 15)
    temp_svg = _lucide_svg(_temp_icon_name(temp_c), 11)
    timer_svg = _lucide_svg("timer", 11)
    repeat_svg = _lucide_svg("repeat", 11)
    play_svg = _lucide_svg("play", 13)
    pause_svg = _lucide_svg("pause", 13)
    reset_svg = _lucide_svg("rotate-ccw", 13)
    complete_svg = _lucide_svg("check", 13)

    t_state = getattr(tea_timer, "state", TimerState.IDLE)
    t_state_name = t_state.name if hasattr(t_state, "name") else "IDLE"
    t_running = t_state in (TimerState.PREPARATION, TimerState.BREWING)
    if t_state == TimerState.IDLE:
        t_secs = int(config.get("prep_time", 1500) or 1500)
    elif t_state == TimerState.DONE:
        t_secs = 0
    else:
        t_secs = max(0, int(getattr(tea_timer, "current_time", 0) or 0))
    t_time_str = f"{t_secs // 60:02d}:{t_secs % 60:02d}"
    t_state_label = _STATE_LABELS.get(t_state_name, t_state_name.title())
    t_play_icon = pause_svg if t_running else play_svg
    t_play_title = "Pause timer" if t_running else ("Resume timer" if t_state == TimerState.PAUSED else "Start timer")

    tea_b64 = get_tea_image_b64(tea.id)
    tea_img_html = (
        f'<img class="s-tea-img" src="data:image/png;base64,{tea_b64}" alt="{tea_name}">'
        if tea_b64
        else f'<span class="s-tea-fallback" aria-hidden="true">{_lucide_svg("coffee", 24)}</span>'
    )

    style_block = f"""
    <style>
    .senchado-container {{
        width: 100%;
        display: flex;
        justify-content: center;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    .senchado-widget {{
        --s-bg: {bg_color};
        --s-fg: {colors['fg']};
        --s-sub: {colors['subtle']};
        --s-border: {border_color};
        --s-accent: {accent_primary};
        --s-accent-fg: {accent_fg};
        --s-accent-soft: {accent_soft};
        --s-chip-bg: {chip_bg};
        --s-track: {track_bg};
        container-type: inline-size;
        background: var(--s-bg);
        color: var(--s-fg);
        padding: 13px 14px;
        margin: 20px auto;
        border-radius: 24px;
        width: {default_dim}px;
        height: {default_dim}px;
        box-sizing: border-box;
        border: 1px solid var(--s-border);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 7px;
        position: relative;
        overflow: hidden;
        {backdrop_filter}
        box-shadow: {card_shadow};
        text-align: left;
    }}

    .senchado-widget * {{
        box-sizing: border-box;
    }}

    .senchado-gear {{
        appearance: none;
        background: var(--s-chip-bg);
        border: none !important;
        color: var(--s-sub);
        cursor: pointer;
        transition: color 0.18s ease, background 0.18s ease, transform 0.22s ease;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px !important;
        height: 28px !important;
        min-width: 28px !important;
        max-width: 28px !important;
        min-height: 28px !important;
        max-height: 28px !important;
        padding: 0 !important;
        margin: 0 !important;
        line-height: 1 !important;
        border-radius: 999px !important;
        flex: 0 0 28px;
        font: inherit;
        box-shadow: none !important;
    }}

    .senchado-gear:hover {{
        color: var(--s-accent);
        background: var(--s-accent-soft);
        transform: rotate(28deg);
    }}

    .senchado-gear:focus-visible {{
        outline: 2px solid var(--s-accent);
        outline-offset: 2px;
    }}

    .s-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        width: 100%;
    }}

    .s-brand {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 10px;
        border-radius: 999px;
        background: var(--s-chip-bg);
        font-size: 10.5px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--s-sub);
        min-width: 0;
    }}

    .s-brand svg {{
        color: var(--s-accent-fg);
        flex: 0 0 auto;
    }}

    .s-header-right {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        flex: 0 0 auto;
    }}

    .s-lvl-pill {{
        display: inline-flex;
        align-items: center;
        padding: 5px 10px;
        border-radius: 999px;
        background: var(--s-accent-soft);
        border: none;
        color: var(--s-accent-fg);
        font-size: 11px;
        font-weight: 700;
        line-height: 1;
        font-variant-numeric: tabular-nums;
    }}

    .s-hero {{
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        padding: 8px 10px;
        border-radius: 15px;
        background: var(--s-chip-bg);
    }}

    .s-tea-emblem {{
        width: 42px;
        height: 42px;
        border-radius: 12px;
        background: var(--s-accent-soft);
        border: none;
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 42px;
    }}

    .s-tea-img {{
        width: 30px;
        height: 30px;
        object-fit: contain;
        display: block;
    }}

    .s-tea-fallback {{
        color: var(--s-accent);
        display: inline-flex;
    }}

    .s-hero-copy {{
        display: flex;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
        flex: 1;
    }}

    .s-tea-name {{
        margin: 0;
        font-size: 19px;
        font-weight: 750;
        letter-spacing: -0.02em;
        line-height: 1.15;
        color: var(--s-fg);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .s-task {{
        margin: 0;
        font-size: 12px;
        font-weight: 500;
        color: var(--s-sub);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .s-xp {{
        display: flex;
        flex-direction: column;
        gap: 5px;
        width: 100%;
        padding: 7px 10px;
        border-radius: 13px;
        background: var(--s-chip-bg);
    }}

    .s-timer-bar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 6px;
        width: 100%;
        padding: 6px 8px 6px 10px;
        border-radius: 14px;
        background: var(--s-chip-bg);
        overflow: hidden;
    }}

    .s-timer-left {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        flex: 1 1 auto;
        min-width: 0;
        overflow: hidden;
        white-space: nowrap;
    }}

    .s-timer-state {{
        display: inline-flex;
        align-items: center;
        padding: 3px 6px;
        border-radius: 999px;
        background: var(--s-accent-soft);
        color: var(--s-accent-fg);
        font-size: 9px;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        line-height: 1;
        flex: 0 0 auto;
    }}

    .s-timer-time {{
        font-size: 14px;
        font-weight: 750;
        color: var(--s-fg);
        font-variant-numeric: tabular-nums;
        line-height: 1;
        flex: 0 0 auto;
        white-space: nowrap;
    }}

    .s-timer-actions {{
        display: inline-flex;
        align-items: center;
        gap: 4px;
        flex: 0 0 auto;
    }}

    .senchado-widget .s-tbtn {{
        appearance: none;
        border: none !important;
        width: 26px !important;
        height: 26px !important;
        min-width: 26px !important;
        max-width: 26px !important;
        min-height: 26px !important;
        max-height: 26px !important;
        padding: 0 !important;
        margin: 0 !important;
        line-height: 1 !important;
        border-radius: 999px !important;
        background: var(--s-bg);
        color: var(--s-sub);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 26px;
        cursor: pointer;
        font: inherit;
        box-shadow: none !important;
        transition: background 0.16s ease, color 0.16s ease, transform 0.14s ease;
    }}

    .senchado-widget .s-tbtn:hover {{
        background: var(--s-accent-soft);
        color: var(--s-accent-fg);
    }}

    .senchado-widget .s-tbtn:active {{
        transform: scale(0.94);
    }}

    .senchado-widget .s-tbtn.is-primary {{
        background: var(--s-accent);
        color: #ffffff;
    }}

    .senchado-widget .s-tbtn.is-primary:hover {{
        opacity: 0.9;
        color: #ffffff;
    }}

    .s-xp-meta {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        font-size: 11px;
        font-weight: 600;
        color: var(--s-sub);
        font-variant-numeric: tabular-nums;
    }}

    .s-xp-track {{
        background: var(--s-track);
        height: 6px;
        width: 100%;
        border-radius: 999px;
        overflow: hidden;
    }}

    .s-xp-fill {{
        height: 100%;
        background: var(--s-accent);
        border-radius: 999px;
        width: {xp_percent:.2f}%;
        transition: width 0.35s ease;
    }}

    .s-metrics {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 7px;
        width: 100%;
    }}

    .s-chip {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        gap: 3px;
        padding: 8px 6px;
        border-radius: 14px;
        background: var(--s-chip-bg);
        border: none;
        min-width: 0;
        overflow: hidden;
    }}

    .s-chip-k {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 3px;
        max-width: 100%;
        font-size: 9px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        color: var(--s-sub);
        white-space: nowrap;
        overflow: hidden;
    }}

    .s-chip-k span {{
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    .s-chip-k svg {{
        color: var(--s-accent-fg);
        flex: 0 0 auto;
    }}

    .s-chip-v {{
        font-size: 13px;
        font-weight: 750;
        color: var(--s-fg);
        font-variant-numeric: tabular-nums;
        max-width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}

    /* Compact preset */
    .senchado-widget.style-compact {{
        padding: 14px;
        gap: 9px;
    }}
    .senchado-widget.style-compact .s-hero {{
        padding: 8px 10px;
    }}
    .senchado-widget.style-compact .s-tea-emblem {{
        width: 42px;
        height: 42px;
        flex: 0 0 42px;
        border-radius: 12px;
    }}
    .senchado-widget.style-compact .s-tea-img {{
        width: 30px;
        height: 30px;
    }}
    .senchado-widget.style-compact .s-tea-name {{
        font-size: 17px;
    }}
    .senchado-widget.style-compact .s-metrics {{
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
    }}
    .senchado-widget.style-compact .s-chip {{
        flex-direction: row;
        align-items: center;
        gap: 5px;
        padding: 6px 10px;
        border-radius: 999px;
        flex: 1 1 auto;
    }}
    .senchado-widget.style-compact .s-chip-v {{
        font-size: 12px;
    }}

    /* Minimal preset */
    .senchado-widget.style-minimal {{
        align-items: center;
        text-align: center;
        justify-content: space-between;
        padding: 16px;
    }}
    .senchado-widget.style-minimal .s-minimal-center {{
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        flex: 1;
        width: 100%;
        padding: 12px;
        border-radius: 18px;
        background: var(--s-chip-bg);
    }}
    .senchado-widget.style-minimal .s-tea-emblem {{
        width: 60px;
        height: 60px;
        flex: 0 0 60px;
        border-radius: 18px;
    }}
    .senchado-widget.style-minimal .s-tea-img {{
        width: 42px;
        height: 42px;
    }}
    .senchado-widget.style-minimal .s-temp-pill {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 5px 11px;
        border-radius: 999px;
        background: var(--s-accent-soft);
        border: none;
        font-size: 12.5px;
        font-weight: 700;
        color: var(--s-accent);
        font-variant-numeric: tabular-nums;
    }}
    .senchado-widget.style-minimal .s-temp-pill svg {{
        color: var(--s-accent);
    }}
    .senchado-widget.style-minimal .s-xp {{
        padding: 6px 10px;
    }}

    /* Classic preset (upgraded with Lucide + borderless containers) */
    .senchado-widget.style-classic {{
        align-items: center;
        text-align: center;
        justify-content: space-between;
        padding: 16px;
        gap: 8px;
    }}
    .senchado-widget.style-classic .senchado-gear {{
        position: absolute;
        top: 12px;
        right: 12px;
        z-index: 5;
    }}
    .senchado-widget.style-classic .s-classic-sec {{
        width: 100%;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        padding: 8px 10px;
        border-radius: 14px;
        background: var(--s-chip-bg);
    }}
    .senchado-widget.style-classic .s-classic-label {{
        display: inline-flex;
        align-items: center;
        gap: 5px;
        font-size: 9.5px;
        font-weight: 700;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        color: var(--s-sub);
    }}
    .senchado-widget.style-classic .s-classic-main {{
        font-size: 19px;
        font-weight: 750;
        color: var(--s-fg);
        line-height: 1.15;
        font-variant-numeric: tabular-nums;
    }}
    .senchado-widget.style-classic .s-classic-tea {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        color: var(--s-accent);
        font-size: 19px;
        font-weight: 750;
    }}
    .senchado-widget.style-classic .s-classic-tea .s-tea-img {{
        width: 32px;
        height: 32px;
    }}
    .senchado-widget.style-classic .s-classic-sub {{
        font-size: 11.5px;
        font-weight: 500;
        color: var(--s-sub);
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-variant-numeric: tabular-nums;
    }}
    .senchado-widget.style-classic .s-xp-track {{
        width: 84%;
        margin-top: 2px;
    }}

    /* Container-query responsiveness for narrower Bento tiles */
    @container (max-width: 245px) {{
        .s-timer-state {{
            display: none;
        }}
        .s-tbtn {{
            width: 24px !important;
            height: 24px !important;
            min-width: 24px !important;
            max-width: 24px !important;
            min-height: 24px !important;
            max-height: 24px !important;
            flex: 0 0 24px;
        }}
    }}
    @container (max-width: 250px) {{
        .senchado-widget {{
            padding: 12px;
            gap: 8px;
        }}
        .s-tea-emblem {{
            width: 40px;
            height: 40px;
            flex: 0 0 40px;
            border-radius: 12px;
        }}
        .s-tea-img {{
            width: 28px;
            height: 28px;
        }}
        .s-tea-name {{
            font-size: 16px;
        }}
        .s-chip {{
            padding: 6px 4px;
        }}
        .s-chip-k {{
            font-size: 8.5px;
        }}
        .s-chip-v {{
            font-size: 11.5px;
        }}
    }}
    {bento_integration.sizing_css(".senchado-container", ".senchado-widget", ui_settings, default_dim, default_dim)}
    </style>
    """

    gear_btn = (
        f'<button type="button" class="senchado-gear" '
        f'onclick="pycmd(\'senchado_settings\');" title="Open Senchadō Settings" '
        f'aria-label="Open Senchadō Settings">{gear_svg}</button>'
    )

    timer_bar_html = (
        f'<div class="s-timer-bar">'
        f'  <div class="s-timer-left">'
        f'    <span id="senchado-main-state" class="s-timer-state">{html.escape(t_state_label)}</span>'
        f'    <span id="senchado-main-time" class="s-timer-time">{t_time_str}</span>'
        f'  </div>'
        f'  <div class="s-timer-actions">'
        f'    <button type="button" id="senchado-main-play" class="s-tbtn is-primary" onclick="pycmd(\'senchado:toggle_play\');" title="{t_play_title}" aria-label="{t_play_title}">{t_play_icon}</button>'
        f'    <button type="button" class="s-tbtn" onclick="pycmd(\'senchado:reset\');" title="Reset timer" aria-label="Reset timer">{reset_svg}</button>'
        f'    <button type="button" class="s-tbtn" onclick="pycmd(\'senchado:complete\');" title="Mark session completed" aria-label="Mark session completed">{complete_svg}</button>'
        f'  </div>'
        f'</div>'
    )

    if widget_style == "classic":
        xp_block = (
            f'<div class="s-classic-sec">'
            f'  <div class="s-classic-label">{coffee_svg}<span>Senchadō · Level {level}</span></div>'
            f'  <div class="s-xp-track"><div class="s-xp-fill"></div></div>'
            f'  <div class="s-classic-sub">{xp} / {next_level_xp} XP</div>'
            f'</div>'
        ) if show_xp else ""

        task_el = f'<div class="s-classic-sub">{task_text}</div>' if show_task else ""
        tea_block = (
            f'<div class="s-classic-sec">'
            f'  <div class="s-classic-tea">{tea_img_html}<span>{tea_name}</span></div>'
            f'  {task_el}'
            f'</div>'
        )
        brew_block = (
            f'<div class="s-classic-sec">'
            f'  <div class="s-classic-sub">'
            f'    <span>{temp_c}°C</span><span>·</span>'
            f'    <span>Prep {prep_m}m</span><span>·</span>'
            f'    <span>Brew {brew_m}m</span><span>·</span>'
            f'    <span>{cycles_n}×</span>'
            f'  </div>'
            f'</div>'
        ) if show_brew else ""

        inner_html = f"{gear_btn}{xp_block}{tea_block}{timer_bar_html}{brew_block}"
    elif widget_style == "minimal":
        lvl_pill = f'<span class="s-lvl-pill">Lvl {level}</span>' if show_xp else ""
        header_html = (
            f'<header class="s-header">'
            f'  <div class="s-brand">{coffee_svg}<span>Senchadō</span></div>'
            f'  <div class="s-header-right">{lvl_pill}{gear_btn}</div>'
            f'</header>'
        )
        task_el = f'<p class="s-task">{task_text}</p>' if show_task else ""
        temp_pill = (
            f'<div class="s-temp-pill">{temp_svg}<span>{temp_c}°C</span></div>'
            if show_brew
            else ""
        )
        center_html = (
            f'<div class="s-minimal-center">'
            f'  <div class="s-tea-emblem">{tea_img_html}</div>'
            f'  <h3 class="s-tea-name">{tea_name}</h3>'
            f'  {task_el}'
            f'  {temp_pill}'
            f'</div>'
        )
        inner_html = f"{header_html}{center_html}{timer_bar_html}"
    elif widget_style == "compact":
        lvl_pill = f'<span class="s-lvl-pill">Lvl {level}</span>' if show_xp else ""
        header_html = (
            f'<header class="s-header">'
            f'  <div class="s-brand">{coffee_svg}<span>Senchadō</span></div>'
            f'  <div class="s-header-right">{lvl_pill}{gear_btn}</div>'
            f'</header>'
        )
        task_el = f'<p class="s-task">{task_text}</p>' if show_task else ""
        hero_html = (
            f'<div class="s-hero">'
            f'  <div class="s-tea-emblem">{tea_img_html}</div>'
            f'  <div class="s-hero-copy">'
            f'    <h3 class="s-tea-name">{tea_name}</h3>'
            f'    {task_el}'
            f'  </div>'
            f'</div>'
        )
        xp_html = (
            f'<div class="s-xp">'
            f'  <div class="s-xp-meta"><span>Level {level}</span><span>{xp} / {next_level_xp} XP</span></div>'
            f'  <div class="s-xp-track"><div class="s-xp-fill"></div></div>'
            f'</div>'
        ) if show_xp else ""
        metrics_html = (
            f'<footer class="s-metrics">'
            f'  <div class="s-chip"><span class="s-chip-k">{temp_svg}</span><span class="s-chip-v">{temp_c}°C</span></div>'
            f'  <div class="s-chip"><span class="s-chip-k">{timer_svg}</span><span class="s-chip-v">{prep_m}/{brew_m}m</span></div>'
            f'  <div class="s-chip"><span class="s-chip-k">{repeat_svg}</span><span class="s-chip-v">{cycles_n}×</span></div>'
            f'</footer>'
        ) if show_brew else ""
        inner_html = f"{header_html}{hero_html}{timer_bar_html}{xp_html}{metrics_html}"
    else:
        # "zen" (default modern card)
        lvl_pill = f'<span class="s-lvl-pill">Lvl {level}</span>' if show_xp else ""
        header_html = (
            f'<header class="s-header">'
            f'  <div class="s-brand">{coffee_svg}<span>Senchadō</span></div>'
            f'  <div class="s-header-right">{lvl_pill}{gear_btn}</div>'
            f'</header>'
        )
        task_el = f'<p class="s-task">{task_text}</p>' if show_task else ""
        hero_html = (
            f'<div class="s-hero">'
            f'  <div class="s-tea-emblem">{tea_img_html}</div>'
            f'  <div class="s-hero-copy">'
            f'    <h3 class="s-tea-name">{tea_name}</h3>'
            f'    {task_el}'
            f'  </div>'
            f'</div>'
        )
        xp_html = (
            f'<div class="s-xp">'
            f'  <div class="s-xp-meta"><span>Experience</span><span>{xp} / {next_level_xp} XP</span></div>'
            f'  <div class="s-xp-track"><div class="s-xp-fill"></div></div>'
            f'</div>'
        ) if show_xp else ""
        metrics_html = (
            f'<footer class="s-metrics">'
            f'  <div class="s-chip"><span class="s-chip-k">{temp_svg}<span>Temp</span></span><span class="s-chip-v">{temp_c}°C</span></div>'
            f'  <div class="s-chip"><span class="s-chip-k">{timer_svg}<span>Brew</span></span><span class="s-chip-v">{prep_m}/{brew_m}m</span></div>'
            f'  <div class="s-chip"><span class="s-chip-k">{repeat_svg}<span>Cycles</span></span><span class="s-chip-v">{cycles_n}×</span></div>'
            f'</footer>'
        ) if show_brew else ""
        inner_html = f"{header_html}{hero_html}{timer_bar_html}{xp_html}{metrics_html}"

    return f"""
    {style_block}
    <div class="senchado-container">
        <article class="senchado-widget style-{widget_style}">
            {inner_html}
        </article>
    </div>
    """

def refresh_live_widgets():
    global _live_refresh_timer
    if _live_refresh_timer is not None:
        try:
            _live_refresh_timer.stop()
        except Exception:
            pass
    try:
        if getattr(mw, "state", None) == "deckBrowser" and getattr(mw, "deckBrowser", None) is not None:
            mw.deckBrowser.refresh()
    except Exception:
        pass
    try:
        from . import reviewer_overlay
        if hasattr(reviewer_overlay, "overlay") and reviewer_overlay.overlay is not None:
            reviewer_overlay.overlay.refresh_from_settings()
    except Exception:
        pass


def schedule_live_widget_refresh(delay_ms: int = 750):
    """Coalesce heavy DeckBrowser refreshes so dragging sliders never stutters."""
    global _live_refresh_timer
    try:
        from aqt.qt import QObject, QTimer
        if _live_refresh_timer is None:
            parent = mw if isinstance(mw, QObject) else None
            _live_refresh_timer = QTimer(parent)
            _live_refresh_timer.setSingleShot(True)
            _live_refresh_timer.timeout.connect(refresh_live_widgets)
        _live_refresh_timer.start(delay_ms)
    except Exception:
        refresh_live_widgets()


def _patch_deck_browser_timer(current=None, state_name=None):
    try:
        if getattr(mw, "state", None) != "deckBrowser":
            return
        web = getattr(getattr(mw, "deckBrowser", None), "web", None)
        if web is None:
            return
        st = state_name or getattr(getattr(tea_timer, "state", None), "name", "IDLE")
        label = _STATE_LABELS.get(st, st.title())
        running = st in ("PREPARATION", "BREWING")
        if current is None:
            if st == "IDLE":
                current = int(manager.get_current_tea().get("prep_time", 1500) or 1500)
            elif st == "DONE":
                current = 0
            else:
                current = max(0, int(getattr(tea_timer, "current_time", 0) or 0))
        secs = max(0, int(current))
        time_str = f"{secs // 60:02d}:{secs % 60:02d}"
        icon_svg = _lucide_svg("pause" if running else "play", 13)
        title = "Pause timer" if running else ("Resume timer" if st == "PAUSED" else "Start timer")
        js = (
            f"(function(){{"
            f"var t=document.getElementById('senchado-main-time'); if(t) t.textContent={json.dumps(time_str)};"
            f"var s=document.getElementById('senchado-main-state'); if(s) s.textContent={json.dumps(label)};"
            f"var b=document.getElementById('senchado-main-play'); if(b){{b.innerHTML={json.dumps(icon_svg)}; b.title={json.dumps(title)}; b.setAttribute('aria-label',{json.dumps(title)});}}"
            f"}})()"
        )
        web.eval(js)
    except Exception:
        pass


def _on_main_timer_tick(current, total, state_name):
    _patch_deck_browser_timer(current=current, state_name=state_name)


def _on_main_timer_state_changed(state_name):
    if state_name == "DONE":
        refresh_live_widgets()
    else:
        _patch_deck_browser_timer(state_name=state_name)


def on_deck_browser_render(overview, content):
    content.stats += generate_widget_html()

def on_js_message(handled, message, context):
    if message == "senchado_settings":
        from aqt.qt import QTimer
        def _open():
            dialog = SenchadoSettings(mw)
            dialog.exec()
            refresh_live_widgets()
        QTimer.singleShot(0, _open)
        return (True, None)
    if message == "senchado:toggle_play":
        tea_timer.toggle_start_pause(outside_reviewer=True)
        return (True, None)
    if message == "senchado:reset":
        tea_timer.reset()
        tooltip("Timer reset")
        return (True, None)
    if message == "senchado:complete":
        xp = tea_timer.complete_session()
        tooltip(f"Session completed! +{xp} XP" if xp > 0 else "Session completed")
        refresh_live_widgets()
        return (True, None)
    return handled

tea_timer.tick.connect(_on_main_timer_tick)
tea_timer.state_changed.connect(_on_main_timer_state_changed)
gui_hooks.deck_browser_will_render_content.append(on_deck_browser_render)
gui_hooks.webview_did_receive_js_message.append(on_js_message)
