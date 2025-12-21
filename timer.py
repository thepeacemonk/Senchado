from datetime import datetime
from enum import Enum
import os
from aqt.qt import QTimer, pyqtSignal, QObject
from aqt.sound import av_player
from .config import manager

class TimerState(Enum):
    IDLE = 0
    PREPARATION = 1
    BREWING = 2
    DONE = 3
    PAUSED = 4 # Optional, if we want pause functionality

class SenchadoTimer(QObject):
    tick = pyqtSignal(int, int, str) # current_time, total_time, current_state_name
    state_changed = pyqtSignal(str) # new_state_name
    finished = pyqtSignal(int) # xp_gained

    def __init__(self):
        super().__init__()
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_tick)
        
        self._reset_state()

    def _reset_state(self):
        self.state = TimerState.IDLE
        self.previous_state = TimerState.IDLE
        self.current_time = 0
        self.total_time = 0
        self.xp_to_award = 0 # DEPRECATED: managed via pending_xp now
        self.pending_xp = 0
        self.cycles_total = 1
        self.cycles_current = 0

    def start_preparation(self, new_session=True):
        config = manager.get_current_tea()
        if new_session:
            self.cycles_total = config.get("cycles", 1)
            self.cycles_current = 1
            self.pending_xp = 0
            
        self.total_time = config["prep_time"]
        self.current_time = self.total_time
        self.state = TimerState.PREPARATION
        self._start_timer(f"{config['task_name']} (Cycle {self.cycles_current}/{self.cycles_total})")

    def start_brewing(self):
        config = manager.get_current_tea()
        self.total_time = config["brew_time"]
        self.current_time = self.total_time
        self.state = TimerState.BREWING
        self._start_timer(f"Brewing {config['flavor_id'].title()} (Cycle {self.cycles_current}/{self.cycles_total})")

    def _start_timer(self, msg):
        self.state_changed.emit(self.state.name)
        self.timer.start(1000)
        self._emit_tick()

    def _on_tick(self):
        self.current_time -= 1
        if self.current_time <= 0:
            self._on_phase_complete()
        self._emit_tick()

    def _emit_tick(self):
        self.tick.emit(self.current_time, self.total_time, self.state.name)

    def _play_sound(self, filename):
        if manager.get_ui_settings().get("silence_notifications", False):
            return
            
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        sound_path = os.path.join(addon_dir, "notification_sounds", filename)
        
        if os.path.exists(sound_path):
            av_player.play_file(sound_path)

    def _on_phase_complete(self):
        self.timer.stop()
        if self.state == TimerState.PREPARATION:
            # Play Prep Done sound
            self._play_sound("notification.mp3")
            # Auto-transition to brewing
            self.start_brewing()
        elif self.state == TimerState.BREWING:
            # Play Cycle Done sound
            self._play_sound("new_cycle.mp3")
            
            self._accumulate_xp()
            
            if self.cycles_current < self.cycles_total:
                self.cycles_current += 1
                self.start_preparation(new_session=False)
            else:
                self.state = TimerState.DONE
                self.state_changed.emit(self.state.name)
                # We do NOT auto-award XP here anymore, wait for explicit commit or user action if desired
                # But requirement says "XP is awarded after they close Reviewer". 
                # So we just sit in DONE state.

    def _accumulate_xp(self):
        config = manager.get_current_tea()
        temp = config["temperature"]
        # Formula: (Temp / 5) + (Total Cycle Time (in mins))
        # Total Cycle Time = (Prep + Brew) / 60
        cycle_time_min = (config["prep_time"] + config["brew_time"]) / 60
        xp = int((temp / 5) + cycle_time_min)
        self.pending_xp += xp

        # Record History
        try:
            progress = manager.get_progress()
            manager.add_history_entry({
                "timestamp": datetime.now().isoformat(),
                "task_name": config["task_name"],
                "temperature": temp,
                "flavor_id": config["flavor_id"],
                "user_level": progress["level"],
                "prep_time": config["prep_time"],
                "brew_time": config["brew_time"]
            })
        except Exception as e:
            print(f"Error recording tea history: {e}")

    def commit_xp(self):
        if self.pending_xp > 0:
            new_level = manager.update_progress(self.pending_xp)
            self.finished.emit(self.pending_xp)
            granted = self.pending_xp
            self.pending_xp = 0 # Reset after awarding
            return granted
        return 0

    def pause(self):
        if self.state in [TimerState.PREPARATION, TimerState.BREWING]:
            self.timer.stop()
            self.previous_state = self.state
            self.state = TimerState.PAUSED
            self.state_changed.emit(self.state.name)

    def resume(self):
        if self.state == TimerState.PAUSED:
            self.state = self.previous_state
            self.state_changed.emit(self.state.name)
            self.timer.start(1000)
            self._emit_tick()

    def stop(self):
        self.timer.stop()
        self.state = TimerState.IDLE
        self.state_changed.emit(self.state.name)

# Global Instance
tea_timer = SenchadoTimer()
