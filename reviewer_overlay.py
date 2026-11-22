from aqt import mw
from aqt.gui_hooks import reviewer_did_show_question, reviewer_will_end, webview_did_receive_js_message
from aqt.qt import *
from aqt.theme import theme_manager
from aqt.utils import tooltip
import html
import json
import os
import base64

from .timer import tea_timer, TimerState
from .config import manager
from .tea_data import get_tea_by_id
from . import bento_integration

_REVIEWER_TEA_IMG_CACHE = {}

_LUCIDE_PATHS = {
    "coffee": (
        '<path d="M10 2v2"/><path d="M14 2v2"/>'
        '<path d="M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1"/>'
        '<path d="M6 2v2"/>'
    ),
    "timer": (
        '<line x1="10" x2="14" y1="2" y2="2"/>'
        '<line x1="12" x2="15" y1="14" y2="11"/>'
        '<circle cx="12" cy="14" r="8"/>'
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
    "repeat": (
        '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/>'
        '<path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/>'
    ),
    "minimize-2": (
        '<polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/>'
        '<line x1="14" x2="21" y1="10" y2="3"/><line x1="3" x2="10" y1="21" y2="14"/>'
    ),
    "maximize-2": (
        '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/>'
        '<line x1="21" x2="14" y1="3" y2="10"/><line x1="3" x2="10" y1="21" y2="14"/>'
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


def _lucide_svg(name: str, size: int = 14) -> str:
    inner = _LUCIDE_PATHS.get(name, "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
        f'style="display:block;flex:0 0 auto;">{inner}</svg>'
    )


def _temp_icon_name(temp_c: int) -> str:
    if temp_c <= 39:
        return "snowflake"
    if temp_c >= 110:
        return "flame"
    return "thermometer"


class ReviewerOverlay:

    def __init__(self):
        self.active = False
        # Initialize minimized state from settings
        self.minimized = manager.get_ui_settings().get("reviewer_minimal_mode_default", False)
        self.notified_milestones = set()
        self.current_notification = None
        
        reviewer_did_show_question.append(self.on_show_question)
        reviewer_will_end.append(self.on_reviewer_end)
        tea_timer.tick.connect(self.on_tick)
        tea_timer.state_changed.connect(self.on_state_changed)
        tea_timer.finished.connect(self.on_finished)
        webview_did_receive_js_message.append(self.on_js_message)

    def get_tea_image_b64(self, tea_id):
        """Encodes the tea image as base64 for embedding in HTML (cached)."""
        if tea_id in _REVIEWER_TEA_IMG_CACHE:
            return _REVIEWER_TEA_IMG_CACHE[tea_id]
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(addon_dir, "tea_gallery", f"{tea_id}.png")
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
                _REVIEWER_TEA_IMG_CACHE[tea_id] = encoded
                return encoded
        _REVIEWER_TEA_IMG_CACHE[tea_id] = None
        return None
        
    def load_icon(self, name, size=14):
        return _lucide_svg(name, size=size)

    def get_styles(self, ui_settings=None, is_dark=None, for_preview=False, tea=None):
        if ui_settings is None:
            ui_settings = manager.get_ui_settings()
        if is_dark is None:
            is_dark = bento_integration.effective_is_dark()

        if is_dark:
            colors = {
                "bg": "#262925",
                "text": "#E1E6DF",
                "sub": "#95A497",
                "shadow": "rgba(0,0,0,0.34)",
                "border": "rgba(255,255,255,0.11)",
                "chip_bg": "rgba(255,255,255,0.06)",
                "chip_border": "rgba(255,255,255,0.09)",
                "track": "rgba(255,255,255,0.10)",
                "accent": "#3F6D49",
                "accent_hover": "#9FBCA1",
            }
        else:
            colors = {
                "bg": "#FFFFFF",
                "text": "#263628",
                "sub": "#5D6F5E",
                "shadow": "rgba(28,42,30,0.12)",
                "border": "rgba(44,62,45,0.13)",
                "chip_bg": "rgba(44,62,45,0.045)",
                "chip_border": "rgba(44,62,45,0.08)",
                "track": "rgba(44,62,45,0.10)",
                "accent": "#3F6D49",
                "accent_hover": "#6B8E6D",
            }

        custom_card_color = ui_settings.get("widget_card_color_dark" if is_dark else "widget_card_color_light")
        if custom_card_color:
            colors["bg"] = custom_card_color

        tea_accent = bool(ui_settings.get("reviewer_tea_accent", False))
        if tea_accent and tea is not None and getattr(tea, "color_start", None):
            colors["accent"] = tea.color_start
            colors["accent_hover"] = getattr(tea, "color_end", None) or tea.color_start

        position = ui_settings.get("reviewer_position", "top-right")
        inset_px = 10 if for_preview else 20

        pos_rules = {
            "top-right": f"top: {inset_px}px; right: {inset_px}px; transform-origin: top right;",
            "top-left": f"top: {inset_px}px; left: {inset_px}px; transform-origin: top left;",
            "top-center": f"top: {inset_px}px; left: 50%; transform: translateX(-50%); transform-origin: top center;",
            "center-left": f"top: 50%; left: {inset_px}px; transform: translateY(-50%); transform-origin: center left;",
            "middle-left": f"top: 50%; left: {inset_px}px; transform: translateY(-50%); transform-origin: center left;",
            "center-right": f"top: 50%; right: {inset_px}px; transform: translateY(-50%); transform-origin: center right;",
            "middle-right": f"top: 50%; right: {inset_px}px; transform: translateY(-50%); transform-origin: center right;",
            "bottom-left": f"bottom: {inset_px}px; left: {inset_px}px; transform-origin: bottom left;",
            "bottom-center": f"bottom: {inset_px}px; left: 50%; transform: translateX(-50%); transform-origin: bottom center;",
            "bottom-right": f"bottom: {inset_px}px; right: {inset_px}px; transform-origin: bottom right;",
        }
        pos_css = pos_rules.get(position, pos_rules["top-right"])

        opacity = float(ui_settings.get("reviewer_opacity", 100)) / 100.0
        blur = float(ui_settings.get("reviewer_blur", 0) or 0)

        c = QColor(colors['bg'])
        if not c.isValid():
            c = QColor("#262925" if is_dark else "#FFFFFF")
        bg_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, {opacity})"

        ac = QColor(colors['accent'])
        if not ac.isValid():
            ac = QColor("#3F6D49")
        accent_soft = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, {0.22 if is_dark else 0.12})"
        accent_ring = f"rgba({ac.red()}, {ac.green()}, {ac.blue()}, {0.38 if is_dark else 0.24})"

        accent_fg = colors['accent'] if (tea_accent or not is_dark) else colors['accent_hover']

        token_vars = f"""
            --_bg: var(--senchado-bg, {bg_rgba});
            --_fg: var(--senchado-fg, {colors['text']});
            --_sub: var(--senchado-sub, {colors['sub']});
            --_border: var(--senchado-border, {colors['border']});
            --_accent: var(--senchado-accent, {colors['accent']});
            --_accent-fg: var(--senchado-accent-fg, {accent_fg});
            --_accent-2: var(--senchado-accent-2, {colors['accent_hover']});
            --_accent-soft: {accent_soft};
            --_accent-ring: {accent_ring};
            --_chip-bg: {colors['chip_bg']};
            --_chip-border: {colors['chip_border']};
            --_track: {colors['track']};
            --_shadow: {colors['shadow']};
        """

        host_rule = (
            f"""
            .senchado-reviewer-preview-stage {{
                position: relative;
                width: 100%;
                height: 100%;
                pointer-events: none;
                {token_vars}
            }}
            .senchado-reviewer-anchor {{
                position: absolute;
                z-index: 10;
                pointer-events: auto;
                {pos_css}
            }}
            """
            if for_preview
            else f"""
            :host {{
                all: initial;
                display: block;
                position: fixed;
                z-index: 9000;
                {pos_css}
                {token_vars}
            }}
            """
        )

        css = f"""
            @layer base, theme;
            @layer base {{
                {host_rule}
                .senchado-container {{
                    background: var(--_bg);
                    border-radius: 18px;
                    box-shadow: 0 10px 28px var(--_shadow);
                    padding: 13px;
                    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", system-ui, sans-serif;
                    display: flex;
                    flex-direction: column;
                    gap: 9px;
                    border: 1px solid var(--_border);
                    transition: transform 0.25s cubic-bezier(.22, 1, .36, 1), opacity 0.2s ease;
                    backdrop-filter: blur({blur}px);
                    -webkit-backdrop-filter: blur({blur}px);
                    width: 260px;
                    box-sizing: border-box;
                    color: var(--_fg);
                    position: relative;
                    overflow: hidden;
                }}
                .senchado-container * {{
                    box-sizing: border-box;
                }}
                .senchado-container.style-pill,
                .senchado-container.minimized {{
                    width: auto;
                    min-width: 310px;
                    max-width: 460px;
                    padding: 8px 11px;
                    border-radius: 999px;
                    gap: 0;
                }}
                .senchado-container.style-minimal {{
                    width: auto;
                    min-width: 268px;
                    max-width: 320px;
                    padding: 10px 12px;
                    border-radius: 16px;
                    gap: 8px;
                }}
                button {{
                    font: inherit;
                    color: inherit;
                    cursor: pointer;
                }}
                .rev-top {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 6px;
                }}
                .rev-top-meta {{
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    min-width: 0;
                    flex: 1;
                }}
                .rev-state-pill {{
                    display: inline-flex;
                    align-items: center;
                    gap: 5px;
                    padding: 4px 8px;
                    border-radius: 999px;
                    background: var(--_accent-soft);
                    border: none;
                    color: var(--_accent-fg);
                    font-size: 9.5px;
                    font-weight: 700;
                    letter-spacing: 0.04em;
                    text-transform: uppercase;
                    flex: 0 0 auto;
                }}
                .rev-state-dot {{
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: var(--_accent-fg);
                }}
                .rev-task {{
                    font-size: 11.5px;
                    font-weight: 600;
                    color: var(--_sub);
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}
                .rev-actions {{
                    display: inline-flex;
                    align-items: center;
                    gap: 4px;
                    flex: 0 0 auto;
                }}
                .rev-icon-btn {{
                    appearance: none;
                    width: 26px;
                    height: 26px;
                    padding: 0;
                    border-radius: 999px;
                    background: var(--_chip-bg);
                    border: none;
                    color: var(--_sub);
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    transition: color 0.16s ease, background 0.16s ease;
                }}
                .rev-icon-btn:hover {{
                    color: var(--_accent);
                    background: var(--_accent-soft);
                }}
                .rev-hero {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 10px;
                    padding: 9px 11px;
                    border-radius: 14px;
                    background: var(--_chip-bg);
                }}
                .rev-tea-tile {{
                    width: 42px;
                    height: 42px;
                    border-radius: 12px;
                    background: var(--_accent-soft);
                    border: none;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex: 0 0 42px;
                }}
                .rev-tea-tile img {{
                    width: 28px;
                    height: 28px;
                    object-fit: contain;
                    display: block;
                }}
                .rev-tea-mini {{
                    width: 26px;
                    height: 26px;
                    border-radius: 999px;
                    background: var(--_accent-soft);
                    border: none;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex: 0 0 26px;
                }}
                .rev-tea-mini img {{
                    width: 18px;
                    height: 18px;
                    object-fit: contain;
                    display: block;
                }}
                .rev-time-block {{
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    min-width: 0;
                    flex: 1;
                }}
                .rev-time {{
                    font-size: 26px;
                    font-weight: 750;
                    letter-spacing: -0.02em;
                    line-height: 1;
                    color: var(--_fg);
                    font-variant-numeric: tabular-nums;
                }}
                .rev-tea-name {{
                    font-size: 11px;
                    font-weight: 650;
                    color: var(--_accent-fg);
                    margin-top: 3px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    max-width: 100%;
                }}
                .rev-hero-task {{
                    font-size: 10.5px;
                    font-weight: 500;
                    color: var(--_sub);
                    margin-top: 1px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    max-width: 100%;
                }}
                .rev-track {{
                    background: var(--_track);
                    height: 6px;
                    border-radius: 999px;
                    overflow: hidden;
                    width: 100%;
                }}
                .rev-fill {{
                    height: 100%;
                    background: var(--_accent);
                    border-radius: 999px;
                    transition: width 0.3s linear;
                }}
                .rev-footer {{
                    display: grid;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    gap: 6px;
                    width: 100%;
                }}
                .rev-footer.two-cols {{
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }}
                .rev-chip {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    gap: 4px;
                    padding: 5px 6px;
                    border-radius: 999px;
                    background: var(--_chip-bg);
                    border: none;
                    font-size: 10.5px;
                    font-weight: 650;
                    color: var(--_sub);
                    font-variant-numeric: tabular-nums;
                    min-width: 0;
                    overflow: hidden;
                    white-space: nowrap;
                }}
                .rev-chip span {{
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}
                .rev-chip svg {{
                    color: var(--_accent-fg);
                    flex: 0 0 auto;
                }}
                .rev-pill-row {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    width: 100%;
                }}
                .rev-pill-time {{
                    font-size: 15px;
                    font-weight: 750;
                    color: var(--_fg);
                    line-height: 1;
                    font-variant-numeric: tabular-nums;
                    min-width: 44px;
                }}
                .rev-pill-bar {{
                    flex: 1;
                    min-width: 52px;
                }}
                .rev-pill-bar .rev-track {{
                    height: 5px;
                }}
                .rev-pill-meta {{
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 4px 8px;
                    border-radius: 999px;
                    background: var(--_chip-bg);
                    font-size: 10.5px;
                    font-weight: 600;
                    color: var(--_sub);
                    font-variant-numeric: tabular-nums;
                    white-space: nowrap;
                }}
                .rev-pill-meta span {{
                    display: inline-flex;
                    align-items: center;
                    gap: 3px;
                }}
                .rev-pill-meta svg {{
                    color: var(--_accent);
                }}
                .rev-minimal-row {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 8px;
                    padding: 6px 8px;
                    border-radius: 12px;
                    background: var(--_chip-bg);
                }}
                .rev-minimal-left {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    min-width: 0;
                }}
                .rev-minimal-time {{
                    font-size: 18px;
                    font-weight: 750;
                    color: var(--_fg);
                    line-height: 1;
                    font-variant-numeric: tabular-nums;
                }}
                .rev-minimal-track {{
                    height: 4px;
                }}
                .rev-notif {{
                    background: var(--_accent);
                    color: #fff;
                    display: none;
                    align-items: center;
                    justify-content: center;
                    font-weight: 700;
                    font-size: 12px;
                    border-radius: 10px;
                    overflow: hidden;
                    height: 0;
                    opacity: 0;
                    margin-top: 0;
                    transition: height 0.25s ease, opacity 0.25s ease;
                }}
                .rev-controls:empty {{
                    display: none;
                }}
                .rev-done-actions {{
                    display: flex;
                    gap: 8px;
                    margin-top: 2px;
                }}
                .btn-restart {{
                    flex: 1;
                    background: var(--_accent);
                    color: #fff;
                    border: none;
                    border-radius: 10px;
                    padding: 7px 12px;
                    font-size: 11.5px;
                    font-weight: 650;
                    transition: opacity 0.16s ease;
                }}
                .btn-restart:hover {{ opacity: 0.9; }}
                .btn-new {{
                    flex: 1;
                    background: var(--_chip-bg);
                    color: var(--_fg);
                    border: none;
                    border-radius: 10px;
                    padding: 7px 12px;
                    font-size: 11.5px;
                    font-weight: 650;
                    transition: background 0.16s ease;
                }}
                .btn-new:hover {{ background: var(--_accent-soft); }}
            }}
        """
        return css, colors

    def on_show_question(self, card):
        # If we are starting a new reviewer session (active was False), apply default
        if not self.active:
            self.minimized = manager.get_ui_settings().get("reviewer_minimal_mode_default", False)
            
        self.active = True
        if tea_timer.state == TimerState.IDLE:
             tea_timer.start_preparation()
        elif tea_timer.state == TimerState.PAUSED:
             tea_timer.resume()
             
        self.update_ui(tea_timer.current_time, tea_timer.total_time, tea_timer.state.name, initial=True)

    def on_reviewer_end(self):
        self.active = False
        if not getattr(tea_timer, "run_outside_reviewer", False):
            tea_timer.pause()
        # Award any pending XP when leaving reviewer
        xp = tea_timer.commit_xp()
        if xp > 0:
            tooltip(f"🍵 Session Ended. +{xp} XP")

    def on_tick(self, current, total, state_name):
        if self.active and mw.reviewer.web:
            self.check_milestones(current, total, state_name)
            self.update_ui(current, total, state_name)

    def check_milestones(self, current, total, state_name):
        if total <= 0: return
        percent_left = (current / total) * 100
        
        # 50% Milestone
        if 48 < percent_left <= 52 and "50" not in self.notified_milestones:
            self.notified_milestones.add("50")
            msg = ""
            if state_name == "PREPARATION":
                msg = "Almost ready to brew"
            elif state_name == "BREWING":
                msg = "Almost ready to drink"
            
            if msg:
                self.trigger_notification(msg)
            
    def trigger_notification(self, msg):
        self.current_notification = msg
        QTimer.singleShot(4000, self.clear_notification)
        
    def clear_notification(self):
        self.current_notification = None
        if self.active:
            self.update_ui(tea_timer.current_time, tea_timer.total_time, tea_timer.state.name)

    def on_state_changed(self, new_state):
        self.notified_milestones.clear()
        self.current_notification = None
        if new_state == "DONE":
            self.trigger_notification("Tea is ready")
            
        if self.active:
            self.update_ui(tea_timer.current_time, tea_timer.total_time, new_state, initial=True)

    def on_finished(self, xp):
        if self.active:
             tooltip(f"🍵 Cycle Complete! (XP stored)")

    def build_overlay_html(
        self,
        current=None,
        total=None,
        state_name="PREPARATION",
        *,
        tea_config=None,
        ui_settings=None,
        is_dark=None,
        minimized=None,
        cycles_current=None,
        cycles_total=None,
        is_paused=None,
        notification=None,
        for_preview=False,
    ):
        config = tea_config if isinstance(tea_config, dict) else manager.get_current_tea()
        ui = ui_settings if isinstance(ui_settings, dict) else manager.get_ui_settings()
        if is_dark is None:
            is_dark = bento_integration.effective_is_dark()
        if minimized is None:
            minimized = bool(ui.get("reviewer_minimal_mode_default", False)) if for_preview else self.minimized
        if total is None:
            total = int(config.get("prep_time", 1500) or 1500)
        if current is None:
            current = int(total * 0.68) if for_preview else total
        if cycles_current is None:
            cycles_current = 1 if for_preview else tea_timer.cycles_current
        if cycles_total is None:
            cycles_total = int(config.get("cycles", 1) or 1) if for_preview else tea_timer.cycles_total
        if is_paused is None:
            is_paused = False if for_preview else (tea_timer.state in (TimerState.PAUSED, TimerState.IDLE, TimerState.DONE))
        if notification is None and not for_preview:
            notification = self.current_notification

        minutes = int(current) // 60
        seconds = int(current) % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        progress = 0.0
        if total > 0:
            progress = min(100.0, max(0.0, ((total - current) / total) * 100.0))

        tea = get_tea_by_id(config.get("flavor_id", "sencha"))
        rev_style = str(ui.get("reviewer_style", "modern") or "modern").lower()
        if rev_style not in ("modern", "pill", "minimal"):
            rev_style = "modern"

        hide_cycle_counter = bool(ui.get("reviewer_hide_cycle_counter", False))
        show_task = bool(ui.get("reviewer_show_task", True))
        temp_c = int(config.get("temperature", 80) or 80)
        total_mins = max(1, int(round(total / 60)))
        task_text = html.escape(str(config.get("task_name", "Study Session") or "Study Session"))
        tea_name = html.escape(tea.name)
        state_key = str(state_name or "PREPARATION").upper()
        state_labels = {
            "PREPARATION": "Prep",
            "BREWING": "Brew",
            "PAUSED": "Paused",
            "DONE": "Done",
            "IDLE": "Ready",
        }
        state_label = html.escape(state_labels.get(state_key, state_key.title()))

        css, colors = self.get_styles(ui_settings=ui, is_dark=is_dark, for_preview=for_preview, tea=tea)

        # Official Lucide SVG Icons
        timer_icon = _lucide_svg("timer", 12)
        temp_icon = _lucide_svg(_temp_icon_name(temp_c), 12)
        cycle_icon = _lucide_svg("repeat", 11)
        toggle_icon = _lucide_svg("maximize-2" if minimized else "minimize-2", 13)
        toggle_title = "Expand" if minimized else "Minimize"
        pause_icon = _lucide_svg("play" if is_paused else "pause", 13)
        pause_title = "Resume" if is_paused else "Pause"
        reset_icon = _lucide_svg("rotate-ccw", 13)
        complete_icon = _lucide_svg("check", 13)

        has_notif = bool(notification)
        notif_msg = notification if has_notif else ""

        tea_b64 = self.get_tea_image_b64(tea.id)
        tea_img_html = (
            f'<img src="data:image/png;base64,{tea_b64}" alt="{tea_name}">'
            if tea_b64
            else _lucide_svg("coffee", 18)
        )

        buttons_html = ""
        if state_name == "DONE" and not minimized:
            buttons_html = (
                '<div class="rev-done-actions">'
                '  <button type="button" onclick="pycmd(\'senchado:restart\')" class="btn-restart">Restart</button>'
                '  <button type="button" onclick="pycmd(\'senchado:new_tea\')" class="btn-new">New Tea</button>'
                '</div>'
            )

        effective_mode = "pill" if minimized else rev_style
        container_cls = "senchado-container minimized" if minimized else f"senchado-container style-{rev_style}"

        if effective_mode == "pill":
            cycle_pill = (
                f'<span title="Cycle">{cycle_icon}{cycles_current}/{cycles_total}</span>'
                if not hide_cycle_counter
                else ""
            )
            content_html = f"""
              <article class="{container_cls}">
                  <div class="rev-pill-row">
                      <div class="rev-tea-mini">{tea_img_html}</div>
                      <span id="senchado-time" class="rev-pill-time">{time_str}</span>
                      <div class="rev-pill-bar">
                          <div class="rev-track">
                              <div id="senchado-progress" class="rev-fill" style="width: {progress:.2f}%;"></div>
                          </div>
                      </div>
                      <div class="rev-pill-meta">
                          {cycle_pill}
                          <span title="Duration">{timer_icon}{total_mins}m</span>
                          <span title="Temperature">{temp_icon}{temp_c}°</span>
                      </div>
                      <div class="rev-actions">
                          <button type="button" onclick="pycmd('senchado:toggle_pause')" title="{pause_title}" aria-label="{pause_title}" class="rev-icon-btn">{pause_icon}</button>
                          <button type="button" onclick="pycmd('senchado:reset')" title="Reset timer" aria-label="Reset timer" class="rev-icon-btn">{reset_icon}</button>
                          <button type="button" onclick="pycmd('senchado:complete')" title="Mark session completed" aria-label="Mark session completed" class="rev-icon-btn">{complete_icon}</button>
                          <button type="button" onclick="pycmd('senchado:toggle_minimize')" title="{toggle_title}" aria-label="{toggle_title}" class="rev-icon-btn">{toggle_icon}</button>
                      </div>
                  </div>
              </article>
            """
        elif effective_mode == "minimal":
            task_sub = f'<div id="senchado-task" class="rev-task" style="font-size:11px;">{task_text}</div>' if show_task else ""
            content_html = f"""
              <article class="{container_cls}">
                  <div class="rev-minimal-row">
                      <div class="rev-minimal-left">
                          <div class="rev-tea-mini">{tea_img_html}</div>
                          <div style="min-width:0;">
                              <div id="senchado-time" class="rev-minimal-time">{time_str}</div>
                              {task_sub}
                          </div>
                      </div>
                      <div class="rev-actions">
                          <button type="button" onclick="pycmd('senchado:toggle_pause')" title="{pause_title}" aria-label="{pause_title}" class="rev-icon-btn">{pause_icon}</button>
                          <button type="button" onclick="pycmd('senchado:reset')" title="Reset timer" aria-label="Reset timer" class="rev-icon-btn">{reset_icon}</button>
                          <button type="button" onclick="pycmd('senchado:complete')" title="Mark session completed" aria-label="Mark session completed" class="rev-icon-btn">{complete_icon}</button>
                          <button type="button" onclick="pycmd('senchado:toggle_minimize')" title="{toggle_title}" aria-label="{toggle_title}" class="rev-icon-btn">{toggle_icon}</button>
                      </div>
                  </div>
                  <div class="rev-track rev-minimal-track">
                      <div id="senchado-progress" class="rev-fill" style="width: {progress:.2f}%;"></div>
                  </div>
                  <div id="senchado-notif-bar" class="rev-notif"></div>
                  <div id="senchado-controls" class="rev-controls">{buttons_html}</div>
              </article>
            """
        else:
            task_el = f'<span id="senchado-task" class="rev-hero-task">{task_text}</span>' if show_task else ""
            cycle_chip = (
                f'<span class="rev-chip" title="Cycle">{cycle_icon}<span>{cycles_current}/{cycles_total}</span></span>'
                if not hide_cycle_counter
                else ""
            )
            footer_cls = "rev-footer two-cols" if hide_cycle_counter else "rev-footer"
            content_html = f"""
              <article class="{container_cls}">
                  <header class="rev-top">
                      <div class="rev-top-meta">
                          <span class="rev-state-pill"><span class="rev-state-dot"></span>{state_label}</span>
                      </div>
                      <div class="rev-actions">
                          <button type="button" onclick="pycmd('senchado:toggle_pause')" title="{pause_title}" aria-label="{pause_title}" class="rev-icon-btn">{pause_icon}</button>
                          <button type="button" onclick="pycmd('senchado:reset')" title="Reset timer" aria-label="Reset timer" class="rev-icon-btn">{reset_icon}</button>
                          <button type="button" onclick="pycmd('senchado:complete')" title="Mark session completed" aria-label="Mark session completed" class="rev-icon-btn">{complete_icon}</button>
                          <button type="button" onclick="pycmd('senchado:toggle_minimize')" title="{toggle_title}" aria-label="{toggle_title}" class="rev-icon-btn">{toggle_icon}</button>
                      </div>
                  </header>
                  <div class="rev-hero">
                      <div class="rev-tea-tile">{tea_img_html}</div>
                      <div class="rev-time-block">
                          <span id="senchado-time" class="rev-time">{time_str}</span>
                          <span class="rev-tea-name">{tea_name}</span>
                          {task_el}
                      </div>
                  </div>
                  <div class="rev-track">
                      <div id="senchado-progress" class="rev-fill" style="width: {progress:.2f}%;"></div>
                  </div>
                  <footer class="{footer_cls}">
                      <span class="rev-chip" title="Duration">{timer_icon}<span>{total_mins}m</span></span>
                      <span class="rev-chip" title="Temperature">{temp_icon}<span>{temp_c}°C</span></span>
                      {cycle_chip}
                  </footer>
                  <div id="senchado-notif-bar" class="rev-notif"></div>
                  <div id="senchado-controls" class="rev-controls">{buttons_html}</div>
              </article>
            """

        if for_preview:
            return (
                f"<style>{css}</style>"
                f'<div class="senchado-reviewer-preview-stage">'
                f'<div class="senchado-reviewer-anchor">{content_html}</div>'
                f"</div>"
            )

        return {
            "full_shadow_html": f"<style>{css}</style>{content_html}",
            "time_str": time_str,
            "progress": progress,
            "has_notif": has_notif,
            "notif_msg": notif_msg,
            "buttons_html": buttons_html if not minimized else "",
        }

    def refresh_from_settings(self):
        self.minimized = bool(manager.get_ui_settings().get("reviewer_minimal_mode_default", False))
        if self.active and getattr(mw, "reviewer", None) and getattr(mw.reviewer, "web", None):
            if tea_timer.state == TimerState.IDLE:
                tea_timer.start_preparation()
            self.update_ui(tea_timer.current_time, tea_timer.total_time, tea_timer.state.name, initial=True)

    def update_ui(self, current, total, state_name, initial=False):
        built = self.build_overlay_html(current, total, state_name)
        full_shadow_html = built["full_shadow_html"]
        time_str = built["time_str"]
        progress = built["progress"]
        has_notif = built["has_notif"]
        notif_msg = built["notif_msg"]
        buttons_html = built["buttons_html"]
        escaped_html = json.dumps(full_shadow_html)
        
        js = f"""
        (function(){{
            var hostId = 'senchado-host';
            var host = document.getElementById(hostId);
            
            // 1. Host Creation
            if (!host) {{
                host = document.createElement('div');
                host.id = hostId;
                document.body.appendChild(host);
                host.attachShadow({{mode: 'open'}});
            }}
            
            var shadow = host.shadowRoot;
            
            // 2. Render Check
            var container = shadow.querySelector('.senchado-container');
            var isMinimized = container && container.classList.contains('minimized');
            var pyMinimized = {str(self.minimized).lower()};
            
            if (!container || isMinimized !== pyMinimized || {str(initial).lower()}) {{
                shadow.innerHTML = {escaped_html};
            }} else {{
                // Update specific elements in Shadow DOM
                var timeEl = shadow.getElementById('senchado-time');
                if(timeEl) timeEl.innerText = "{time_str}";
                
                var bar = shadow.getElementById('senchado-progress');
                if(bar) bar.style.width = "{progress}%";
                
                // Update notification
                var notif = shadow.getElementById('senchado-notif-bar');
                var shouldShow = {str(has_notif).lower()};
                var msg = "{notif_msg}";
                if (notif) {{
                     if (shouldShow) {{
                         notif.style.display = "flex";
                         notif.style.height = "30px";
                         notif.style.opacity = "1";
                         if (notif.innerText !== msg) notif.innerText = msg;
                     }} else {{
                         notif.style.height = "0px";
                         notif.style.opacity = "0";
                         notif.style.display = "none";
                     }}
                }}
                
                // Update buttons if needed by checking innerHTML mismatch
                var buttonsContent = {json.dumps(buttons_html)};
                var controls = shadow.getElementById('senchado-controls');
                if(controls && buttonsContent !== undefined) {{
                     if(controls.innerHTML !== buttonsContent) controls.innerHTML = buttonsContent;
                }}
            }}
        }})()
        """
        
        mw.reviewer.web.eval(js)

    def on_js_message(self, handled, message, context):
        if message == "senchado:restart":
            tea_timer.start_preparation(new_session=True)
            return (True, None)
        elif message == "senchado:new_tea":
            QTimer.singleShot(0, self.open_settings_and_restart)
            return (True, None)
        elif message == "senchado:toggle_minimize":
            self.minimized = not self.minimized
            self.update_ui(tea_timer.current_time, tea_timer.total_time, tea_timer.state.name, initial=True)
            return (True, None)
        elif message == "senchado:toggle_pause":
            tea_timer.toggle_start_pause(outside_reviewer=getattr(tea_timer, "run_outside_reviewer", False))
            self.update_ui(tea_timer.current_time, tea_timer.total_time, tea_timer.state.name, initial=True)
            return (True, None)
        return handled

    def open_settings_and_restart(self):
        from .settings import SenchadoSettings
        dialog = SenchadoSettings(mw)
        dialog.exec()
        tea_timer.start_preparation()
        self.refresh_from_settings()


def generate_reviewer_html(tea_config=None, ui_settings=None, is_dark=None):
    return overlay.build_overlay_html(
        tea_config=tea_config,
        ui_settings=ui_settings,
        is_dark=is_dark,
        for_preview=True,
    )


# Initialize
overlay = ReviewerOverlay()
