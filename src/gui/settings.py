from aqt.qt import *
from aqt import mw
from aqt.theme import theme_manager
import os
from ..config import manager
from ..tea_data import TEAS, get_available_teas, TeaFlavor
from ..logic.timer import tea_timer
from datetime import datetime

class SenchadoSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Komori Timer")
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

        # Nav Bar
        self.header_container = QWidget()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 20, 0, 0)
        self.header_container.setLayout(header_layout)
        
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

        # Connect combo box change to sync selection with Level page
        self.tea_combo.currentIndexChanged.connect(self.update_tea_selection_visuals)
        # Initial visual update
        self.update_tea_selection_visuals()

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
        self.tea_combo = QComboBox()
        card_layout.addRow(self.create_label("Select Tea"), self.tea_combo)

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
        pos_title = QLabel("Tea Room configurations")
        pos_title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px; margin-top: 10px;")
        main_layout.addWidget(pos_title)
        
        pos_card = QFrame()
        pos_card.setProperty("class", "tea-card")
        pos_card_layout = QVBoxLayout()
        pos_card_layout.setContentsMargins(30, 30, 30, 30)
        pos_card_layout.setSpacing(20)
        pos_card.setLayout(pos_card_layout)
        
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
        main_layout.addWidget(pos_card)

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
        
        for i, tea in enumerate(sorted_teas):
            row = i // 2
            col = i % 2
            
            card = self.create_tea_card(tea, progress['level'])
            self.tea_cards[tea.id] = card
            grid.addWidget(card, row, col)
            
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
        
        addon_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        # Find index in combo box
        index = self.tea_combo.findData(tea_id)
        if index >= 0:
            self.tea_combo.setCurrentIndex(index)
            # update_tea_selection_visuals will be called by signal
            
    def update_tea_selection_visuals(self):
        current_id = self.tea_combo.itemData(self.tea_combo.currentIndex())
        
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
        available = get_available_teas(progress["level"])
        self.tea_combo.clear()
        
        current_idx = 0
        for i, tea in enumerate(available):
            self.tea_combo.addItem(tea.name, tea.id)
            if tea.id == conf["flavor_id"]:
                current_idx = i
        self.tea_combo.setCurrentIndex(current_idx)

    def save_and_close(self):
        # Save Current Tea Config
        current_flavor = self.tea_combo.itemData(self.tea_combo.currentIndex())
        
        manager.set_current_tea(
            flavor_id=current_flavor,
            task_name=self.task_name_input.text(),
            temperature=self.temp_slider.value(),
            prep_time=self.prep_time_spin.value() * 60,
            brew_time=self.brew_time_spin.value() * 60,
            cycles=self.cycles_spin.value()
        )
        
        # Save UI Settings
        if hasattr(self, 'selected_pos'):
            manager.set_ui_setting("reviewer_position", self.selected_pos)
            
        tea_timer.stop() # Reset timer to apply new settings
        self.accept()
