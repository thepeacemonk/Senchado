from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *

from .config import manager
from .timer import tea_timer

from .settings import SenchadoSettings
from . import bento_integration
from . import reviewer_overlay # Init overlay
from . import main_widget # Init main widget



_is_settings_open = False
def debounce_settings(func):
    def wrapper(*args, **kwargs):
        global _is_settings_open
        if _is_settings_open:
            return
        _is_settings_open = True
        try:
            return func()
        finally:
            _is_settings_open = False
    return wrapper

@debounce_settings
def show_settings():
    settings = SenchadoSettings(mw)
    settings.exec()
    main_widget.refresh_live_widgets()

def setup_menu():
    bento_integration.register_widget(
        "Senchado",
        settings_callback=show_settings,
        open_callback=show_settings,
        kind="game",
    )
    bento_integration.add_menu_action("Senchado - Tea House", show_settings)

def setup_hooks():
    # Will add hooks for Reviewer and DeckBrowser here
    pass

# Initialize
setup_menu()
setup_hooks()
