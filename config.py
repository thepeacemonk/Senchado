import json
import os
from aqt import mw
from .tea_data import get_tea_by_id
from datetime import datetime, timedelta, date
from copy import deepcopy
import os

DEFAULT_CONFIG = {
    "current_tea": {
        "flavor_id": "sencha",
        "task_name": "Study Session",
        "temperature": 80,
        "prep_time": 25 * 60, # 25 minutes in seconds
        "brew_time": 5 * 60,  # 5 minutes in seconds
        "cycles": 1,
    },
    "user_progress": {
        "xp": 0,
        "level": 1,
        "total_brews": 0
    },
    "tea_history": [],
    "favorites": [],
    "ui_settings": {
        "reviewer_position": "top-right", # Options: top-left, top-right, bottom-left, bottom-right
        "silence_notifications": False,
        "widget_opacity": 100,
        "widget_glass": False,
        "widget_glass_strength": 0,
        "reviewer_opacity": 100,
        "reviewer_blur": 0,
        "reviewer_minimal_mode_default": False
    }
}

class ConfigManager:
    def __init__(self):
        self.config = {}
        # Path to user_files folder and tea_history.json inside it
        addon_dir = os.path.dirname(os.path.abspath(__file__))
        user_files_dir = os.path.join(addon_dir, "user_files")
        
        # Create user_files folder if it doesn't exist
        if not os.path.exists(user_files_dir):
            os.makedirs(user_files_dir)
        
        self.tea_history_path = os.path.join(user_files_dir, "tea_history.json")
        self.load()

    def load(self):
        # 1. Determine Addon Directory Name
        addon_dir = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        if not addon_dir or addon_dir == "src":
             addon_dir = "Senchado"

        # 2. Load Anki Config (Preferences, current tea, etc.)
        anki_config = {}
        if mw.addonManager:
            anki_config = mw.addonManager.getConfig(addon_dir) or {}
        
        # 3. Load History/Progress from tea_history.json
        history_data = self._load_history_file()
        
        # 4. Migration Logic
        # If tea_history.json did not exist (or was just created empty) AND we have old data in Anki config
        # We assume if the file existed, migration is already done or not needed.
        # But specifically checking if file exists on disk is better done before _load calls or by checking if data is default.
        # _load_history_file returns defaults if file missing.
        
        file_exists = os.path.exists(self.tea_history_path)
        
        if not file_exists and ("user_progress" in anki_config or "tea_history" in anki_config):
            # Migrate data from Anki config to history structure
            if "user_progress" in anki_config:
                history_data["user_progress"] = anki_config["user_progress"]
            if "tea_history" in anki_config:
                history_data["tea_history"] = anki_config["tea_history"]
            
            # Save to new file
            self._save_history_file(history_data)
            
            # Clean up Anki config
            cleaned_anki_config = deepcopy(anki_config)
            if "user_progress" in cleaned_anki_config: del cleaned_anki_config["user_progress"]
            if "tea_history" in cleaned_anki_config: del cleaned_anki_config["tea_history"]
            
            if mw.addonManager:
                mw.addonManager.writeConfig(addon_dir, cleaned_anki_config)
            
            anki_config = cleaned_anki_config

        # 5. Merge into runtime config
        self.config = deepcopy(DEFAULT_CONFIG)
        self.config.update(anki_config) # Priorities keys from Anki config
        self.config.update(history_data) # Priorities keys from history file (overwrites defaults)

        # Self-correction: Ensure total_brews is at least as large as the known history
        # This fixes issues where the counter got out of sync
        history_cnt = len(self.config.get("tea_history", []))
        if self.config["user_progress"]["total_brews"] < history_cnt:
            self.config["user_progress"]["total_brews"] = history_cnt
            self.save() # Persist the correction

    def _load_history_file(self):
        data = {
            "user_progress": deepcopy(DEFAULT_CONFIG["user_progress"]),
            "tea_history": deepcopy(DEFAULT_CONFIG["tea_history"])
        }
        if os.path.exists(self.tea_history_path):
            try:
                with open(self.tea_history_path, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # Only update known keys to avoid polluting with garbage if file is messy
                    if "user_progress" in loaded: data["user_progress"] = loaded["user_progress"]
                    if "tea_history" in loaded: data["tea_history"] = loaded["tea_history"]
            except Exception as e:
                print(f"Error loading tea_history.json: {e}")
        return data

    def _save_history_file(self, data):
        try:
            with open(self.tea_history_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving tea_history.json: {e}")

    def save(self):
        addon_dir = os.path.basename(os.path.dirname(os.path.abspath(__file__)))
        if not addon_dir or addon_dir == "src":
             addon_dir = "Senchado"

        # Separate data sources
        anki_keys = ["current_tea", "favorites", "ui_settings"]
        anki_data = {k: self.config.get(k) for k in anki_keys if k in self.config}
        
        hist_keys = ["user_progress", "tea_history"]
        hist_data = {k: self.config.get(k) for k in hist_keys if k in self.config}

        # Save to Anki
        if mw.addonManager:
            current_conf = mw.addonManager.getConfig(addon_dir) or {}
            # Update only our managed keys, preserve others if any? 
            # Usually writeConfig replaces everything. We should be careful.
            # But here we are the owner of the config.
            # To be safe, merge with existing just in case (though we loaded it earlier)
            current_conf.update(anki_data)
            # Ensure we don't write history back to Anki if it's there for some reason
            if "user_progress" in current_conf: del current_conf["user_progress"]
            if "tea_history" in current_conf: del current_conf["tea_history"]
            
            mw.addonManager.writeConfig(addon_dir, current_conf)

        # Save to File
        self._save_history_file(hist_data)

    def get_current_tea(self):
        return self.config.get("current_tea", DEFAULT_CONFIG["current_tea"])

    def get_progress(self):
        return self.config.get("user_progress", DEFAULT_CONFIG["user_progress"])
    
    def update_progress(self, xp_gain: int):
        progress = self.get_progress()
        progress["xp"] += xp_gain
        progress["total_brews"] += 1
        
        required_xp = progress["level"] * 100
        while progress["xp"] >= required_xp:
            progress["xp"] -= required_xp
            progress["level"] += 1
            required_xp = progress["level"] * 100
            
        self.config["user_progress"] = progress
        self.save()
        return progress["level"]

    
    def add_history_entry(self, entry_data: dict):
        """
        Adds a new entry to the tea history and prunes old entries (older than 30 days).
        entry_data should contain:
        - timestamp (ISO format string)
        - task_name
        - temperature
        - flavor_id
        - user_level
        """
        history = self.config.get("tea_history", [])
        
        # Add new entry
        history.insert(0, entry_data)
        
        # Prune old entries
        cutoff_date = datetime.now() - timedelta(days=30)
        valid_history = []
        
        for entry in history:
            try:
                entry_date = datetime.fromisoformat(entry["timestamp"])
                if entry_date > cutoff_date:
                    valid_history.append(entry)
            except (ValueError, KeyError):
                continue
                
        self.config["tea_history"] = valid_history
        self.save()

    def set_current_tea(self, flavor_id: str, task_name: str, temperature: int, prep_time: int, brew_time: int, cycles: int):
        self.config["current_tea"] = {
            "flavor_id": flavor_id,
            "task_name": task_name,
            "temperature": temperature,
            "prep_time": prep_time,
            "brew_time": brew_time,
            "cycles": cycles
        }
        self.save()

    def get_favorites(self):
        return self.config.get("favorites", [])

    def add_favorite(self, config: dict):
        favorites = self.get_favorites()
        favorites.append(config)
        self.config["favorites"] = favorites
        self.save()

    def remove_favorite(self, index: int):
        favorites = self.get_favorites()
        if 0 <= index < len(favorites):
            favorites.pop(index)
            self.config["favorites"] = favorites
            self.save()

    def get_ui_settings(self):
        return self.config.get("ui_settings", DEFAULT_CONFIG["ui_settings"])

    def set_ui_setting(self, key, value):
        if "ui_settings" not in self.config:
            self.config["ui_settings"] = deepcopy(DEFAULT_CONFIG["ui_settings"])
        self.config["ui_settings"][key] = value
        self.save()

# Global instance
manager = ConfigManager()
