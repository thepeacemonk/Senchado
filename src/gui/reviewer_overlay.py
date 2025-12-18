from aqt import mw
from aqt.gui_hooks import reviewer_did_show_question, reviewer_will_end, webview_did_receive_js_message
from aqt.qt import *
from aqt.theme import theme_manager
from aqt.utils import tooltip
import json
import os
import base64

from ..logic.timer import tea_timer, TimerState
from ..config import manager
from ..tea_data import get_tea_by_id

class ReviewerOverlay:

    def __init__(self):
        self.active = False
        self.minimized = False  # New state
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
        addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        img_path = os.path.join(addon_dir, "tea_gallery", f"{tea_id}.png")
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        return None
        
    def load_icon(self, filename, size=14):
        addon_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
            bg = "#262925"        
            text = "#E1E6DF"      
            sub = "#8F9E91"       
            shadow = "rgba(0,0,0,0.3)"
            border = "#3A3F39"    
            accent = "#7FA082"    
            accent_hover = "#9FBCA1"
        else:
            bg = "#FFFFFF"        
            text = "#2C3E2D"      
            sub = "#5D6F5E"       
            shadow = "rgba(0,0,0,0.1)"
            border = "#D8DED0"    
            accent = "#4A6C4C"    
            accent_hover = "#6B8E6D"
            
        # Position Logic
        position = manager.get_ui_settings().get("reviewer_position", "top-right")
        
        # Default top-right
        pos_css = "top: 20px; right: 20px; transform-origin: top right;"
        
        if position == "top-left":
            pos_css = "top: 20px; left: 20px; transform-origin: top left;"
        elif position == "top-center":
            pos_css = "top: 20px; left: 50%; transform: translateX(-50%); transform-origin: top center;"
        elif position == "bottom-left":
            pos_css = "bottom: 20px; left: 20px; transform-origin: bottom left;"
        elif position == "bottom-center":
            pos_css = "bottom: 20px; left: 50%; transform: translateX(-50%); transform-origin: bottom center;"
        elif position == "bottom-right":
            pos_css = "bottom: 20px; right: 20px; transform-origin: bottom right;"
            
        return f"""
            position: fixed;
            {pos_css}
            width: 240px;
            background: {bg};
            border-radius: 16px;
            box-shadow: 0 4px 12px {shadow};
            padding: 16px;
            font-family: 'Inter', system-ui, sans-serif;
            z-index: 9000;
            display: flex;
            flex-direction: column;
            gap: 10px;
            border: 1px solid {border};
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            backdrop-filter: blur(10px);
        """, text, sub, border, accent, accent_hover

    def on_show_question(self, card):
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
        
        style, text_color, sub_color, border_col, accent, accent_hover = self.get_styles()
        
        # Icons
        clock_icon = self.load_icon("clock.svg", size=12)
        thermometer_icon = self.load_icon("temperature-high.svg", size=12)
        cycle_icon = self.load_icon("cycle.svg", size=10) 
        
        # Minimized Toggle Icon
        if self.minimized:
             toggle_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 3 21 3 21 9"></polyline><polyline points="9 21 3 21 3 15"></polyline><line x1="21" y1="3" x2="14" y2="10"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>"""
             toggle_title = "Maximize"
             width = "180px" # Smaller width for minimized
             extras_style = "display: none;"
        else:
             toggle_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 14 10 14 10 20"></polyline><polyline points="20 10 14 10 14 4"></polyline><line x1="14" y1="10" x2="21" y2="3"></line><line x1="3" y1="21" x2="10" y2="14"></line></svg>"""
             toggle_title = "Minimize"
             width = "240px"
             extras_style = ""

        # Colors: Using theme 'accent' for bar, not tea color
        bar_color_start = accent
        bar_color_end = accent_hover
        
        # Notification Logic
        has_notif = bool(self.current_notification)
        notif_msg = self.current_notification if has_notif else ""
        
        # Tea Image
        tea_b64 = self.get_tea_image_b64(tea.id)
        tea_img_elem = ""
        if tea_b64:
             tea_img_elem = f'<img src="data:image/png;base64,{tea_b64}" style="width: 40px; height: 40px; object-fit: contain; flex-shrink: 0; border-radius: 8px;">'
        
        # Completion Buttons
        buttons_html = ""
        if state_name == "DONE" and not self.minimized:
            buttons_html = f"""
            <div style="display: flex; gap: 8px; margin-top: 10px;">
                <button onclick="pycmd('senchado:restart')" style="
                    flex: 1;
                    background: {accent};
                    color: #fff;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                    font-family: inherit;
                ">Restart</button>
                <button onclick="pycmd('senchado:new_tea')" style="
                    flex: 1;
                    background: transparent;
                    color: {text_color};
                    border: 1px solid {border_col};
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 11px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                    font-family: inherit;
                ">New Tea</button>
            </div>
            """
        

        # Adjust main style for width
        if self.minimized:
             # Minimal style tweaks
             style = style.replace("width: 240px;", "width: auto; min-width: 300px; max-width: 400px;")
             style = style.replace("padding: 16px;", "padding: 8px 12px;") # Reduce padding
             style = style.replace("border-radius: 16px;", "border-radius: 12px;")
             style = style.replace("gap: 10px;", "gap: 0px;") # Remove gap
             
             # Single row layout with flex
             # Time | Progress | Info | Toggle
             content_html = f"""
             <div style="display: flex; gap: 12px; align-items: center; justify-content: space-between;">
                 <!-- Time -->
                 <span id="senchado-time" style="font-size: 16px; font-weight: 700; color: {text_color}; line-height: 1; tabular-nums: lining-nums;">{time_str}</span>
                 
                 <!-- Progress Bar (Flex Grow) -->
                 <div style="flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 3px; margin: 0 4px;">
                     <div style="background: {border_col}; height: 4px; border-radius: 2px; overflow: hidden; width: 100%;">
                          <div id="senchado-progress" style="height: 100%; width: {progress}%; background: linear-gradient(90deg, {bar_color_start}, {bar_color_end}); border-radius: 2px; transition: width 0.3s linear; box-shadow: 0 0 10px {bar_color_start}40;"></div>
                     </div>
                 </div>

                 <!-- Info Group (Compact) -->
                 <div style="display: flex; gap: 8px; align-items: center; font-size: 10px; color: {sub_color};">
                      <span title="Cycle" style="display: flex; align-items: center; gap: 2px; opacity: 0.8;">
                        {cycle_icon}
                        {tea_timer.cycles_current}/{tea_timer.cycles_total}
                      </span>
                      <span title="Brewing Time" style="display: flex; align-items: center; gap: 2px; opacity: 0.8;">{clock_icon} {int(tea_timer.total_time/60)}m</span>
                      <span title="Temperature" style="display: flex; align-items: center; gap: 2px; opacity: 0.8;">{thermometer_icon} {config.get('temperature', 80)}º</span>
                 </div>

                 <!-- Toggle -->
                 <button onclick="pycmd('senchado:toggle_minimize')" title="{toggle_title}" style="background: none; border: none; cursor: pointer; color: {sub_color}; padding: 0; display: flex; margin-left: 4px;">{toggle_icon}</button>
             </div>
             """
        else:
             content_html = f"""
             <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 2px;">
                 {tea_img_elem}
                 <div style="flex: 1; display: flex; justify-content: space-between; align-items: center;">
                     <span id="senchado-time" style="font-size: 24px; font-weight: 700; color: {text_color}; line-height: 1;">{time_str}</span>
                     <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end;">
                          <div style="display: flex; gap: 6px; align-items: center;">
                               <button onclick="pycmd('senchado:toggle_minimize')" title="{toggle_title}" style="background: none; border: none; cursor: pointer; color: {sub_color}; padding: 0; display: flex;">{toggle_icon}</button>
                          </div>
                         <div id="senchado-task" style="font-size: 11px; font-weight: 600; color: {sub_color}; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px;">{config['task_name']}</div>
                         <div style="font-size: 11px; color: {sub_color}; opacity: 0.8;">{state_name.title()}</div>
                     </div>
                 </div>
             </div>
             
             <div style="background: {border_col}; height: 8px; border-radius: 4px; overflow: hidden; position: relative;">
                  <div id="senchado-progress" style="height: 100%; width: {progress}%; background: linear-gradient(90deg, {bar_color_start}, {bar_color_end}); border-radius: 4px; transition: width 0.3s linear; box-shadow: 0 0 10px {bar_color_start}40;"></div>
             </div>
             
             <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: {sub_color}; margin-top: 4px;">
                 <span style="display: flex; align-items: center; gap: 4px;">{clock_icon} {int(tea_timer.total_time/60)}m</span>
                 <span style="display: flex; align-items: center; gap: 4px;">{thermometer_icon} {config.get('temperature', 80)}º</span>
                 <span style="display: flex; align-items: center; gap: 4px;">Cycle {tea_timer.cycles_current}/{tea_timer.cycles_total}</span>
                 <span style="color: {tea.color_start}; font-weight: 600;">{tea.name}</span>
             </div>
             """
             
        timer_html = f"""
        <div id="senchado-timer" style="{style}">
            {content_html}

            <div id="senchado-notif-bar" style="
                background: {accent};
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
            <div id="senchado-controls">{buttons_html}</div>
        </div>
        """
        
        escaped_html = json.dumps(timer_html)
        
        js = f"""
        (function(){{
            var timer = document.getElementById('senchado-timer');
            
            // 1. Initial Creation or Toggle Re-render
            if (!timer || {str(initial).lower()}) {{
                if(timer) timer.remove();
                document.body.insertAdjacentHTML('beforeend', {escaped_html});
                timer = document.getElementById('senchado-timer');
            }}
            
            // 2. Data Updates (Only if we didn't just re-render, but here we almost always re-render to handle structure changes safely)
            // But if structure is same, we can optimize. For now, since structure changes significantly between min/max, full replace is safer.
            if(timer) {{
                 document.getElementById('senchado-time').innerText = "{time_str}";
                 var bar = document.getElementById('senchado-progress');
                 if(bar) {{
                     bar.style.width = "{progress}%";
                     // Background is now set in HTML/CSS, but we can keep this for safety
                     bar.style.background = "linear-gradient(90deg, {bar_color_start}, {bar_color_end})";
                 }}
                 
                 // Update Controls
                 var controls = document.getElementById('senchado-controls');
                 if(controls) {{
                     controls.innerHTML = {json.dumps(buttons_html)};
                 }}
            }}
            
            // 3. Notification & Animation (Height Expansion)
            var notif = document.getElementById('senchado-notif-bar');
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
