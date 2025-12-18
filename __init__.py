from aqt import mw
from aqt.utils import showInfo
from aqt.qt import *

from .src.config import manager
from .src.logic.timer import tea_timer

from .src.gui.settings import SenchadoSettings
from .src.gui import reviewer_overlay # Init overlay
from .src.gui import main_widget # Init main widget

def show_settings():
    settings = SenchadoSettings(mw)
    settings.exec()
    # showInfo("Senchadō Settings - Coming Soon!\nCurrent Level: " + str(manager.get_progress()["level"]))

def setup_menu():
    action = QAction("Komori Timer", mw)
    action.triggered.connect(show_settings)
    mw.form.menuTools.addAction(action)

def setup_hooks():
    # Will add hooks for Reviewer and DeckBrowser here
    pass

# Initialize
setup_menu()
setup_hooks()
