from aqt.qt import *
from aqt import mw
from aqt.theme import theme_manager
import os
import webbrowser
from .config import manager
from .tea_data import TEAS, get_available_teas, TeaFlavor
from .timer import tea_timer
from datetime import datetime

class TeaOptionButton(QFrame):
    clicked = pyqtSignal(str) # tea_id

    def __init__(self, tea_id, parent=None):
        super().__init__(parent)
        self.tea_id = tea_id
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit(self.tea_id)
        super().mouseReleaseEvent(event)

class TeaSelectionMenu(QDialog):
    def __init__(self, parent=None, colors=None, available_teas=None, current_tea_id=None, width=400):
        super().__init__(parent)
        # self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.colors = colors or {}
        self.teas = available_teas or []
        self.selected_tea_id = current_tea_id
        self.menu_width = width
        
        self.setup_ui()
        
    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Main Container with shadow/border
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors.get('card', '#FFFFFF')};
                border: 1px solid {self.colors.get('border', '#CCCCCC')};
                border-radius: 12px;
            }}
        """)
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(5, 5, 5, 5) # Smaller margins for scroll area
        container.setLayout(container_layout)
        
        addon_root = os.path.dirname(os.path.abspath(__file__))
        
        # Header with Close Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 5, 8, 5)
        
        title = QLabel("Select Tea")
        title.setStyleSheet(f"font-weight: bold; color: {self.colors.get('fg', '#000')}; font-size: 14px;")
        
        close_btn = QToolButton()
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        icon_path = os.path.join(addon_root, "icons", "xmark-simple.svg")
        if os.path.exists(icon_path):
            # Load and colorize SVG icon
            src_pix = QPixmap(icon_path)
            # Create a pixmap of the same size
            colored_pix = QPixmap(src_pix.size())
            colored_pix.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(colored_pix)
            # Determine color based on theme - user requested #FFFFFF (dark mode) or #252925 (light mode)
            icon_color = QColor("#FFFFFF") if theme_manager.night_mode else QColor("#252925")
            
            # Draw the icon using CompositionMode_SourceIn to colorize non-transparent pixels
            # First map the source pixmap
            painter.drawPixmap(0, 0, src_pix)
            # Set composition mode
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            # Fill with color
            painter.fillRect(colored_pix.rect(), icon_color)
            painter.end()
            
            close_btn.setIcon(QIcon(colored_pix))
            close_btn.setIconSize(QSize(16, 16))
        else:
            close_btn.setText("✕")
            
        close_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                color: {self.colors.get('fg', '#000')};
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background: {self.colors.get('border', '#E0E0E0')};
            }}
        """)
        close_btn.clicked.connect(self.reject)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        container_layout.addLayout(header_layout)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colors.get('border', '#CCCCCC')};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Grid Widget
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        
        # Grid of teas
        grid = QGridLayout()
        grid.setSpacing(8)
        grid_widget.setLayout(grid)
        
        # addon_root already defined above
        
        # Calculate columns based on count
        # Fixed 1 column (List View) as requested
        cols = 1
        
        for i, tea in enumerate(self.teas):
            row = i // cols
            col = i % cols
            
            
            btn = TeaOptionButton(tea.id)
            
            # Styling based on selection
            is_selected = (tea.id == self.selected_tea_id)
            bg_color = self.colors.get('bg', '#F0F0F0')
            border_color = self.colors.get('accent', '#4A6C4C') if is_selected else "transparent"
            
            btn.setStyleSheet(f"""
                TeaOptionButton {{
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 8px;
                }}
                TeaOptionButton:hover {{
                    background-color: {self.colors.get('border', '#E0E0E0')};
                }}
            """)
            
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(8, 8, 8, 8)
            btn.setLayout(btn_layout)
            
            # Icon
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(32, 32)
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            img_path = os.path.join(addon_root, "tea_gallery", f"{tea.id}.png")
            if os.path.exists(img_path):
                pix = QPixmap(img_path)
                pix = pix.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                icon_lbl.setPixmap(pix)
            else:
                icon_lbl.setText("🍵")
            
            # Text
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)
            name_lbl = QLabel(tea.name)
            name_lbl.setStyleSheet(f"border: none; background: transparent; font-weight: 600; color: {self.colors.get('fg', '#000')};")
            name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            text_layout.addWidget(name_lbl)
            
            btn_layout.addWidget(icon_lbl)
            btn_layout.addLayout(text_layout)
            
            # Connect signal
            btn.clicked.connect(self.select_tea)
            
            grid.addWidget(btn, row, col)
            
        scroll.setWidget(grid_widget)
        container_layout.addWidget(scroll)
        layout.addWidget(container) # Add container to main layout
        
        # Dynamic resizing
        import math
        total_rows = math.ceil(len(self.teas) / cols)
        row_height_approx = 60 # 48 content + padding/spacing
        calculated_height = (total_rows * row_height_approx) + 20 # + margins
        
        
        # Max height for ~3.5 rows to show scrolling is possible if many items
        # row height approx 60. 3.5 * 60 = 210. + header/padding.
        # "Limit height to ~250px"
        max_height = 250
        
        final_height = min(calculated_height, max_height)
        # Ensure minimum so it's not tiny
        final_height = max(final_height, 100)
        
        self.setFixedHeight(final_height)
        self.setFixedWidth(self.menu_width) # Match parent width
        
        # Install event filter on App to detect outside clicks (since we are not a real Popup anymore)
        mw.app.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            # Handle Qt6 vs Qt5
            if hasattr(event, "globalPosition"):
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()
            
            # Map global click to local coords to see if it's inside our geometry
            # Or simpler: check if click is strictly outside our frame geometry
            
            # Note: mapFromGlobal maps to the widget's coordinate system (0,0 is top-left of widget)
            # rect() is (0,0, width, height)
            
            # Only trigger if the click target isn't us or our children (already handled by event propagation usually, 
            # but since we filter App events, we see everything)
            
            # Check if one of our children is under mouse? No need, rect check is enough.
            # If click is inside us, rect().contains(mapFromGlobal(pos)) is True.
            
            if not self.rect().contains(self.mapFromGlobal(pos)):
                self.reject()
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        # Clean up event filter
        mw.app.removeEventFilter(self)
        super().closeEvent(event)
        
    def select_tea(self, tea_id):
        self.selected_tea_id = tea_id
        self.accept()

class ModernWarningDialog(QDialog):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.message = message
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        
        # Colors
        if theme_manager.night_mode:
            self.c = {
                "bg": "#1A1C19", "fg": "#E1E6DF", "border": "#3A3F39", 
                "accent": "#7FA082", "btn_txt": "#1A1C19"
            }
        else:
            self.c = {
                "bg": "#FAFAF5", "fg": "#2C3E2D", "border": "#D8DED0", 
                "accent": "#4A6C4C", "btn_txt": "#FFFFFF"
            }
            
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.c['bg']};
                border: 1px solid {self.c['border']};
                border-radius: 12px;
            }}
        """)
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(25, 25, 25, 25)
        container_layout.setSpacing(20)
        container.setLayout(container_layout)
        
        # Title
        title_lbl = QLabel("🍵")
        title_lbl.setStyleSheet(f"font-size: 40px; border: none; background: transparent;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(title_lbl)
        
        # Message
        msg_lbl = QLabel(self.message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setStyleSheet(f"font-size: 14px; color: {self.c['fg']}; border: none; background: transparent;")
        container_layout.addWidget(msg_lbl)
        
        # OK Button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setFixedSize(100, 35)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.c['accent']};
                color: {self.c['btn_txt']};
                border-radius: 8px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        btn_layout.addStretch()
        
        container_layout.addLayout(btn_layout)
        
        layout.addWidget(container)
        
        # Sizing
        self.setFixedWidth(320)
        # Height dynamic

class TeaSelector(QFrame):
    teaSelected = pyqtSignal(str) # Emits tea_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_tea_id = None
        self.colors = {}
        self.setFixedHeight(45)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Ensure QFrame background works with stylesheets and transparency
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        self.setup_ui()
        
    def setColors(self, colors):
        self.colors = colors
        self.update_style()
        
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter) # Center vertically
        self.setLayout(layout)
        
        self.icon_lbl = QLabel()
        self.icon_lbl.setFixedSize(28, 28) # Slightly smaller to fit 45px comfortably
        self.icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.name_lbl = QLabel("Select Tea")
        self.name_lbl.setStyleSheet("font-weight: 600; font-size: 14px;")
        self.name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.chevron = QLabel("▼") # or an icon
        self.chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout.addWidget(self.icon_lbl)
        layout.addSpacing(10)
        layout.addWidget(self.name_lbl)
        layout.addStretch()
        layout.addWidget(self.chevron)
        
    def update_style(self):
        self.setStyleSheet(f"""
            TeaSelector {{
                background-color: {self.colors.get('card', '#FFFFFF')};
                border: 1px solid {self.colors.get('border', '#CCCCCC')};
                border-radius: 12px;
            }}
            TeaSelector:hover {{
                border: 1px solid {self.colors.get('accent', '#4A6C4C')};
            }}
            QLabel {{
                color: {self.colors.get('fg', '#000000')};
                border: none;
                background: transparent;
            }}
        """)
        
    def setTea(self, tea_id):
        self.current_tea_id = tea_id
        if tea_id in TEAS:
            tea = TEAS[tea_id]
            self.name_lbl.setText(tea.name)
            
            addon_root = os.path.dirname(os.path.abspath(__file__))
            img_path = os.path.join(addon_root, "tea_gallery", f"{tea_id}.png")
            if os.path.exists(img_path):
                pix = QPixmap(img_path)
                pix = pix.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.icon_lbl.setPixmap(pix)
            else:
                self.icon_lbl.setText("🍵")
        else:
            self.name_lbl.setText("Unknown Tea")
            self.icon_lbl.setText("❓")
            
        self.teaSelected.emit(tea_id)
            
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.show_menu()
            
    def show_menu(self):
        # Get parent settings to know available teas usually
        # But we need access to progress/level...
        # Let's assume parent has it or we pass it.
        # Best way is for the main class to configure this, but logic is here.
        # We'll use manager here since we're in the same file
        progress = manager.get_progress()
        available = get_available_teas(progress["level"])
        
        menu = TeaSelectionMenu(self, self.colors, available, self.current_tea_id, width=self.width())
        
        # Position menu below the selector
        global_pos = self.mapToGlobal(QPoint(0, self.height() + 5))
        
        # Smart Positioning (Clamp to screen)
        screen = self.screen() if hasattr(self, "screen") else QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            
            # Check right edge
            if global_pos.x() + menu.width() > screen_geo.right():
                global_pos.setX(screen_geo.right() - menu.width() - 10)
            
            # Check bottom edge
            if global_pos.y() + menu.height() > screen_geo.bottom():
                # If it doesn't fit below, try above
                above_y = self.mapToGlobal(QPoint(0, 0)).y() - menu.height() - 5
                if above_y >= screen_geo.top():
                    global_pos.setY(above_y)
                else:
                    # If it doesn't fit above either, clamp to bottom
                     global_pos.setY(screen_geo.bottom() - menu.height() - 10)

        menu.move(global_pos)
        
        if menu.exec():
            if menu.selected_tea_id and menu.selected_tea_id != self.current_tea_id:
                self.setTea(menu.selected_tea_id)


class VersionPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        # Theme colors
        if theme_manager.night_mode:
            bg_color = "#1A1C19"
            text_color = "#E1E6DF"
            border_color = "#3A3F39"
            btn_bg = "#252925"
            btn_txt = "#FFFFFF"
            btn_hover = "#3A3F39"
        else:
            bg_color = "#FAFAF5"
            text_color = "#2C3E2D"
            border_color = "#D8DED0"
            btn_bg = "#3F6D49"
            btn_txt = "#FFFFFF"
            btn_hover = "#4A7E54"

        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(20, 15, 20, 15)
        container_layout.setSpacing(15)
        container.setLayout(container_layout)

        label = QLabel("Version 1.1")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"""
            color: {text_color};
            font-size: 14px;
            font-weight: 600;
            border: none;
            background: transparent;
        """)
        
        container_layout.addWidget(label)
        
        # Close Button
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setFixedSize(80, 30)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_txt};
                border-radius: 15px;
                font-weight: 600;
                font-size: 12px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        container_layout.addLayout(btn_layout)

        layout.addWidget(container)

class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

class SenchadoSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Senchado")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        self.setup_styles()
        
        # Track card widgets
        self.tea_cards = {}

        # Content Stack (Initialize early for dependency, add to layout later)
        self.stack = QStackedWidget()

        # Header Container
        self.header_container = QWidget()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(40, 20, 40, 0)
        self.header_container.setLayout(header_layout)
        
        # Logo Row with Side Buttons
        logo_row = QHBoxLayout()
        logo_row.setSpacing(20)
        
        # Button colors based on theme
        btn_bg = "#252925" if theme_manager.night_mode else "#3F6D49"
        btn_text = "#FFFFFF"
        btn_hover = "#3A3F39" if theme_manager.night_mode else "#4A7E54"
        
        # Left Button - Buy me a tea
        buy_tea_btn = QPushButton("Buy me a tea")
        buy_tea_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buy_tea_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border-radius: 20px;
                font-weight: 600;
                font-size: 13px;
                min-width: 120px;
                max-width: 140px;
                min-height: 40px;
                max-height: 40px;
                padding: 0px 20px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        buy_tea_btn.clicked.connect(lambda: webbrowser.open("https://buymeacoffee.com/peacemonk"))
        
        # Logo
        self.logo_label = ClickableLabel()
        addon_root = os.path.dirname(os.path.abspath(__file__))
        logo_filename = "Senchado_night.png" if theme_manager.night_mode else "Senchado.png"
        logo_path = os.path.join(addon_root, logo_filename)
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            logo_pixmap = logo_pixmap.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.clicked.connect(self.show_version_popup)
        
        # Right Button - Report bug
        report_btn = QPushButton("Report bug")
        report_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        report_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_text};
                border-radius: 20px;
                font-weight: 600;
                font-size: 13px;
                min-width: 120px;
                max-width: 140px;
                min-height: 40px;
                max-height: 40px;
                padding: 0px 20px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """)
        report_btn.clicked.connect(lambda: webbrowser.open("https://github.com/thepeacemonk/Komori"))
        
        logo_row.addStretch()
        logo_row.addWidget(buy_tea_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        logo_row.addWidget(self.logo_label)
        logo_row.addWidget(report_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        logo_row.addStretch()
        
        header_layout.addLayout(logo_row)
        header_layout.addSpacing(10)
        
        self.setup_nav_bar()
        header_layout.addWidget(self.nav_bar)
        
        
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.layout.addWidget(self.header_container)
        
        # Add Stack to Layout (Bottom)
        self.layout.addWidget(self.stack)

        self.setup_tea_room()
        self.setup_secret_garden()
        self.setup_favorites_page()
        self.setup_history_page()
        
        # Button Box container for padding
        btn_container = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 10, 20, 20)
        btn_container.setLayout(btn_layout)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.save_and_close)
        self.button_box.rejected.connect(self.reject)
        btn_layout.addWidget(self.button_box)
        
        self.layout.addWidget(btn_container)
        
        self.load_settings()

        # Connect tea selector signal
        self.tea_selector.teaSelected.connect(self.update_tea_selection_visuals)
        # Initial visual update
        self.update_tea_selection_visuals()


    def show_version_popup(self):
        popup = VersionPopup(self)
        
        # Calculate position relative to logo
        # Map logo position to global coordinates
        logo_pos = self.logo_label.mapToGlobal(QPoint(0, 0))
        logo_width = self.logo_label.width()
        logo_height = self.logo_label.height()
        
        popup_width = popup.width() # This might be small if not shown yet, verify size hint
        # Force a size hint calculation or set fixed size in popup if needed, 
        # but let's assume popup has a reasonable size or we set it.
        # VersionPopup uses layout, let's hint it.
        popup.adjustSize()
        popup_width = popup.width()
        popup_height = popup.height()
        
        # Center horizontally: logo_x + (logo_w - popup_w) / 2
        center_x = logo_pos.x() + (logo_width - popup_width) // 2
        
        # Position below logo or centered vertically over it? 
        # "Aligned with the logo" usually means centered.
        # Let's simple center it over the logo for now as that's safe for "pop-up".
        # Or maybe slightly below center?
        center_y = logo_pos.y() + (logo_height - popup_height) // 2
        
        popup.move(center_x, center_y)
        popup.exec()

    def get_theme_colors(self):
        # Helper to get colors for child widgets before setup_styles runs/or if needed
        # Actually it's better if we just reuse self.c if setup_styles ran.
        # But setup_styles runs in __init__.
        return getattr(self, 'c', {})

    def setup_nav_bar(self):
        self.nav_bar = QFrame()
        self.nav_bar.setObjectName("nav_bar")
        self.nav_bar.setFixedHeight(50) 
        # Removed setFixedSize(700, 50) to allow width to adapt, 
        # but we might want a maximum width to prevent it looking too stretched on large screens
        self.nav_bar.setMaximumWidth(700) 
        self.nav_bar.setMinimumWidth(400) # Ensure it doesn't get too small to fit buttons
        
        # Pill Shape & Shadow
        # Using ID selectors to ensure high specificity.
        # Buttons are 40px high, so 20px radius makes them perfectly pill-shaped.
        self.nav_bar.setStyleSheet(f"""
            QFrame#nav_bar {{
                background-color: {self.c['card']};
                border-radius: 25px;
                border: 1px solid {self.c['border']};
            }}
            QPushButton#nav_btn {{
                border-radius: 20px;
                border: none;
                font-weight: 600;
                background-color: transparent;
                color: {self.c['sub']};
                margin: 0px; 
            }}
            QPushButton#nav_btn:hover {{
                background-color: {self.c['bg']}; 
                color: {self.c['fg']};
            }}
            QPushButton#nav_btn[active="true"] {{
                background-color: {self.c['accent']};
                color: {self.c['btn_txt']};
                font-weight: bold;
                border-radius: 20px; /* Explicitly restate to prevent override */
            }}
            QPushButton#nav_btn[active="true"]:hover {{
                background-color: {self.c['accent_hover']};
            }}
        """)
        

        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)
        self.nav_bar.setLayout(layout)
        
        # Buttons
        # Shortened names for better fit on small screens
        self.btn_tea_room = QPushButton("Tea Room")
        self.btn_tea_room.setObjectName("nav_btn")
        self.btn_garden = QPushButton("Level") # Shortened from Secret Tea Garden
        self.btn_garden.setObjectName("nav_btn")
        self.btn_favorites = QPushButton("Favorites") # Shortened from Favorite Tea Flavors
        self.btn_favorites.setObjectName("nav_btn")
        self.btn_history = QPushButton("History") # Shortened from Past Tea Preps
        self.btn_history.setObjectName("nav_btn")
        
        for btn in [self.btn_tea_room, self.btn_garden, self.btn_favorites, self.btn_history]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setCheckable(True)
            btn.setFixedHeight(40)
            btn.setMinimumWidth(60) # Allow shrinking
            btn.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed) # Adapt width to text
            
        self.btn_tea_room.clicked.connect(lambda: self.switch_tab(0))
        self.btn_garden.clicked.connect(lambda: self.switch_tab(1))
        self.btn_favorites.clicked.connect(lambda: self.switch_tab(3)) # Favorites at index 3 (visually before history maybe?)
        # Let's reorder: Room(0), Garden(1), Favorites(2), History(3)
        # But setup_history_page called after favorites in my init logic above?
        # My init: setup_tea_room, setup_secret_garden, setup_favorites_page, setup_history_page
        # So stack indices: 0, 1, 2, 3.
        # Favorites is 2. History is 3.
        
        self.btn_favorites.clicked.connect(lambda: self.switch_tab(2))
        self.btn_history.clicked.connect(lambda: self.switch_tab(3))
        
        layout.addWidget(self.btn_tea_room)
        layout.addWidget(self.btn_garden)
        layout.addWidget(self.btn_favorites)
        layout.addWidget(self.btn_history)
        
        # Initial State
        self.switch_tab(0)

    def switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        
        # Determine which button is active
        self.btn_tea_room.setProperty("active", index == 0)
        self.btn_garden.setProperty("active", index == 1)
        self.btn_favorites.setProperty("active", index == 2)
        self.btn_history.setProperty("active", index == 3)
        
        # Force style update
        for btn in [self.btn_tea_room, self.btn_garden, self.btn_favorites, self.btn_history]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def setup_styles(self):
        # Natural / Zen Palette
        if theme_manager.night_mode:
            self.c = {
                "bg": "#1A1C19", "fg": "#E1E6DF", "sub": "#8F9E91",
                "card": "#262925", "border": "#3A3F39", "accent": "#7FA082",
                "accent_hover": "#9FBCA1", "btn_txt": "#1A1C19"
            }
        else:
            self.c = {
                "bg": "#FAFAF5", "fg": "#2C3E2D", "sub": "#5D6F5E",
                "card": "#FFFFFF", "border": "#D8DED0", "accent": "#4A6C4C",
                "accent_hover": "#6B8E6D", "btn_txt": "#FFFFFF"
            }
            
        qss = f"""
            QDialog {{
                background-color: {self.c['bg']};
                color: {self.c['fg']};
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }}
            QTabWidget::pane {{
                border: none;
                background-color: {self.c['bg']};
            }}
            QTabBar::tab {{
                background: transparent;
                color: {self.c['sub']};
                padding: 12px 20px;
                font-weight: 600;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {self.c['accent']};
                border-bottom: 2px solid {self.c['accent']};
            }}
            QLabel {{
                color: {self.c['fg']};
            }}
            QLineEdit, QComboBox, QSpinBox {{
                background-color: {self.c['card']};
                border: 1px solid {self.c['border']};
                border-radius: 8px;
                padding: 8px 12px;
                color: {self.c['fg']};
                selection-background-color: {self.c['accent']};
            }}
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border: 1px solid {self.c['accent']};
            }}
            /* Cards */
            QFrame.tea-card {{
                background-color: {self.c['card']};
                border-radius: 12px;
                border: 1px solid {self.c['border']};
            }}
            QPushButton {{
                background-color: {self.c['accent']};
                color: {self.c['btn_txt']};
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {self.c['accent_hover']};
            }}
            /* Specific fix for standard buttons in button box if needed */
            QDialogButtonBox QPushButton {{
                min-width: 60px;
            }}
        """
        self.setStyleSheet(qss)

    def setup_tea_room(self):
        tab = QWidget()
        # Main Layout (Tab Container)
        tab_layout = QVBoxLayout()
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab.setLayout(tab_layout)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        # Content Widget
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        
        # The actual layout that holds our form
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        content.setLayout(main_layout)
        
        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        
        # Title
        title = QLabel("Brewing Configurations")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        main_layout.addWidget(title)
        
        # Form Container (Card)
        form_card = QFrame()
        form_card.setProperty("class", "tea-card")
        card_layout = QFormLayout()
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(20)
        form_card.setLayout(card_layout)
        
        # Task Name
        self.task_name_input = QLineEdit()
        self.task_name_input.setPlaceholderText("e.g. Study Kanji")
        card_layout.addRow(self.create_label("Task Name"), self.task_name_input)

        # Tea Selection
        # Tea Selection
        # self.tea_combo = QComboBox()
        # card_layout.addRow(self.create_label("Select Tea"), self.tea_combo)
        
        self.tea_selector = TeaSelector()
        self.tea_selector.setColors(self.c)
        card_layout.addRow(self.create_label("Select Tea"), self.tea_selector)

        # Temperature
        # Temperature
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 200)
        self.temp_slider.valueChanged.connect(self.update_temp_label)
        
        # Gradient Style
        # Blue -> Green -> Yellow -> Orange -> Red
        # 0% -> 25% -> 50% -> 75% -> 100%
        gradient_qss = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                height: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #89b4fa, 
                    stop:0.25 #a6e3a1, 
                    stop:0.5 #f9e2af, 
                    stop:0.75 #fab387, 
                    stop:1 #f38ba8);
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: transparent;
                border-radius: 5px;
            }
            QSlider::add-page:horizontal {
                background: transparent;
                border-radius: 5px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 1px solid #5c5f77;
                width: 18px;
                height: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
        """
        self.temp_slider.setStyleSheet(gradient_qss)
        
        self.temp_label = QLabel("80º")
        self.temp_label.setFixedWidth(40)
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Icons
        snowflake_icon = QLabel("❄️") # Using unicode for simplicity, looks good on Mac
        snowflake_icon.setStyleSheet("font-size: 16px;")
        flame_icon = QLabel("🔥")
        flame_icon.setStyleSheet("font-size: 16px;")
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(snowflake_icon)
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(flame_icon)
        temp_layout.addWidget(self.temp_label)
        card_layout.addRow(self.create_label("Temperature"), temp_layout)
        
        # Timer Settings
        self.prep_time_spin = QSpinBox()
        self.prep_time_spin.setRange(1, 120)
        self.prep_time_spin.setSuffix(" min")
        card_layout.addRow(self.create_label("Preparation Time"), self.prep_time_spin)
        
        self.brew_time_spin = QSpinBox()
        self.brew_time_spin.setRange(1, 60)
        self.brew_time_spin.setSuffix(" min")
        card_layout.addRow(self.create_label("Brewing Time"), self.brew_time_spin)

        self.cycles_spin = QSpinBox()
        self.cycles_spin.setRange(1, 10)
        self.cycles_spin.setSuffix(" cycles")
        card_layout.addRow(self.create_label("Number of Cycles"), self.cycles_spin)
        
        main_layout.addWidget(form_card)
        main_layout.addStretch()

        main_layout.addWidget(form_card)
        
        # --- Widget Position Section ---
        
        # Title
        pos_title = QLabel("Tea Room on Reviewer")
        pos_title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px; margin-top: 10px;")
        main_layout.addWidget(pos_title)
        
        pos_card = QFrame()
        pos_card.setProperty("class", "tea-card")
        pos_card_layout = QVBoxLayout()
        pos_card_layout.setContentsMargins(30, 30, 30, 30)
        pos_card_layout.setSpacing(20)
        pos_card.setLayout(pos_card_layout)
        
        # Opacity
        self.reviewer_opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.reviewer_opacity_slider.setRange(0, 100)
        self.reviewer_opacity_slider.setValue(100)
        self.reviewer_opacity_slider.valueChanged.connect(self.update_reviewer_opacity_label)
        
        # Consistent Modern Style
        slider_qss = f"""
            QSlider::groove:horizontal {{
                border: 1px solid {self.c['border']};
                height: 6px;
                background: {self.c['border']};
                margin: 2px 0;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {self.c['accent']};
                border: 1px solid {self.c['accent']};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {self.c['accent_hover']};
            }}
            QSlider::sub-page:horizontal {{
                background: {self.c['accent']};
                border-radius: 3px;
            }}
        """
        self.reviewer_opacity_slider.setStyleSheet(slider_qss)
        
        self.reviewer_opacity_label = QLabel("100%")
        self.reviewer_opacity_label.setFixedWidth(40)
        self.reviewer_opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        row_opacity = QHBoxLayout()
        row_opacity.addWidget(QLabel("Opacity"))
        row_opacity.addWidget(self.reviewer_opacity_slider)
        row_opacity.addWidget(self.reviewer_opacity_label)
        pos_card_layout.addLayout(row_opacity)

        # Glassmorphism (Blur)
        self.reviewer_blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.reviewer_blur_slider.setRange(0, 20)
        self.reviewer_blur_slider.setValue(0)
        self.reviewer_blur_slider.valueChanged.connect(self.update_reviewer_blur_label)
        
        self.reviewer_blur_slider.setStyleSheet(slider_qss)
        
        self.reviewer_blur_label = QLabel("0px")
        self.reviewer_blur_label.setFixedWidth(40)
        self.reviewer_blur_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        row_blur = QHBoxLayout()
        row_blur.addWidget(QLabel("Blur"))
        row_blur.addWidget(self.reviewer_blur_slider)
        row_blur.addWidget(self.reviewer_blur_label)
        pos_card_layout.addLayout(row_blur)
        
        # Minimal Mode Default
        self.reviewer_minimal_check = QCheckBox("Minimal mode as default")
        self.reviewer_minimal_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reviewer_minimal_check.setStyleSheet(f"""
            QCheckBox {{
                font-weight: 500;
                color: {self.c['fg']};
                margin-top: 10px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {self.c['border']};
                background: {self.c['card']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.c['accent']};
                border: 1px solid {self.c['accent']};
            }}
        """)
        pos_card_layout.addWidget(self.reviewer_minimal_check)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(f"background-color: {self.c.get('border', '#ccc')}; max-height: 1px; border: none;")
        pos_card_layout.addWidget(sep)
        
        pos_lbl = self.create_label("Review Screen Widget Position")
        pos_card_layout.addWidget(pos_lbl)
        
        # Container for selector and preview
        pos_container = QHBoxLayout()
        pos_container.setSpacing(40)
        
        # 1. Selector (Grid of 6 buttons)
        selector_grid = QGridLayout()
        selector_grid.setSpacing(10)
        
        self.pos_buttons = {}
        positions = [
            ("top-left", 0, 0), ("top-center", 0, 1), ("top-right", 0, 2),
            ("bottom-left", 1, 0), ("bottom-center", 1, 1), ("bottom-right", 1, 2)
        ]
        
        # current selection
        current_pos = manager.get_ui_settings().get("reviewer_position", "top-right")
        self.selected_pos = current_pos
        
        for pos_id, r, c in positions:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(60, 40)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # Store ID in dynamic property
            btn.setProperty("pos_id", pos_id)
            
            # Icon logic
            if "center" in pos_id:
                icon_char = "↑" if "top" in pos_id else "↓"
            else:
                icon_char = "↖" if pos_id == "top-left" else "↗" if pos_id == "top-right" else "↙" if pos_id == "bottom-left" else "↘"
                
            btn.setText(icon_char)
            btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 20px; 
                    background-color: {self.c['bg']};
                    color: {self.c['sub']};
                    border: 1px solid {self.c['border']};
                }}
                QPushButton:checked {{
                    background-color: {self.c['accent']};
                    color: white;
                    border: 1px solid {self.c['accent']};
                }}
            """)
            
            if pos_id == current_pos:
                btn.setChecked(True)
            
            btn.clicked.connect(lambda checked, pid=pos_id: self.on_pos_clicked(pid))
            self.pos_buttons[pos_id] = btn
            selector_grid.addWidget(btn, r, c)
            
        pos_container.addLayout(selector_grid)
        
        # 2. Preview (Mini screen representation)
        self.preview_frame = QFrame()
        self.preview_frame.setFixedSize(160, 100)
        self.preview_frame.setStyleSheet(f"""
            background-color: {self.c['bg']};
            border: 2px solid {self.c['border']};
            border-radius: 8px;
        """)
        
        # The widget representation within preview
        self.preview_widget = QLabel()
        self.preview_widget.setFixedSize(40, 25)
        self.preview_widget.setStyleSheet(f"""
            background-color: {self.c['accent']};
            border-radius: 4px;
        """)
        
        # Helper layout for preview positioning
        self.preview_layout = QGridLayout(self.preview_frame)
        self.preview_layout.setContentsMargins(10, 10, 10, 10)
        
        # Update preview initially
        self.update_pos_preview(current_pos)
        
        pos_container.addWidget(self.preview_frame)
        pos_container.addStretch()
        
        pos_card_layout.addLayout(pos_container)
        
        # 3. Silence Notifications
        self.silence_check = QCheckBox("Silence notifications")
        self.silence_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.silence_check.setStyleSheet(f"""
            QCheckBox {{
                font-weight: 500;
                color: {self.c['fg']};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {self.c['border']};
                background: {self.c['card']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.c['accent']};
                border: 1px solid {self.c['accent']};
            }}
        """)
        pos_card_layout.addWidget(self.silence_check)
        main_layout.addWidget(pos_card)

        # --- Tea Room Widget Section ---
        
        widget_title = QLabel("Tea Room Widget")
        widget_title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px; margin-top: 10px;")
        main_layout.addWidget(widget_title)

        widget_card = QFrame()
        widget_card.setProperty("class", "tea-card")
        widget_layout = QFormLayout()
        widget_layout.setContentsMargins(30, 30, 30, 30)
        widget_layout.setSpacing(20)
        widget_card.setLayout(widget_layout)

        # 1. Opacity
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(10, 100) # Minimum 10%
        self.opacity_slider.setSingleStep(10)
        
        # Modern Slider Style
        self.opacity_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {self.c['border']};
                height: 6px;
                background: {self.c['border']};
                margin: 2px 0;
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {self.c['accent']};
                border: 1px solid {self.c['accent']};
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {self.c['accent_hover']};
            }}
            QSlider::sub-page:horizontal {{
                background: {self.c['accent']};
                border-radius: 3px;
            }}
        """)
        
        opacity_container = QHBoxLayout()
        opacity_container.addWidget(self.opacity_slider)
        self.opacity_label = QLabel("100%")
        self.opacity_label.setFixedWidth(40)
        self.opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        opacity_container.addWidget(self.opacity_label)
        
        self.opacity_slider.valueChanged.connect(lambda v: self.opacity_label.setText(f"{v}%"))
        
        widget_layout.addRow(self.create_label("Opacity"), opacity_container)

        # 2. Blur (Glassmorphism)
        # Checkbox removed, slider controls everything (0 = off)
        self.glass_slider = QSlider(Qt.Orientation.Horizontal)
        self.glass_slider.setRange(0, 20) # Blur radius 0-20px
        self.glass_slider.setSingleStep(1)
        
        # Reusing slider style
        self.glass_slider.setStyleSheet(self.opacity_slider.styleSheet())
        
        glass_container = QHBoxLayout()
        glass_container.addWidget(self.glass_slider)
        self.glass_label = QLabel("0px")
        self.glass_label.setFixedWidth(40)
        self.glass_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        glass_container.addWidget(self.glass_label)
        
        self.glass_slider.valueChanged.connect(lambda v: self.glass_label.setText(f"{v}px"))
        
        widget_layout.addRow(self.create_label("Blur"), glass_container)

        # 3. Size
        size_container = QHBoxLayout()
        size_container.setSpacing(15)
        
        self.size_group = QButtonGroup(self)
        self.size_buttons = {}
        
        # User requested: "Small (less info), Medium (more info), Big (Level, Session, Temp)"
        sizes = [
            ("small", "Small", "Level, Tea (200px)"),
            ("medium", "Medium", "Level, Tea, Temp (300px)"), 
            ("big", "Big", "Full Details (400px)") 
        ]

        for size_id, title, subtitle in sizes:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(100, 60)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            btn.setProperty("size_id", size_id)
            
            btn_layout = QVBoxLayout(btn)
            btn_layout.setContentsMargins(5,5,5,5)
            btn_layout.setSpacing(2)
            
            b_title = QLabel(title)
            b_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_title.setStyleSheet("font-weight: 600; border: none; background: transparent;")
            
            b_sub = QLabel(subtitle)
            b_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            b_sub.setStyleSheet(f"font-size: 10px; border: none; background: transparent; color: {self.c['sub']};")
            
            btn_layout.addWidget(b_title)
            btn_layout.addWidget(b_sub)
            
            # Store references
            btn.title_lbl = b_title
            btn.sub_lbl = b_sub
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.c['bg']};
                    border: 1px solid {self.c['border']};
                    border-radius: 8px;
                }}
                QPushButton:checked {{
                    background-color: {self.c['accent']};
                    border: 1px solid {self.c['accent']};
                }}
            """)
            
            self.size_group.addButton(btn)
            self.size_buttons[size_id] = btn
            
            btn.clicked.connect(self.update_size_selection_style)
            
            size_container.addWidget(btn)
            
        widget_layout.addRow(self.create_label("Size"), size_container)
        
        main_layout.addWidget(widget_card)

        main_layout.addStretch()

        self.stack.addWidget(tab)

    def on_pos_clicked(self, pos_id):
        self.selected_pos = pos_id
        # Update buttons state
        for pid, btn in self.pos_buttons.items():
            btn.setChecked(pid == pos_id)
            
        # Update preview
        self.update_pos_preview(pos_id)
        
    def update_pos_preview(self, pos_id):
        # Clear layout
        # QGridLayout logic: remove widget, then re-add in correct cell
        self.preview_layout.removeWidget(self.preview_widget)
        
        r = 0 if "top" in pos_id else 1
        
        if "left" in pos_id:
            c = 0
            align = Qt.AlignmentFlag.AlignLeft
        elif "right" in pos_id:
            c = 2
            align = Qt.AlignmentFlag.AlignRight
        else:
            c = 1
            align = Qt.AlignmentFlag.AlignHCenter
        
        v_align = Qt.AlignmentFlag.AlignTop if r==0 else Qt.AlignmentFlag.AlignBottom
                
        self.preview_layout.addWidget(self.preview_widget, r, c, v_align | align)
        
    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: 500;")
        return lbl

    def setup_secret_garden(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        tab.setLayout(layout)
        
        # 1. Hero / Level Section
        progress = manager.get_progress()
        level = progress['level']
        current_xp = progress['xp']
        required_xp = level * 100
        
        hero_card = QFrame()
        hero_card.setProperty("class", "tea-card")
        hero_layout = QVBoxLayout()
        hero_layout.setContentsMargins(24, 24, 24, 24)
        hero_card.setLayout(hero_layout)
        
        # Top Row: Level + Stats
        top_row = QHBoxLayout()
        lvl_lbl = QLabel(f"Level {level}")
        lvl_lbl.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {self.c['accent']};")
        top_row.addWidget(lvl_lbl)
        top_row.addStretch()
        
        stats_lbl = QLabel(f"{progress['total_brews']} Total Brews")
        stats_lbl.setStyleSheet(f"color: {self.c['sub']}; font-weight: 600;")
        top_row.addWidget(stats_lbl)
        hero_layout.addLayout(top_row)
        
        # Progress Bar
        hero_layout.addSpacing(15)
        pbar_container = QWidget()
        pbar_layout = QVBoxLayout()
        pbar_layout.setContentsMargins(0,0,0,0)
        pbar_layout.setSpacing(8)
        
        pbar_info = QHBoxLayout()
        xp_text = QLabel(f"{current_xp} / {required_xp} XP")
        xp_text.setStyleSheet(f"color: {self.c['sub']}; font-weight: bold; font-size: 13px;")
        pbar_info.addWidget(xp_text)
        pbar_info.addStretch()
        next_lvl = QLabel(f"Next: Level {level + 1}")
        next_lvl.setStyleSheet(f"color: {self.c['sub']}; font-size: 13px;")
        pbar_info.addWidget(next_lvl)
        
        p_bar = QProgressBar()
        p_bar.setRange(0, required_xp)
        p_bar.setValue(current_xp)
        p_bar.setTextVisible(False)
        p_bar.setFixedHeight(12)
        p_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.c['bg']};
                border-radius: 6px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {self.c['accent']};
                border-radius: 6px;
            }}
        """)
        
        pbar_layout.addLayout(pbar_info)
        pbar_layout.addWidget(p_bar)
        hero_layout.addLayout(pbar_layout)
        
        layout.addWidget(hero_card)
        
        # 2. Grid of Teas
        layout.addSpacing(20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        grid = QGridLayout()
        grid.setSpacing(15)
        grid.setContentsMargins(0, 0, 0, 0)
        content.setLayout(grid)
        
        sorted_teas = sorted(TEAS.values(), key=lambda t: t.unlock_level)
        
        current_row = 0
        current_col = 0
        
        for tea in sorted_teas:
            card = self.create_tea_card(tea, progress['level'])
            self.tea_cards[tea.id] = card
            
            if tea.id == "keemun":
                # If currently on the second column, move to next row so we can span full width
                if current_col > 0:
                    current_row += 1
                    current_col = 0
                
                grid.addWidget(card, current_row, current_col, 1, 2)
                
                # Advance to next row after adding a full-width item
                current_row += 1
                current_col = 0
            else:
                grid.addWidget(card, current_row, current_col)
                
                current_col += 1
                if current_col > 1:
                    current_col = 0
                    current_row += 1
            
        # Push content up if few items
        grid.setRowStretch(grid.rowCount(), 1)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)

        self.stack.addWidget(tab)

    def create_tea_card(self, tea, user_level):
        card = QFrame()
        card.setProperty("class", "tea-card")
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(15, 20, 15, 20)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.setLayout(card_layout)
        
        # Icon
        icon_lbl = QLabel()
        icon_lbl.setFixedSize(80, 80)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        addon_root = os.path.dirname(os.path.abspath(__file__))
        img_path = os.path.join(addon_root, "tea_gallery", f"{tea.id}.png")
        
        if os.path.exists(img_path):
            pix = QPixmap(img_path)
            pix = pix.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("🍵")
            icon_lbl.setStyleSheet("font-size: 50px;")
            
        card_layout.addWidget(icon_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addSpacing(10)
        
        # Name
        name_lbl = QLabel(tea.name)
        name_lbl.setStyleSheet("font-weight: 700; font-size: 16px;")
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setWordWrap(True)
        card_layout.addWidget(name_lbl)
        
        # Status
        is_unlocked = tea.unlock_level <= user_level
        
        if is_unlocked:
            status = QLabel("Unlocked")
            status.setStyleSheet(f"color: {self.c['accent']}; font-weight: 600; font-size: 13px;")
        else:
            status = QLabel(f"Lvl {tea.unlock_level}")
            status.setStyleSheet(f"color: {self.c['sub']}; font-weight: 600; font-size: 13px;")
            
            # Dim the card visuals for locked state
            op = QGraphicsOpacityEffect(icon_lbl)
            op.setOpacity(0.5)
            icon_lbl.setGraphicsEffect(op)
            
            name_lbl.setStyleSheet(name_lbl.styleSheet() + f"color: {self.c['sub']};")
            
        status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(status)
        
        # Make clickable if unlocked
        if tea.unlock_level <= user_level:
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda e, t=tea.id: self.on_tea_card_clicked(t)

        return card

    def on_tea_card_clicked(self, tea_id):
        # Update selector
        self.tea_selector.setTea(tea_id)
        # update_tea_selection_visuals will be called by signal from selector
            
    def update_tea_selection_visuals(self):
        current_id = self.tea_selector.current_tea_id
        
        for tea_id, card in self.tea_cards.items():
            if tea_id == current_id:
                # Selected State
                card.setStyleSheet(f"""
                    QFrame.tea-card {{
                        background-color: {self.c['card']};
                        border-radius: 12px;
                        border: 2px solid {self.c['accent']};
                    }}
                """)
                # Optional: Add a "Selected" badge if we wanted, but border is good for now
            else:
                # Normal State - Reset style
                card.setStyleSheet(f"""
                    QFrame.tea-card {{
                        background-color: {self.c['card']};
                        border-radius: 12px;
                        border: 1px solid {self.c['border']};
                    }}
                """)

    def setup_favorites_page(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        tab.setLayout(layout)
        
        # Header
        header_layout = QHBoxLayout()
        title_lbl = QLabel("Favorite Tea Flavors")
        title_lbl.setStyleSheet("font-size: 20px; font-weight: bold;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        
        save_btn = QPushButton("+ Save Current")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_current_as_favorite)
        header_layout.addWidget(save_btn)
        
        layout.addLayout(header_layout)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.favorites_content_layout = QVBoxLayout()
        self.favorites_content_layout.setSpacing(10)
        self.favorites_content_layout.setContentsMargins(0, 20, 0, 0)
        self.favorites_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.setLayout(self.favorites_content_layout)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        self.stack.addWidget(tab)
        
    def refresh_favorites_list(self):
        # Clear existing
        while self.favorites_content_layout.count():
            item = self.favorites_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        favorites = manager.get_favorites()
        
        if not favorites:
            lbl = QLabel("No favorite configurations saved yet.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {self.c['sub']}; font-size: 14px; margin-top: 50px;")
            self.favorites_content_layout.addWidget(lbl)
            return

        for i, fav in enumerate(favorites):
            card = QFrame()
            card.setProperty("class", "tea-card")
            card_layout = QHBoxLayout()
            card_layout.setContentsMargins(15, 12, 15, 12)
            card_layout.setSpacing(15)
            card.setLayout(card_layout)
            
            # Tea Icon placeholder?
            tea_id = fav.get("flavor_id", "sencha")
            tea = TEAS.get(tea_id)
            tea_name = tea.name if tea else tea_id.title()
            
            # Text Info
            info_layout = QVBoxLayout()
            
            task_name = fav.get("task_name", "Unnamed Task")
            task_lbl = QLabel(task_name)
            task_lbl.setStyleSheet("font-weight: 600; font-size: 15px;")
            
            details = f"🍵 {tea_name}  •  🔥 {fav['temperature']}º  •  ⏱️ {int(fav['prep_time']/60)}/{int(fav['brew_time']/60)}m"
            if fav.get("cycles", 1) > 1:
                details += f"  •  x{fav['cycles']}"
                
            details_lbl = QLabel(details)
            details_lbl.setStyleSheet(f"color: {self.c['sub']}; font-size: 12px;")
            
            info_layout.addWidget(task_lbl)
            info_layout.addWidget(details_lbl)
            
            card_layout.addLayout(info_layout, stretch=1)
            
            # Buttons
            load_btn = QPushButton("Load")
            load_btn.setFixedSize(60, 30)
            load_btn.setStyleSheet(f"background-color: {self.c['card']}; border: 1px solid {self.c['accent']}; color: {self.c['accent']}; padding: 0;")
            load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            load_btn.clicked.connect(lambda checked, idx=i: self.load_favorite(idx))
            
            del_btn = QPushButton("Delete")
            del_btn.setFixedSize(60, 30)
            del_btn.setStyleSheet(f"background-color: {self.c['card']}; border: 1px solid #e06c75; color: #e06c75; padding: 0; font-size: 11px;")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked, idx=i: self.delete_favorite(idx))
            
            card_layout.addWidget(load_btn)
            card_layout.addWidget(del_btn)
            
            self.favorites_content_layout.addWidget(card)

    def save_current_as_favorite(self):
        flavor_id = self.tea_combo.itemData(self.tea_combo.currentIndex())
        config = {
            "flavor_id": flavor_id,
            "task_name": self.task_name_input.text(),
            "temperature": self.temp_slider.value(),
            "prep_time": self.prep_time_spin.value() * 60,
            "brew_time": self.brew_time_spin.value() * 60,
            "cycles": self.cycles_spin.value()
        }
        manager.add_favorite(config)
        self.refresh_favorites_list()
        
    def load_favorite(self, index):
        favorites = manager.get_favorites()
        if 0 <= index < len(favorites):
            conf = favorites[index]
            self.task_name_input.setText(conf["task_name"])
            self.temp_slider.setValue(conf["temperature"])
            self.update_temp_label(conf["temperature"])
            self.prep_time_spin.setValue(int(conf["prep_time"] / 60))
            self.brew_time_spin.setValue(int(conf["brew_time"] / 60))
            self.cycles_spin.setValue(int(conf.get("cycles", 1)))
            
            idx = self.tea_combo.findData(conf["flavor_id"])
            if idx >= 0:
                self.tea_combo.setCurrentIndex(idx)
            
            # Persist immediately as current session
            manager.set_current_tea(
                flavor_id=conf.get("flavor_id", "sencha"),
                task_name=conf.get("task_name", "Unnamed Task"),
                temperature=conf.get("temperature", 80),
                prep_time=conf.get("prep_time", 1500),
                brew_time=conf.get("brew_time", 300),
                cycles=conf.get("cycles", 1)
            )
            tea_timer.stop()
                
            self.switch_tab(0)
            
    def delete_favorite(self, index):
        manager.remove_favorite(index)
        self.refresh_favorites_list()

    def setup_history_page(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        tab.setLayout(layout)
        
        # Header
        header_lbl = QLabel("Past 30 Days")
        header_lbl.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header_lbl)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        self.history_content_layout = QVBoxLayout()
        self.history_content_layout.setSpacing(10)
        self.history_content_layout.setContentsMargins(0, 0, 0, 0)
        self.history_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content.setLayout(self.history_content_layout)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        
        self.stack.addWidget(tab)

    def refresh_history_list(self):
        # Clear existing items
        while self.history_content_layout.count():
            item = self.history_content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        history = manager.config.get("tea_history", [])
        
        if not history:
            lbl = QLabel("No tea preparations recorded yet.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(f"color: {self.c['sub']}; font-size: 14px; margin-top: 50px;")
            self.history_content_layout.addWidget(lbl)
            return

        for entry in history:
            card = QFrame()
            card.setProperty("class", "tea-card")
            card_layout = QHBoxLayout()
            card_layout.setContentsMargins(15, 12, 15, 12)
            card_layout.setSpacing(15)
            card.setLayout(card_layout)
            
            # Data Extraction
            try:
                dt = datetime.fromisoformat(entry["timestamp"])
                date_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                date_str = "Unknown Date"
            
            flavor_id = entry.get("flavor_id", "")
            tea = TEAS.get(flavor_id)
            tea_name = tea.name if tea else flavor_id.title()
            
            temp = entry.get('temperature', '?')
            level = entry.get('user_level', '?')
            
            # 1. Date (Monospace, Subtler)
            date_lbl = QLabel(date_str)
            date_lbl.setStyleSheet(f"color: {self.c['sub']}; font-family: monospace; font-size: 12px;")
            
            # 2. Task Name (Prominent)
            task_lbl = QLabel(entry.get("task_name", "Unknown Task"))
            task_lbl.setStyleSheet("font-weight: 600; font-size: 14px;")
            
            # 3. Tea & Stats (Right Aligned)
            tea_lbl = QLabel(f"🍵 {tea_name}")
            tea_lbl.setStyleSheet(f"color: {self.c['accent']}; font-weight: 500;")
            
            prep_min = int(entry.get('prep_time', 0) / 60)
            brew_min = int(entry.get('brew_time', 0) / 60)
            
            stats_lbl = QLabel(f"🔥 {temp}º   Chef Lvl {level}   ⏱️ {prep_min}m / {brew_min}m")
            stats_lbl.setStyleSheet(f"color: {self.c['sub']}; font-size: 12px;")
            
            # Layout Assembly
            card_layout.addWidget(date_lbl)
            card_layout.addWidget(task_lbl, stretch=1) # Task takes available space
            card_layout.addWidget(tea_lbl)
            card_layout.addWidget(stats_lbl)
            
            self.history_content_layout.addWidget(card)
    def update_temp_label(self, value):
        self.temp_label.setText(f"{value}º")

    def load_settings(self):
        conf = manager.get_current_tea()
        self.task_name_input.setText(conf["task_name"])
        self.temp_slider.setValue(conf["temperature"])
        self.update_temp_label(conf["temperature"])
        self.prep_time_spin.setValue(int(conf["prep_time"] / 60))
        self.brew_time_spin.setValue(int(conf["brew_time"] / 60))
        self.cycles_spin.setValue(int(conf.get("cycles", 1)))
        
        # Reload history (hacky but works for now as dialog is recreated usually)
        # Actually standard practice is to refresh UI on open, but here we just construct initially. 
        # If we wanted live refresh when tab clicked, we'd move this logic to switch_tab or a view event.
        # But history changes only when timer finishes (user outside dialog), so it's fine.
        if hasattr(self, 'history_content_layout'):
             self.refresh_history_list()
        
        if hasattr(self, 'favorites_content_layout'):
             self.refresh_favorites_list()
        
        progress = manager.get_progress()
        # available = get_available_teas(progress["level"])
        # self.tea_combo.clear()
        
        # current_idx = 0
        # for i, tea in enumerate(available):
        #     self.tea_combo.addItem(tea.name, tea.id)
        #     if tea.id == conf["flavor_id"]:
        #         current_idx = i
        # self.tea_combo.setCurrentIndex(current_idx)
        
        if conf["flavor_id"]:
            self.tea_selector.setTea(conf["flavor_id"])
            
        # Load UI Settings
        ui_settings = manager.get_ui_settings()
        
        # Opacity
        opacity = ui_settings.get("widget_opacity", 100)
        if hasattr(self, 'opacity_slider'):
            self.opacity_slider.setValue(opacity)
            self.opacity_label.setText(f"{opacity}%")
            
        # Glassmorphism
        # glass = ui_settings.get("widget_glass", False) # Legacy read, not needed for UI state
        glass_strength = ui_settings.get("widget_glass_strength", 0)
            
        if hasattr(self, 'glass_slider'):
            self.glass_slider.setValue(glass_strength)
            # self.glass_slider.setEnabled(glass) # Always enabled now
            
        # Size
        size = ui_settings.get("widget_size", "big")
        if hasattr(self, 'size_buttons') and size in self.size_buttons:
            self.size_buttons[size].setChecked(True)
            self.update_size_selection_style()

        # Notifications
        silence = ui_settings.get("silence_notifications", False)
        if hasattr(self, 'silence_check'):
            self.silence_check.setChecked(silence)
            
        # Reviewer Overlay Settings
        rev_opacity = ui_settings.get("reviewer_opacity", 100)
        rev_blur = ui_settings.get("reviewer_blur", 0)
        
        if hasattr(self, 'reviewer_opacity_slider'):
            self.reviewer_opacity_slider.setValue(rev_opacity)
            self.update_reviewer_opacity_label(rev_opacity)
            
        if hasattr(self, 'reviewer_blur_slider'):
            self.reviewer_blur_slider.setValue(rev_blur)
            self.update_reviewer_blur_label(rev_blur)

        # Minimal Mode Default
        rev_minimal = ui_settings.get("reviewer_minimal_mode_default", False)
        if hasattr(self, 'reviewer_minimal_check'):
            self.reviewer_minimal_check.setChecked(rev_minimal)

    def update_size_selection_style(self):
        for btn in self.size_group.buttons():
            if btn.isChecked():
                btn.title_lbl.setStyleSheet("font-weight: 600; border: none; background: transparent; color: " + self.c['btn_txt'] + ";")
                btn.sub_lbl.setStyleSheet("font-size: 10px; border: none; background: transparent; color: " + self.c['btn_txt'] + ";")
            else:
                btn.title_lbl.setStyleSheet("font-weight: 600; border: none; background: transparent; color: " + self.c['fg'] + ";")
                btn.sub_lbl.setStyleSheet("font-size: 10px; border: none; background: transparent; color: " + self.c['sub'] + ";")

    def save_and_close(self):
        # Validate Task Name
        task_name = self.task_name_input.text()
        if len(task_name) >= 15:
            # Modern validation message
            dlg = ModernWarningDialog("Task name must be less than 15 characters.", self)
            dlg.exec()
            return

        # Save Current Tea Config
        current_flavor = self.tea_selector.current_tea_id
        
        manager.set_current_tea(
            flavor_id=current_flavor,
            task_name=task_name,
            temperature=self.temp_slider.value(),
            prep_time=self.prep_time_spin.value() * 60,
            brew_time=self.brew_time_spin.value() * 60,
            cycles=self.cycles_spin.value()
        )
        
        # Save UI Settings
        if hasattr(self, 'selected_pos'):
            manager.set_ui_setting("reviewer_position", self.selected_pos)
            
        # Save Tea Room Widget Settings (Legacy/Main Menu)
        if hasattr(self, 'opacity_slider'):
            manager.set_ui_setting("widget_opacity", self.opacity_slider.value())
            
        if hasattr(self, 'glass_slider'):
            strength = self.glass_slider.value()
            manager.set_ui_setting("widget_glass_strength", strength)
            manager.set_ui_setting("widget_glass", strength > 0)
            
        # Save Reviewer Overlay Settings
        if hasattr(self, 'reviewer_opacity_slider'):
            manager.set_ui_setting("reviewer_opacity", self.reviewer_opacity_slider.value())
            
        if hasattr(self, 'reviewer_blur_slider'):
            manager.set_ui_setting("reviewer_blur", self.reviewer_blur_slider.value())

        if hasattr(self, 'reviewer_minimal_check'):
            manager.set_ui_setting("reviewer_minimal_mode_default", self.reviewer_minimal_check.isChecked())
            
        # Find selected size
        if hasattr(self, 'size_buttons'):
            for size_id, btn in self.size_buttons.items():
                if btn.isChecked():
                    manager.set_ui_setting("widget_size", size_id)
                    break

        if hasattr(self, 'silence_check'):
            manager.set_ui_setting("silence_notifications", self.silence_check.isChecked())
            
        tea_timer.stop() # Reset timer to apply new settings
        self.accept()

    def update_reviewer_opacity_label(self, value):
        self.reviewer_opacity_label.setText(f"{value}%")
        
    def update_reviewer_blur_label(self, value):
        self.reviewer_blur_label.setText(f"{value}px")
