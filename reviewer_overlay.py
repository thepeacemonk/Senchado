from aqt import mw
from aqt.gui_hooks import reviewer_did_show_question, reviewer_will_end, webview_did_receive_js_message
from aqt.qt import *
from aqt.theme import theme_manager
from aqt.utils import tooltip
import json
import os
import base64

from .timer import tea_timer, TimerState
from .config import manager
from .tea_data import get_tea_by_id

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
        """Encodes the tea image as base64 for embedding in HTML"""
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(addon_dir, "tea_gallery", f"{tea_id}.png")
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        return None
        
    def load_icon(self, filename, size=14):
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(addon_dir, "icons", filename)
        if os.path.exists(icon_path):
            with open(icon_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Simple attribute replacement to force size and color
                # We remove existing width/height/fill and inject our own
                import re
                content = re.sub(r'width="[^"]*"', '', content)
                content = re.sub(r'height="[^"]*"', '', content)
                content = re.sub(r'fill="[^"]*"', '', content)
                # Inject new size and currentColor
                return content.replace('<svg', f'<svg width="{size}" height="{size}" fill="currentColor" style="min-width: {size}px; min-height: {size}px;"', 1)
        return ""

    def get_styles(self):
        # Onigiri-match logic
        if theme_manager.night_mode:
            colors = {
                "bg": "#262925",
                "text": "#E1E6DF",
                "sub": "#8F9E91",
                "shadow": "rgba(0,0,0,0.3)",
                "border": "#3A3F39",
                "accent": "#7FA082",
                "accent_hover": "#9FBCA1"
            }
        else:
            colors = {
                "bg": "#FFFFFF",
                "text": "#2C3E2D",
                "sub": "#5D6F5E",
                "shadow": "rgba(0,0,0,0.1)",
                "border": "#D8DED0",
                "accent": "#4A6C4C",
                "accent_hover": "#6B8E6D"
            }
            
        # Position Logic
        position = manager.get_ui_settings().get("reviewer_position", "top-right")
        
        pos_rules = {
            "top-right": "top: 20px; right: 20px; transform-origin: top right;",
            "top-left": "top: 20px; left: 20px; transform-origin: top left;",
            "top-center": "top: 20px; left: 50%; transform: translateX(-50%); transform-origin: top center;",
            "bottom-left": "bottom: 20px; left: 20px; transform-origin: bottom left;",
            "bottom-center": "bottom: 20px; left: 50%; transform: translateX(-50%); transform-origin: bottom center;",
            "bottom-right": "bottom: 20px; right: 20px; transform-origin: bottom right;",
        }
        pos_css = pos_rules.get(position, pos_rules["top-right"])

        # Opacity & Blur
        ui_settings = manager.get_ui_settings()
        opacity = ui_settings.get("reviewer_opacity", 100) / 100.0
        blur = ui_settings.get("reviewer_blur", 0)
        
        # Convert bg to rgba
        c = QColor(colors['bg'])
        bg_rgba = f"rgba({c.red()}, {c.green()}, {c.blue()}, {opacity})"

        # CSS Block
        css = f"""
            :host {{
                all: initial; /* Reset all inherited properties */
                position: fixed;
                z-index: 9000;
                {pos_css}
            }}
            .senchado-container {{
                background: {bg_rgba};
                border-radius: 16px;
                box-shadow: 0 4px 12px {colors['shadow']};
                padding: 16px;
                font-family: 'Inter', system-ui, sans-serif;
                display: flex;
                flex-direction: column;
                gap: 10px;
                border: 1px solid {colors['border']};
                transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
                backdrop-filter: blur({blur}px);
                width: 240px;
                box-sizing: border-box;
                color: {colors['text']};
                position: relative; /* Ensure absolute children are relative to this */
            }}
            .senchado-container.minimized {{
                width: auto;
                min-width: 300px;
                max-width: 400px;
                padding: 8px 12px;
                border-radius: 12px;
                gap: 0px;
            }}
            .text-main {{ color: {colors['text']}; }}
            .text-sub {{ color: {colors['sub']}; }}
            
            button {{
                font-family: inherit;
                cursor: pointer;
            }}
            
            /* Utils */
            .flex {{ display: flex; }}
            .flex-col {{ flex-direction: column; }}
            .items-center {{ align-items: center; }}
            .justify-center {{ justify-content: center; }}
            .justify-between {{ justify-content: space-between; }}
            .gap-2 {{ gap: 8px; }}
            .gap-1 {{ gap: 4px; }}
            
            .btn-restart {{
                flex: 1;
                background: {colors['accent']};
                color: #fff;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                transition: all 0.2s;
            }}
            .btn-new {{
                flex: 1;
                background: transparent;
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
                transition: all 0.2s;
            }}
            
            .toggle-btn {{
                 background: none;
                 border: none;
                 color: {colors['sub']};
                 padding: 4px;
                 display: flex;
                 align-items: center;
                 justify-content: center;
                 opacity: 0.6;
                 transition: opacity 0.2s;
            }}
            .toggle-btn:hover {{ opacity: 1; }}
            
            .toggle-abs {{
                position: absolute;
                top: 6px;
                right: 6px;
                z-index: 20;
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
            self.trigger_notification("Tea is raedy")
            
        if self.active:
            self.update_ui(tea_timer.current_time, tea_timer.total_time, new_state)

    def on_finished(self, xp):
        if self.active:
             tooltip(f"🍵 Cycle Complete! (XP stored)")

    def update_ui(self, current, total, state_name, initial=False):
        minutes = current // 60
        seconds = current % 60
        time_str = f"{minutes:02d}:{seconds:02d}"
        
        progress = 0
        if total > 0:
            progress = ((total - current) / total) * 100
            
        config = manager.get_current_tea()
        tea = get_tea_by_id(config["flavor_id"])
        
        css, colors = self.get_styles()
        
        # Icons
        clock_icon = self.load_icon("clock.svg", size=12)
        thermometer_icon = self.load_icon("temperature-high.svg", size=12)
        cycle_icon = self.load_icon("cycle.svg", size=10) 
        
        # Minimized Toggle Icon
        if self.minimized:
             toggle_icon = self.load_icon("expand.svg", size=16)
             toggle_title = "Maximize"
        else:
             toggle_icon = self.load_icon("minimize.svg", size=16)
             toggle_title = "Minimize"

        # Colors: Using theme 'accent' for bar, not tea color
        bar_color_start = colors['accent']
        bar_color_end = colors['accent_hover']
        
        # Notification Logic
        has_notif = bool(self.current_notification)
        notif_msg = self.current_notification if has_notif else ""
        
        # Tea Image
        tea_b64 = self.get_tea_image_b64(tea.id)
        tea_img_elem = ""
        if tea_b64:
             tea_img_elem = f'<img src="data:image/png;base64,{tea_b64}" style="width: 40px; height: 40px; object-fit: contain; flex-shrink: 0; border-radius: 8px; filter: none !important;">'
        
        # Logic for content based on Minimized state
        if self.minimized:
             content_html = f"""
              <div class="senchado-container minimized">
                  <div class="flex items-center justify-between" style="gap: 12px;">
                     <!-- Time -->
                     <span id="senchado-time" style="font-size: 16px; font-weight: 700; color: {colors['text']}; line-height: 1; tabular-nums: lining-nums; min-width: 50px; text-align: center; display: inline-block;">{time_str}</span>
                     
                     <!-- Progress Bar -->
                     <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 3px; margin: 0 4px;">
                         <div style="background: {colors['border']}; height: 4px; border-radius: 2px; overflow: hidden; width: 100%;">
                              <div id="senchado-progress" style="height: 100%; width: {progress}%; background: linear-gradient(90deg, {bar_color_start}, {bar_color_end}); border-radius: 2px; transition: width 0.3s linear; box-shadow: 0 0 10px {bar_color_start}40;"></div>
                         </div>
                     </div>
    
                     <!-- Info Group -->
                     <div class="flex items-center" style="gap: 8px; font-size: 10px; color: {colors['sub']};">
                          <span title="Cycle" style="display: flex; align-items: center; gap: 2px; opacity: 0.8;">
                            {cycle_icon}
                            {tea_timer.cycles_current}/{tea_timer.cycles_total}
                          </span>
                          <span title="Brewing Time" style="display: flex; align-items: center; gap: 2px; opacity: 0.8;">{clock_icon} {int(tea_timer.total_time/60)}m</span>
                          <span title="Temperature" style="display: flex; align-items: center; gap: 2px; opacity: 0.8;">{thermometer_icon} {config.get('temperature', 80)}º</span>
                     </div>
    
                     <!-- Toggle -->
                     <div class="flex items-center justify-center">
                         <button onclick="pycmd('senchado:toggle_minimize')" title="{toggle_title}" class="toggle-btn" style="margin-left: 4px;">{toggle_icon}</button>
                     </div>
                  </div>
              </div>
             """
        else:
             # Completion Buttons
             buttons_html = ""
             if state_name == "DONE":
                buttons_html = f"""
                <div class="flex gap-2" style="margin-top: 10px;">
                    <button onclick="pycmd('senchado:restart')" class="btn-restart">Restart</button>
                    <button onclick="pycmd('senchado:new_tea')" class="btn-new">New Tea</button>
                </div>
                """

             content_html = f"""
             <div class="senchado-container">
                  <!-- Minimize Button -->
                  <button onclick="pycmd('senchado:toggle_minimize')" title="{toggle_title}" class="toggle-btn toggle-abs">{toggle_icon}</button>
                  
                  <!-- Header -->
                  <div style="text-align: center; margin-bottom: 6px; margin-top: 4px;">
                      <div id="senchado-task" style="font-size: 13px; font-weight: 700; color: {colors['sub']}; margin-bottom: 2px;">{config['task_name']}</div>
                      <div style="font-size: 11px; color: {colors['sub']}; opacity: 0.8;">{state_name.title()}</div>
                  </div>
                  
                  <!-- Center Info -->
                  <div class="flex items-center justify-center" style="gap: 12px; margin-bottom: 0px;">
                      {tea_img_elem}
                      <span id="senchado-time" style="font-size: 28px; font-weight: 700; color: {colors['text']}; line-height: 1; font-variant-numeric: tabular-nums; min-width: 80px; text-align: left;">{time_str}</span>
                  </div>
                  
                  <!-- Progress Bar -->
                  <div style="background: {colors['border']}; height: 8px; border-radius: 4px; overflow: hidden; position: relative; margin-bottom: 8px;">
                       <div id="senchado-progress" style="height: 100%; width: {progress}%; background: linear-gradient(90deg, {bar_color_start}, {bar_color_end}); border-radius: 4px; transition: width 0.3s linear; box-shadow: 0 0 10px {bar_color_start}40;"></div>
                  </div>
                  
                  <!-- Footer -->
                  <div class="flex justify-between items-center" style="font-size: 11px; color: {colors['sub']};">
                      <span class="flex items-center gap-1">{clock_icon} {int(tea_timer.total_time/60)}m</span>
                      <span class="flex items-center gap-1">{thermometer_icon} {config.get('temperature', 80)}º</span>
                      <span class="flex items-center gap-1">Cycle {tea_timer.cycles_current}/{tea_timer.cycles_total}</span>
                      <span style="color: {tea.color_start}; font-weight: 600;">{tea.name}</span>
                  </div>
    
                  <!-- Notifications -->
                  <div id="senchado-notif-bar" style="
                        background: {colors['accent']};
                        color: #fff;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        font-size: 13px;
                        border-radius: 8px;
                        overflow: hidden;
                        height: 0px;
                        opacity: 0;
                        margin-top: 0px;
                        transition: height 0.3s ease, opacity 0.3s ease, margin-top 0.3s ease;
                    "></div>
                    
                  <!-- Buttons -->
                  <div id="senchado-controls">{buttons_html}</div>
             </div>
             """
        
        # Combine CSS and HTML
        full_shadow_html = f"<style>{css}</style>{content_html}"
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
                         notif.style.height = "32px";
                         notif.style.opacity = "1";
                         notif.style.marginTop = "10px";
                         if (notif.innerText !== msg) notif.innerText = msg;
                     }} else {{
                         notif.style.height = "0px";
                         notif.style.opacity = "0";
                         notif.style.marginTop = "0px";
                     }}
                }}
                
                // Update buttons if needed by checking innerHTML mismatch
                var buttonsContent = {json.dumps(buttons_html if not self.minimized else "")};
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
            self.open_settings_and_restart()
            return (True, None)
        elif message == "senchado:toggle_minimize":
            self.minimized = not self.minimized
            self.update_ui(tea_timer.current_time, tea_timer.total_time, tea_timer.state.name, initial=True)
            return (True, None)
        return handled

    def open_settings_and_restart(self):
        from .settings import SenchadoSettings
        dialog = SenchadoSettings(mw)
        if dialog.exec():
            tea_timer.start_preparation()

# Initialize
overlay = ReviewerOverlay()
