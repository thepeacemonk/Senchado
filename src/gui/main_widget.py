from aqt import mw, gui_hooks
from aqt.theme import theme_manager
from ..config import manager
from ..tea_data import get_tea_by_id
from .settings import SenchadoSettings
import os
import base64

# Global cache
cached_widget_html = None

def get_zen_palette():
    """
    Returns the Zen/Natural color palette matching settings.py.
    """
    if theme_manager.night_mode:
        return {
            "bg": "#1A1C19",       # Background
            "card_bg": "#262925",  # Card
            "fg": "#E1E6DF",       # Foreground / Text
            "subtle": "#8F9E91",   # Subtext
            "border": "#3A3F39",   # Border
            "accent": "#7FA082",   # Accent
            "accent_sec": "#9FBCA1" # Secondary Accent (Hover/Light)
        }
    else:
        return {
            "bg": "#FAFAF5",       # Background
            "card_bg": "#FFFFFF",  # Card
            "fg": "#2C3E2D",       # Foreground / Text
            "subtle": "#5D6F5E",   # Subtext
            "border": "#D8DED0",   # Border
            "accent": "#4A6C4C",   # Accent
            "accent_sec": "#6B8E6D" # Secondary Accent
        }

def get_tea_image_b64(tea_id):
    """Encodes the tea image as base64 for embedding in HTML"""
    addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    img_path = os.path.join(addon_dir, "tea_gallery", f"{tea_id}.png")
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')
    return None

def generate_widget_html():
    progress = manager.get_progress()
    config = manager.get_current_tea()
    tea = get_tea_by_id(config["flavor_id"])
    colors = get_zen_palette()
    
    next_level_xp = progress["level"] * 100
    xp_percent = (progress["xp"] / next_level_xp) * 100 if next_level_xp > 0 else 0
    
    # SVG Icons
    tea_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M20,10h-.115A3.1,3.1,0,0,0,17,6L3,6c-5.451.372-2,8.651-.589,10.912A6.877,6.877,0,0,0,8.216,20h3.567a6.875,6.875,0,0,0,5.742-3H20C24.814,16.907,25.759,9.822,20,10Zm-8.217,8H8.216a4.881,4.881,0,0,1-4.131-2.179C3.541,15.3.494,8,3,8L17,8a.973.973,0,0,1,.729.325,1.028,1.028,0,0,1,.261.8C17.427,13.384,16.368,17.811,11.783,18ZM20,15H18.588a16.82,16.82,0,0,0,.954-3c1.209-.081,2.546.216,2.458,1.143A1.984,1.984,0,0,1,20,15ZM9.025,3V1a1,1,0,0,1,2,0V3A1,1,0,0,1,9.025,3Zm4,0V1a1,1,0,0,1,2,0V3A1,1,0,0,1,13.025,3Zm-8,0V1a1,1,0,0,1,2,0V3A1,1,0,0,1,5.025,3ZM20,23a1,1,0,0,1-1,1H1a1,1,0,0,1,0-2H19A1,1,0,0,1,20,23Z"/></svg>"""
    gear_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12,8a4,4,0,1,0,4,4A4,4,0,0,0,12,8Zm0,6a2,2,0,1,1,2-2A2,2,0,0,1,12,14Z"/><path d="M21.294,13.9l-.444-.256a9.1,9.1,0,0,0,0-3.29l.444-.256a3,3,0,1,0-3-5.2l-.445.257A8.977,8.977,0,0,0,15,3.513V3A3,3,0,0,0,9,3v.513A8.977,8.977,0,0,0,6.152,5.159L5.705,4.9a3,3,0,0,0-3,5.2l.444.256a9.1,9.1,0,0,0,0,3.29l-.444.256a3,3,0,1,0,3,5.2l.445-.257A8.977,8.977,0,0,0,9,20.487V21a3,3,0,0,0,6,0v-.513a8.977,8.977,0,0,0,2.848-1.646l.447.258a3,3,0,0,0,3-5.2Zm-2.548-3.776a7.048,7.048,0,0,1,0,3.75,1,1,0,0,0,.464,1.133l1.084.626a1,1,0,0,1-1,1.733l-1.086-.628a1,1,0,0,0-1.215.165,6.984,6.984,0,0,1-3.243,1.875,1,1,0,0,0-.751.969V21a1,1,0,0,1-2,0V19.748a1,1,0,0,0-.751-.969A6.984,6.984,0,0,1,7.006,16.9a1,1,0,0,0-1.215-.165l-1.084.627a1,1,0,1,1-1-1.732l1.084-.626a1,1,0,0,0,.464-1.133,7.048,7.048,0,0,1,0-3.75A1,1,0,0,0,4.79,8.992L3.706,8.366a1,1,0,0,1,1-1.733l1.086.628A1,1,0,0,0,7.006,7.1a6.984,6.984,0,0,1,3.243-1.875A1,1,0,0,0,11,4.252V3a1,1,0,0,1,2,0V4.252a1,1,0,0,0,.751.969A6.984,6.984,0,0,1,16.994,7.1a1,1,0,0,0,1.215.165l1.084-.627a1,1,0,1,1,1,1.732l-1.084.626A1,1,0,0,0,18.746,10.125Z"/></svg>"""
    
    # Get Tea Image
    tea_b64 = get_tea_image_b64(tea.id)
    tea_img_elem = ""
    if tea_b64:
        # Use a max-height and fixed width/object-fit to prevent stretching and huge size.
        # Main menu widget is spacious, so 50px-60px height is good.
        tea_img_elem = f'<img src="data:image/png;base64,{tea_b64}" style="height: 32px; width: auto; max-width: 60px; object-fit: contain; margin-right: 12px; vertical-align: middle;">'
    
    return f"""
    <style>
    .senchado-container {{
        container-type: inline-size;
        width: 100%;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }}

    .senchado-widget {{
        background: {colors['card_bg']};
        color: {colors['fg']};
        padding: 24px;
        margin: 20px auto;
        border-radius: 24px;
        max-width: 800px;
        border: 1px solid {colors['border']};
        display: flex;
        flex-direction: row;
        gap: 24px;
        align-items: center;
        justify-content: space-between;
        position: relative;
    }}

    .senchado-gear {{
        position: absolute;
        top: 16px;
        right: 16px;
        color: {colors['subtle']};
        opacity: 0.5;
        cursor: pointer;
        transition: all 0.2s ease;
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        height: 30px;
        border-radius: 50%;
    }}

    .senchado-gear:hover {{
        color: {colors['accent']};
        opacity: 1;
        background: {colors['border']}40;
        transform: rotate(30deg);
    }}

    /* Sections */
    .s-section {{
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-width: 150px;
    }}
    
    .s-center {{
        text-align: center;
        border-left: 1px solid {colors['border']};
        border-right: 1px solid {colors['border']};
        padding: 0 24px;
    }}
    
    .s-right {{
        text-align: right;
    }}

    /* Typography */
    .s-label {{
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        color: {colors['subtle']};
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }}
    
    .s-main {{
        font-size: 28px;
        font-weight: 700;
        color: {colors['fg']};
        line-height: 1.1;
        margin-bottom: 4px;
    }}
    
    .s-detail {{
        font-size: 13px;
        color: {colors['subtle']};
        font-weight: 500;
    }}

    /* XP Bar */
    .xp-container {{
        margin-top: 12px;
        width: 100%;
    }}
    .xp-track {{
        background: {colors['border']};
        height: 6px;
        width: 100%;
        border-radius: 3px;
        overflow: hidden;
    }}
    .xp-fill {{
        height: 100%;
        background: {colors['accent']};
        border-radius: 3px;
        width: {xp_percent}%;
    }}
    .xp-text {{
        font-size: 11px;
        color: {colors['subtle']};
        margin-top: 4px;
        text-align: center;
        font-weight: 600;
    }}

    /* Responsive Logic */
    @container (max-width: 600px) {{
        .senchado-widget {{
            flex-direction: column;
            align-items: stretch;
            gap: 20px;
            text-align: center;
        }}
        
        .s-center {{
            border-left: none;
            border-right: none;
            border-top: 1px solid {colors['border']};
            border-bottom: 1px solid {colors['border']};
            padding: 20px 0;
            margin: 0;
        }}
        
        .s-right {{
            text-align: center;
        }}
        
        .s-label {{
            justify-content: center;
        }}
        
        .s-sub {{
            justify-content: center !important;
        }}
    }}
    </style>
    
    <div class="senchado-container">
        <div class="senchado-widget">
            <div class="senchado-gear" onclick="pycmd('senchado_settings');" title="Open Tea House">
                {gear_icon}
            </div>
            <!-- Left: Level & XP -->
            <div class="s-section">
                <div class="s-label">{tea_icon} SENCHADŌ</div>
                <div class="s-main">Level {progress['level']}</div>
                <div class="xp-container">
                    <div class="xp-track">
                        <div class="xp-fill"></div>
                    </div>
                </div>
                <div class="xp-text">{progress['xp']} / {next_level_xp} XP</div>
            </div>
            
            <!-- Center: Current Session -->
            <div class="s-section s-center">
                <div class="s-label" style="justify-content: center;">CURRENT SESSION</div>
                <div class="s-main" style="color: {colors['accent']}; display: flex; align-items: center; justify-content: center;">
                    {tea_img_elem}
                    <div>{tea.name}</div>
                </div>
                <div class="s-detail">{config['task_name']}</div>
            </div>
            
            <!-- Right: Temperature & Settings -->
            <div class="s-section s-right">
                <div class="s-label" style="justify-content: flex-end;">TEMPERATURE</div>
                <div class="s-main">{config['temperature']}°C</div>
                <div class="s-detail s-sub" style="display: flex; gap: 12px; justify-content: flex-end;">
                    <span>Prep: {int(config['prep_time']/60)}m</span>
                    <span>Brew: {int(config['brew_time']/60)}m</span>
                </div>
            </div>
        </div>
    </div>
    """

def on_deck_browser_render(overview, content):
    content.stats += generate_widget_html()

def on_js_message(handled, message, context):
    if message == "senchado_settings":
        dialog = SenchadoSettings(mw)
        dialog.exec()
        return (True, None)
    return handled

gui_hooks.deck_browser_will_render_content.append(on_deck_browser_render)
gui_hooks.webview_did_receive_js_message.append(on_js_message)
