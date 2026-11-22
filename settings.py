from aqt.qt import *
from aqt import mw
from aqt.theme import theme_manager
from aqt.webview import AnkiWebView
import os
import webbrowser
import importlib
from copy import deepcopy
from .config import manager
from .tea_data import TEAS, TeaFlavor
from .timer import tea_timer
from . import bento_integration
from datetime import datetime

try:
    from PyQt6.QtCore import QRectF, QPointF, QSize, QPropertyAnimation, QEasingCurve, QByteArray, pyqtProperty
except ImportError:
    from PyQt5.QtCore import QRectF, QPointF, QSize, QPropertyAnimation, QEasingCurve, QByteArray, pyqtProperty

try:
    from PyQt6.QtSvg import QSvgRenderer
except ImportError:
    from PyQt5.QtSvg import QSvgRenderer

_ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
_lucide_icon_cache = {}


def load_lucide_icon(name: str, color: str, size: int = 20) -> QPixmap:
    """Renders a lucide-static SVG (icons/lucide-<name>.svg) tinted to `color`.

    Rendered at a higher pixel density (with devicePixelRatio set) so the
    icon stays crisp on HiDPI/Retina screens instead of looking blurry.
    """
    cache_key = (name, color, size)
    if cache_key in _lucide_icon_cache:
        return _lucide_icon_cache[cache_key]

    dpr = mw.devicePixelRatioF() if hasattr(mw, "devicePixelRatioF") else 1.0
    dpr = max(dpr, 2.0)  # always render at least @2x so it's sharp even if reported dpr is 1
    pixel_size = max(1, int(size * dpr))

    pixmap = QPixmap(pixel_size, pixel_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    svg_path = os.path.join(_ICONS_DIR, f"lucide-{name}.svg")
    if os.path.exists(svg_path):
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_data = f.read().replace("currentColor", color)
        renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
        if renderer.isValid():
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            renderer.render(painter)
            painter.end()

    pixmap.setDevicePixelRatio(dpr)
    _lucide_icon_cache[cache_key] = pixmap
    return pixmap


def _contrast_text_color(hex_color: str) -> str:
    c = hex_color.lstrip('#')
    r, g, b = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) if len(c) in (6, 8) else (255, 255, 255)
    luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    return "#111111" if luminance > 0.56 else "#ffffff"


def _apply_swatch_style(button, color_str):
    text_color = _contrast_text_color(color_str)
    button.setText(color_str.upper())
    button.setStyleSheet(
        f"QPushButton#colorSwatchButton {{"
        f"  background-color: {color_str};"
        f"  color: {text_color};"
        f"  font-weight: bold;"
        f"  font-size: 13px;"
        f"  border: 1px solid rgba(0,0,0,0.15);"
        f"  border-radius: 12px;"
        f"  padding: 6px 16px;"
        f"}}"
        f"QPushButton#colorSwatchButton:hover {{"
        f"  border: 1px solid rgba(0,0,0,0.35);"
        f"}}"
    )


def create_color_button(initial_color: str, parent: QWidget) -> QPushButton:
    button = QPushButton(parent)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setObjectName("colorSwatchButton")
    _apply_swatch_style(button, initial_color)
    return button


class OnigiriStyleSlider(QSlider):
    """Rounded, segmented pill slider matching Onigiri's (1011095603) slider design.

    Ported from settings/_widgets.py's MainBackgroundEffectSlider, minus the
    locked-state affordance which this dialog's sliders never need.
    """

    def __init__(self, accent_color, track_color, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self._accent_color = QColor(accent_color)
        self._track_color = QColor(track_color)
        self._handle_color = QColor("#ffffff")
        self.setFixedHeight(30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

    def wheelEvent(self, event):
        event.ignore()

    def setColors(self, accent_color, track_color):
        self._accent_color = QColor(accent_color)
        self._track_color = QColor(track_color)
        self.update()

    def sizeHint(self):
        hint = super().sizeHint()
        return QSize(max(220, hint.width()), 30)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        paint_pad = 4
        track_height = 22
        handle_radius = (track_height / 2) - 3
        track_left = paint_pad
        track_right = max(track_left + track_height + 1, self.width() - paint_pad)
        track_width = track_right - track_left
        track_top = (self.height() - track_height) / 2
        track_rect = QRectF(track_left, track_top, track_width, track_height)
        handle_min_x = track_rect.left() + (track_height / 2)
        handle_max_x = track_rect.right() - (track_height / 2)

        value_range = max(1, self.maximum() - self.minimum())
        progress = max(0.0, min(1.0, (self.value() - self.minimum()) / value_range))
        handle_x = handle_min_x + (handle_max_x - handle_min_x) * progress

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._track_color))
        painter.drawRoundedRect(track_rect, track_height / 2, track_height / 2)

        if progress <= 0.0:
            active_width = 0.0
        elif progress >= 1.0:
            active_width = track_width
        else:
            active_width = min(track_width, max(0.0, handle_x + handle_radius - track_left))
        if active_width > 0:
            active_rect = QRectF(track_left, track_top, active_width, track_height)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._accent_color))
            painter.drawRoundedRect(active_rect, track_height / 2, track_height / 2)

        for step in range(1, 6):
            x = track_left + track_width * step / 6
            if x <= track_left + active_width:
                continue
            mark_color = QColor(self._track_color).darker(120)
            mark_color.setAlpha(95)
            painter.setPen(QPen(mark_color, 1))
            painter.drawLine(QPointF(x, track_top + 4), QPointF(x, track_top + track_height - 4))

        handle_rect = QRectF(
            handle_x - handle_radius,
            (self.height() / 2) - handle_radius,
            handle_radius * 2,
            handle_radius * 2,
        )
        painter.setBrush(QBrush(self._handle_color))
        painter.setPen(QPen(self._accent_color, 3))
        painter.drawEllipse(handle_rect)


class FixedSpinBox(QSpinBox):
    """A QSpinBox with no up/down arrows and no accidental wheel-scroll edits.

    The value is still directly editable by clicking in and typing -
    only the spinner buttons and scroll-to-change are removed.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

    def wheelEvent(self, event):
        event.ignore()


class _SpinUnitLabel(QLabel):
    """A colored unit suffix (e.g. "min") pinned to a spin box's right edge.

    QSpinBox's built-in suffix sits right after the digits and shifts as the
    number's width changes; this instead floats fixed at the right edge so
    the number stays freely editable underneath it.
    """

    def __init__(self, spin_box, text, color):
        super().__init__(text, spin_box)
        self.setStyleSheet(f"color: {color}; font-weight: 600; background: transparent; border: none;")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._spin_box = spin_box
        self.adjustSize()
        spin_box.installEventFilter(self)
        self._reposition()

    def eventFilter(self, obj, event):
        if obj is self._spin_box and event.type() == QEvent.Type.Resize:
            self._reposition()
        return super().eventFilter(obj, event)

    def _reposition(self):
        margin = 14
        x = self._spin_box.width() - self.width() - margin
        y = (self._spin_box.height() - self.height()) // 2
        self.move(max(0, x), y)


def attach_unit_label(spin_box, text, color, reserved_px=60):
    """Removes the spin box's built-in suffix and pins a colored unit label
    to its right edge instead, reserving room so digits never run under it."""
    spin_box.setSuffix("")
    spin_box.setStyleSheet(f"QSpinBox {{ padding-right: {reserved_px}px; }}")
    return _SpinUnitLabel(spin_box, text, color)


class AnimatedToggleButton(QAbstractButton):
    """Modern toggle switch with a gooey drag animation, ported from Onigiri
    (1011095603)'s settings/_widgets.py, minus its locked/lock-icon state."""

    def __init__(self, parent=None, accent_color="#3F6D49", track_color_off=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.accent_color = QColor(accent_color)
        if track_color_off is not None:
            self.track_color_off = QColor(track_color_off)
        else:
            self.track_color_off = QColor("#4b5563") if theme_manager.night_mode else QColor("#d1d5db")
        self.thumb_color = QColor("#ffffff")

        self.setFixedSize(50, 30)
        self._thumb_x_pos = 0.0
        self._gooey_amount = 0.0
        self._gooey_direction = 1.0

        self.animation = QPropertyAnimation(self, b"thumb_x_pos", self)
        self.animation.setDuration(180)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.gooey_animation = QPropertyAnimation(self, b"gooey_amount", self)
        self.gooey_animation.setDuration(230)
        self.gooey_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._start_animation)

    def _track_rect(self):
        return QRectF(3, 3, self.width() - 6, self.height() - 6)

    def _checked_thumb_position(self, checked=None):
        if checked is None:
            checked = self.isChecked()
        track = self._track_rect()
        thumb_r = (track.height() / 2.0) - 3
        if checked:
            return float(track.right() - 3 - (thumb_r * 2))
        return float(track.left() + 3)

    def _sync_thumb_to_checked(self):
        self._thumb_x_pos = self._checked_thumb_position()
        self.update()

    def setChecked(self, checked):
        super().setChecked(checked)
        if self.signalsBlocked() or not self.isVisible():
            self.animation.stop()
            self.gooey_animation.stop()
            self._gooey_amount = 0.0
            self._sync_thumb_to_checked()

    @pyqtProperty(float)
    def thumb_x_pos(self):
        return self._thumb_x_pos

    @thumb_x_pos.setter
    def thumb_x_pos(self, value):
        self._thumb_x_pos = value
        self.update()

    @pyqtProperty(float)
    def gooey_amount(self):
        return self._gooey_amount

    @gooey_amount.setter
    def gooey_amount(self, value):
        self._gooey_amount = max(0.0, min(1.0, float(value)))
        self.update()

    def _start_animation(self, checked):
        end_pos = self._checked_thumb_position(checked)
        self._gooey_direction = 1.0 if checked else -1.0
        self.animation.setStartValue(self.thumb_x_pos)
        self.animation.setEndValue(float(end_pos))
        self.animation.start()
        self.gooey_animation.stop()
        self.gooey_animation.setStartValue(1.0)
        self.gooey_animation.setEndValue(0.0)
        self.gooey_animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        track_rect = self._track_rect()
        radius = track_rect.height() / 2.0
        painter.setPen(Qt.PenStyle.NoPen)
        track_color = self.accent_color if self.isChecked() else self.track_color_off
        painter.setBrush(track_color)
        painter.drawRoundedRect(track_rect, radius, radius)
        thumb_r = radius - 3
        thumb_center = QPointF(self._thumb_x_pos + thumb_r, track_rect.center().y())
        if self._gooey_amount > 0.01:
            gooey_path = QPainterPath()
            stretch = (3.5 + 4.5 * self._gooey_amount) * self._gooey_direction
            min_center_x = track_rect.left() + 3 + thumb_r
            max_center_x = track_rect.right() - 3 - thumb_r
            trail_x = max(min_center_x, min(max_center_x, thumb_center.x() - stretch))
            trail_center = QPointF(trail_x, thumb_center.y())
            trail_r = max(thumb_r * 0.56, thumb_r * (0.70 - 0.12 * self._gooey_amount))
            gooey_path.addEllipse(thumb_center, thumb_r + 0.8 * self._gooey_amount, thumb_r)
            gooey_path.addEllipse(trail_center, trail_r, trail_r * 0.94)
            bridge_left = min(thumb_center.x(), trail_center.x())
            bridge_width = abs(thumb_center.x() - trail_center.x())
            gooey_path.addRoundedRect(
                QRectF(bridge_left, track_rect.center().y() - trail_r, bridge_width, trail_r * 2),
                trail_r,
                trail_r,
            )
            painter.setBrush(self.thumb_color)
            painter.drawPath(gooey_path)
        painter.setBrush(self.thumb_color)
        painter.drawEllipse(thumb_center, thumb_r, thumb_r)

    def showEvent(self, event):
        super().showEvent(event)
        self._sync_thumb_to_checked()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_thumb_to_checked()


class IconExpandButton(QPushButton):
    """Icon-only pill button that expands on hover to reveal its label.

    Collapsed it's just a circular icon; on hover it grows and the label
    fades in, like a tooltip built into the button itself.
    """

    def __init__(self, icon_name, label, bg, fg, hover_bg, size=40, parent=None):
        super().__init__(parent)
        self._label = label
        self._collapsed_w = size
        self._icon_pixmap = load_lucide_icon(icon_name, fg, 18)
        self.setIcon(QIcon(self._icon_pixmap))
        self.setIconSize(QSize(18, 18))
        self.setFixedHeight(size)
        self.setMinimumWidth(size)
        self.setMaximumWidth(size)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {fg};
                border: none;
                border-radius: {size // 2}px;
                font-weight: 600;
                font-size: 13px;
                padding: 0px 12px;
                text-align: right;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
            }}
        """)

        fm = self.fontMetrics()
        self._expanded_w = size + fm.horizontalAdvance(label) + 14

        self._anim = QPropertyAnimation(self, b"minimumWidth", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim2 = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim2.setDuration(150)
        self._anim2.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _animate_to(self, width):
        for anim in (self._anim, self._anim2):
            anim.stop()
            anim.setStartValue(self.width())
            anim.setEndValue(width)
            anim.start()

    def enterEvent(self, event):
        self.setText(self._label + "  ")
        self._animate_to(self._expanded_w)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setText("")
        self._animate_to(self._collapsed_w)
        super().leaveEvent(event)


class TeaOptionButton(QFrame):
    clicked = pyqtSignal(str) # tea_id

    def __init__(self, tea_id, locked=False, parent=None):
        super().__init__(parent)
        self.tea_id = tea_id
        self.locked = locked
        self.setCursor(Qt.CursorShape.ArrowCursor if locked else Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

    def mouseReleaseEvent(self, event):
        if not self.locked and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit(self.tea_id)
        super().mouseReleaseEvent(event)

class TeaSelectionMenu(QDialog):
    """A dedicated floating dialog listing every tea, locked ones dimmed.

    Selecting a row just previews the choice (highlighted); nothing is
    applied until Save is pressed. Cancel/close/click-outside discards it.
    """

    def __init__(self, parent=None, colors=None, all_teas=None, current_tea_id=None, current_level=1, width=400):
        super().__init__(parent)
        # NoDropShadowWindowHint stops the OS from drawing its own shadow
        # around the true (rectangular) window bounds, which otherwise shows
        # through as a faint outline/hairline around our rounded card.
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.colors = colors or {}
        self.teas = all_teas or []
        self.current_level = current_level
        self.selected_tea_id = current_tea_id
        self.menu_width = width
        self._rows = [] # (TeaOptionButton, tea, locked)

        self.setup_ui()

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        accent = self.colors.get('accent', '#3F6D49')
        accent_rgb = tuple(int(accent.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
        muted = self.colors.get('sub', '#8F9E91')
        btn_bg = "#252925" if theme_manager.night_mode else "#3F6D49"
        btn_text = "#FFFFFF"
        btn_hover = "#3A3F39" if theme_manager.night_mode else "#4A7E54"

        # Main Container with shadow/border
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors.get('card', '#FFFFFF')};
                border: none;
                border-radius: 22px;
            }}
        """)
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(10, 10, 10, 14)
        container_layout.setSpacing(10)
        container.setLayout(container_layout)

        addon_root = os.path.dirname(os.path.abspath(__file__))

        # Header with Close Button
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(14, 10, 10, 4)

        title = QLabel("Select a Tea below")
        title.setStyleSheet(f"font-weight: 700; color: {self.colors.get('fg', '#000')}; font-size: 18px; border: none; background: transparent;")

        header_layout.addStretch()
        header_layout.addWidget(title)
        header_layout.addStretch()

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
        # The viewport paints its own opaque background rectangle by default,
        # which squares off the container's rounded bottom corners unless
        # it's made transparent too (setting it only on QScrollArea itself
        # doesn't reach the internal viewport widget).
        scroll.viewport().setStyleSheet("background: transparent;")
        scroll.viewport().setAutoFillBackground(False)

        # List Widget
        list_widget = QWidget()
        list_widget.setStyleSheet("background: transparent;")

        list_layout = QVBoxLayout()
        list_layout.setSpacing(8)
        list_layout.setContentsMargins(4, 4, 4, 4)
        list_widget.setLayout(list_layout)

        for tea in self.teas:
            locked = tea.unlock_level > self.current_level

            btn = TeaOptionButton(tea.id, locked=locked)
            btn.setFixedHeight(64)

            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(10, 8, 14, 8)
            btn_layout.setSpacing(14)
            btn.setLayout(btn_layout)

            # Icon, in a soft accent-tinted circular chip like the main selector
            icon_chip = QLabel()
            icon_chip.setFixedSize(44, 44)
            icon_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip_bg = f"rgba(140, 140, 140, 30)" if locked else f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 30)"
            icon_chip.setStyleSheet(f"border: none; border-radius: 22px; background-color: {chip_bg};")
            icon_chip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

            if locked:
                icon_lbl = QLabel(icon_chip)
                icon_lbl.setFixedSize(20, 20)
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_lbl.setStyleSheet("border: none; background: transparent;")
                icon_lbl.setPixmap(load_lucide_icon("lock", muted, 20))
                icon_lbl.move(12, 12)
            else:
                icon_lbl = QLabel(icon_chip)
                icon_lbl.setFixedSize(32, 32)
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                icon_lbl.setStyleSheet("border: none; background: transparent;")
                icon_lbl.move(6, 6)
                img_path = os.path.join(addon_root, "tea_gallery", f"{tea.id}.png")
                if os.path.exists(img_path):
                    pix = QPixmap(img_path)
                    pix = pix.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    icon_lbl.setPixmap(pix)
                else:
                    icon_lbl.setText("🍵")

            # Text: name + subtitle (description, or unlock requirement if locked)
            text_layout = QVBoxLayout()
            text_layout.setSpacing(2)

            name_color = muted if locked else self.colors.get('fg', '#000')
            name_lbl = QLabel(tea.name)
            name_lbl.setStyleSheet(f"border: none; background: transparent; font-weight: 600; font-size: 15px; color: {name_color};")
            name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            text_layout.addWidget(name_lbl)

            subtitle = f"Unlocks at Level {tea.unlock_level}" if locked else tea.description
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(f"border: none; background: transparent; font-size: 12px; color: {muted};")
            sub_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            text_layout.addWidget(sub_lbl)

            btn_layout.addWidget(icon_chip)
            btn_layout.addLayout(text_layout, 1)

            if not locked:
                check_lbl = QLabel()
                check_lbl.setStyleSheet("border: none; background: transparent;")
                check_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
                btn_layout.addWidget(check_lbl)
                btn.check_lbl = check_lbl
                btn.clicked.connect(self.select_tea)
            else:
                dim = QGraphicsOpacityEffect(btn)
                dim.setOpacity(0.45)
                btn.setGraphicsEffect(dim)

            list_layout.addWidget(btn)
            self._rows.append((btn, tea, locked))

        list_layout.addStretch()

        scroll.setWidget(list_widget)
        container_layout.addWidget(scroll, 1)

        # Footer: Cancel / Save
        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(14, 6, 10, 0)
        footer_layout.addStretch()
        cancel_btn = IconExpandButton("x", "Cancel", btn_bg, btn_text, btn_hover)
        cancel_btn.clicked.connect(self.reject)
        save_btn = IconExpandButton("check", "Save", btn_bg, btn_text, btn_hover)
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        footer_layout.addWidget(cancel_btn)
        footer_layout.addWidget(save_btn)
        footer_layout.addStretch()
        container_layout.addLayout(footer_layout)

        layout.addWidget(container) # Add container to main layout

        self._refresh_row_styles(accent, accent_rgb)

        # A dedicated floating dialog: fixed, generous size regardless of the
        # field width, but never larger than the screen it opens on.
        target_w = max(self.menu_width, 460)
        target_h = 560
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            target_w = min(target_w, screen_geo.width() - 40)
            target_h = min(target_h, screen_geo.height() - 60)
        self.setFixedWidth(target_w)
        self.setFixedHeight(target_h)

        # Install event filter on App to detect outside clicks (since we are not a real Popup anymore)
        mw.app.installEventFilter(self)

    def _refresh_row_styles(self, accent, accent_rgb):
        for btn, tea, locked in self._rows:
            if locked:
                border_color = "transparent"
                bg_color = self.colors.get('bg', '#F0F0F0')
            else:
                is_selected = (tea.id == self.selected_tea_id)
                if is_selected:
                    bg_color = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 35)"
                    border_color = accent
                else:
                    bg_color = self.colors.get('bg', '#F0F0F0')
                    border_color = "transparent"
                if hasattr(btn, "check_lbl"):
                    btn.check_lbl.setPixmap(load_lucide_icon("check", accent, 18) if is_selected else QPixmap())

            btn.setStyleSheet(f"""
                TeaOptionButton {{
                    background-color: {bg_color};
                    border: 1.5px solid {border_color};
                    border-radius: 18px;
                }}
                TeaOptionButton:hover {{
                    border: 1.5px solid {"transparent" if locked else accent};
                }}
            """)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            # Handle Qt6 vs Qt5
            if hasattr(event, "globalPosition"):
                pos = event.globalPosition().toPoint()
            else:
                pos = event.globalPos()

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
        accent = self.colors.get('accent', '#3F6D49')
        accent_rgb = tuple(int(accent.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
        self._refresh_row_styles(accent, accent_rgb)

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
                "accent": "#3F6D49", "btn_txt": "#FFFFFF"
            }
        else:
            self.c = {
                "bg": "#FAFAF5", "fg": "#2C3E2D", "border": "#D8DED0", 
                "accent": "#3F6D49", "btn_txt": "#FFFFFF"
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
        self.setFixedHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Ensure QFrame background works with stylesheets and transparency
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 45))
        self.setGraphicsEffect(shadow)

        self.setup_ui()

    def setColors(self, colors):
        self.colors = colors
        self.update_style()
        self._update_chevron()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 0, 18, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter) # Center vertically
        self.setLayout(layout)

        self.icon_chip = QLabel()
        self.icon_chip.setObjectName("tea_icon_chip")
        self.icon_chip.setFixedSize(36, 36)
        self.icon_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_chip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.icon_lbl = QLabel(self.icon_chip)
        self.icon_lbl.setFixedSize(26, 26)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.icon_lbl.move(5, 5)

        self.name_lbl = QLabel("Select Tea")
        self.name_lbl.setStyleSheet("font-weight: 600; font-size: 15px;")
        self.name_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.chevron = QLabel()
        self.chevron.setFixedSize(18, 18)
        self.chevron.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout.addWidget(self.icon_chip)
        layout.addSpacing(12)
        layout.addWidget(self.name_lbl)
        layout.addStretch()
        layout.addWidget(self.chevron)

    def _update_chevron(self, open=False):
        accent = self.colors.get('accent', '#3F6D49')
        icon_name = "chevron-up" if open else "chevron-down"
        self.chevron.setPixmap(load_lucide_icon(icon_name, accent, 18))

    def update_style(self):
        accent = self.colors.get('accent', '#3F6D49')
        accent_rgb = tuple(int(accent.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4))
        self.setStyleSheet(f"""
            TeaSelector {{
                background-color: {self.colors.get('card', '#FFFFFF')};
                border: 1.5px solid {self.colors.get('border', '#CCCCCC')};
                border-radius: 26px;
            }}
            TeaSelector:hover {{
                border: 1.5px solid {accent};
                background-color: rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 20);
            }}
            QLabel#tea_icon_chip {{
                background-color: rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 30);
                border-radius: 18px;
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
                pix = pix.scaled(26, 26, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
        progress = manager.get_progress()
        level = progress["level"]
        all_teas = list(TEAS.values())

        menu = TeaSelectionMenu(self, self.colors, all_teas, self.current_tea_id, current_level=level, width=self.width())

        # A dedicated floating dialog: center it over the settings window,
        # not anchored below the (now full-width) field.
        anchor = self.window() if self.window() else self
        anchor_geo = anchor.geometry()
        anchor_top_left = anchor.mapToGlobal(QPoint(0, 0)) if anchor is not self else self.mapToGlobal(QPoint(0, 0))
        center_x = anchor_top_left.x() + (anchor_geo.width() - menu.width()) // 2
        center_y = anchor_top_left.y() + (anchor_geo.height() - menu.height()) // 2

        # Clamp to screen
        screen = self.screen() if hasattr(self, "screen") else QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            center_x = max(screen_geo.left() + 10, min(center_x, screen_geo.right() - menu.width() - 10))
            center_y = max(screen_geo.top() + 10, min(center_y, screen_geo.bottom() - menu.height() - 10))

        menu.move(center_x, center_y)

        self._update_chevron(open=True)
        try:
            if menu.exec():
                if menu.selected_tea_id and menu.selected_tea_id != self.current_tea_id:
                    self.setTea(menu.selected_tea_id)
        finally:
            self._update_chevron(open=False)


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

# ─── Live Preview ────────────────────────────────────────────────────────────

# .senchado-widget is a square sized off widget_size (small/medium/big =
# 200/300/400px) with `margin: 20px auto` baked into main_widget.py's
# style_block, so unlike Global there's a size PER widget_size value rather
# than a per-view-mode dict of unrelated layouts.
_TEA_WIDGET_NATURAL_SIZES = {
    "small": (200, 240),
    "medium": (300, 340),
    "big": (400, 440),
}


class SenchadoWidgetPreview(QWidget):
    """Renders a live HTML preview of the Tea Room deck-browser widget.

    Player level/XP is real (there's nothing to preview there — it's not
    edited in this dialog), but the tea/task/appearance reflect this
    dialog's in-progress (unsaved) settings.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.preview_layout = QVBoxLayout(self)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)

        self.webview = None

        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self.refresh)
        self._last_data = (manager.get_progress(), manager.get_current_tea(), manager.get_ui_settings())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(120)

    def cleanup(self):
        """Release the embedded AnkiWebView before this widget is destroyed.

        AnkiWebView wraps a QWebEngineView; if it is left to be torn down
        implicitly during Python interpreter finalization (Anki quitting),
        Qt dereferences already-freed child widgets and segfaults. Cleaning
        it up explicitly on dialog close avoids that.
        """
        if getattr(self, "_resize_timer", None) is not None:
            self._resize_timer.stop()
        if getattr(self, "webview", None) is not None:
            if getattr(self, "webview", None):
                self.webview.cleanup()
            self.webview = None

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, "webview", None) is None:
            self.webview = AnkiWebView(title="senchado_preview", parent=self)
            self.webview.setMinimumSize(260, 300)
            self.webview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            self.webview.disable_zoom()
            try:
                self.webview.page().setBackgroundColor(QColor(0, 0, 0, 0))
            except Exception:
                pass
            self.preview_layout.addWidget(self.webview)
            self.refresh()

    def refresh(self, progress=None, tea_config=None, ui_settings=None):
        if progress is not None or tea_config is not None or ui_settings is not None:
            self._last_data = (progress, tea_config, ui_settings)
        progress, tea_config, ui_settings = self._last_data

        if not getattr(self, "webview", None):
            return

        # Deferred import: main_widget.py imports SenchadoSettings from this
        # same module, so importing it at module load time would be circular.
        main_widget = importlib.import_module(f"{__package__}.main_widget")
        is_dark = theme_manager.night_mode

        html_content = main_widget.generate_widget_html(
            progress=progress, tea_config=tea_config, ui_settings=ui_settings, is_dark=is_dark,
        )

        # Behind the widget: Onigiri's actual deck-browser wallpaper when the
        # integration is active, otherwise the same flat color as this dialog.
        settings_bg = "#181818" if is_dark else "#f7f7f7"
        card_bg = "#262925" if is_dark else "#FFFFFF"
        wallpaper = None
        if bento_integration.is_onigiri_detected():
            wallpaper = bento_integration.main_menu_wallpaper(is_dark)
        if not wallpaper:
            wallpaper = {"kind": "color", "color": settings_bg}

        if wallpaper["kind"] == "image":
            # Only apply the blur filter when actually blurring - even
            # `filter: blur(0px)` forces Chromium into a filter-effect
            # compositing path that can fringe/noise the rounded-corner clip.
            blur_css = f"filter: blur({wallpaper['blur_px']}px);" if wallpaper['blur_px'] > 0 else ""
            bg_layer_css = f"""
                background-color: {wallpaper['color']};
                background-image: url('{wallpaper['url']}');
                background-size: cover; background-position: center; background-repeat: no-repeat;
                {blur_css}
                opacity: {wallpaper['opacity']};
            """
        else:
            bg_layer_css = f"background-color: {wallpaper['color']}; opacity: 1;"

        base_w = ui_settings.get("manual_widget_width", 300)
        base_h = ui_settings.get("manual_widget_height", 300)
        natural_w = base_w + 40
        natural_h = base_h + 40

        panel_w = self.webview.width()
        panel_h = self.webview.height()
        if panel_w < 100 or panel_h < 100:
            panel_w, panel_h = 320, 400

        avail_w = panel_w - 40
        avail_h = panel_h - 40
        factor = min(1.0, avail_w / natural_w, avail_h / natural_h) * 0.94
        final_w = natural_w * factor + 2
        final_h = natural_h * factor + 2

        full_html = f"""
        <html><head><style>
            html {{ background-color: {settings_bg}; }}
            html, body {{ margin: 0; padding: 0; height: 100%; overflow: hidden; }}
            body {{
                position: relative;
                display: flex; align-items: center; justify-content: center;
                background-color: {card_bg};
                border-radius: 20px;
            }}
            #onigiri-bg-container {{
                position: absolute; inset: 0; z-index: 0;
                border-radius: 20px; overflow: hidden;
            }}
            #onigiri-bg-layer {{
                position: absolute; inset: -50px;
                {bg_layer_css}
            }}
            #scale-wrapper {{
                position: relative; z-index: 1;
                width: {final_w}px; height: {final_h}px;
                flex-shrink: 0;
            }}
            #senchado-preview-inner {{
                position: absolute; top: 0; left: 0;
                width: {natural_w}px; height: {natural_h}px;
                transform: scale({factor}); transform-origin: top left;
            }}
        </style></head>
        <body>
            <div id="onigiri-bg-container">
                <div id="onigiri-bg-layer"></div>
            </div>
            <div id="scale-wrapper">
                <div id="senchado-preview-inner">{html_content}</div>
            </div>
        </body></html>
        """
        self.webview.setHtml(full_html)


class SenchadoSettings(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("Senchado")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self.finished.connect(self._cleanup_on_close)

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

        # Button colors based on theme
        btn_bg = "#252925" if theme_manager.night_mode else "#3F6D49"
        btn_text = "#FFFFFF"
        btn_hover = "#3A3F39" if theme_manager.night_mode else "#4A7E54"

        # Left Button - Buy me a tea
        buy_tea_btn = IconExpandButton("coffee", "Buy me a tea", btn_bg, btn_text, btn_hover)
        buy_tea_btn.clicked.connect(lambda: webbrowser.open("https://buymeacoffee.com/peacemonk"))

        # Logo (small, inline wordmark for the bottom bar)
        self.logo_label = ClickableLabel()
        addon_root = os.path.dirname(os.path.abspath(__file__))
        logo_filename = "senchado_timer_logo.svg"
        logo_path = os.path.join(addon_root, logo_filename)
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path)
            logo_pixmap = logo_pixmap.scaledToHeight(40, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(logo_pixmap)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.logo_label.clicked.connect(self.show_version_popup)

        # Right Button - Report bug
        report_btn = IconExpandButton("bug", "Report bug", btn_bg, btn_text, btn_hover)
        report_btn.clicked.connect(lambda: webbrowser.open("https://github.com/thepeacemonk/Komori"))

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

        # Bottom Bar: logo + link buttons + Cancel/Ok, all in a single pill bar
        btn_container = QWidget()
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(20, 10, 20, 20)
        btn_container.setLayout(btn_layout)

        self.bottom_bar = QFrame()
        self.bottom_bar.setObjectName("bottom_bar")
        self.bottom_bar.setStyleSheet(f"""
            QFrame#bottom_bar {{
                background-color: {self.c['card']};
                border-radius: 25px;
                border: 1px solid {self.c['border']};
            }}
        """)
        bottom_bar_layout = QHBoxLayout()
        bottom_bar_layout.setContentsMargins(15, 8, 15, 8)
        bottom_bar_layout.setSpacing(15)
        self.bottom_bar.setLayout(bottom_bar_layout)

        bottom_bar_layout.addWidget(self.logo_label)
        bottom_bar_layout.addStretch()

        cancel_btn = IconExpandButton("x", "Cancel", btn_bg, btn_text, btn_hover)
        cancel_btn.clicked.connect(self.reject)
        ok_btn = IconExpandButton("check", "Ok", btn_bg, btn_text, btn_hover)
        ok_btn.clicked.connect(self.save_and_close)
        ok_btn.setDefault(True)
        bottom_bar_layout.addWidget(buy_tea_btn)
        bottom_bar_layout.addWidget(report_btn)
        bottom_bar_layout.addWidget(cancel_btn)
        bottom_bar_layout.addWidget(ok_btn)

        btn_layout.addWidget(self.bottom_bar)

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
                "card": "#262925", "border": "#3A3F39", "accent": "#3F6D49",
                "accent_hover": "#6B8E6D", "btn_txt": "#FFFFFF"
            }
        else:
            self.c = {
                "bg": "#FAFAF5", "fg": "#2C3E2D", "sub": "#5D6F5E",
                "card": "#FFFFFF", "border": "#D8DED0", "accent": "#3F6D49",
                "accent_hover": "#6B8E6D", "btn_txt": "#FFFFFF"
            }

        accent_hex = self.c['accent'].lstrip('#')
        accent_rgb = tuple(int(accent_hex[i:i + 2], 16) for i in (0, 2, 4))
        scrollbar_thumb = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.45)"
        scrollbar_thumb_hover = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.75)"

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
            /* Support button - MUST be pill-shaped at all times */
            QPushButton#support_btn {{
                background-color: {self.c['bg']};
                color: {self.c['fg']};
                border: 1px solid {self.c['border']};
                border-radius: 20px;
                font-weight: 600;
                font-size: 13px;
                padding-left: 10px;
                padding-right: 10px;
            }}
            QPushButton#support_btn:hover {{
                border: 1px solid {self.c['accent']};
                border-radius: 20px;
                color: {self.c['accent']};
                background-color: {self.c['card']};
            }}
            QPushButton#support_btn:pressed {{
                border: 1px solid {self.c['accent']};
                border-radius: 20px;
                color: {self.c['accent']};
                background-color: {self.c['bg']};
            }}
            QPushButton#support_btn:focus {{
                border: 1px solid {self.c['accent']};
                border-radius: 20px;
            }}
            QPushButton#support_btn:disabled {{
                border-radius: 20px;
            }}
            QScrollArea#teaRoomScroll QScrollBar:vertical {{
                background: {self.c['bg']};
                width: 8px;
                margin: 0px;
                border: none;
            }}
            QScrollArea#teaRoomScroll QScrollBar::handle:vertical {{
                background: {scrollbar_thumb};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollArea#teaRoomScroll QScrollBar::handle:vertical:hover {{
                background: {scrollbar_thumb_hover};
            }}
            QScrollArea#teaRoomScroll QScrollBar::add-line:vertical,
            QScrollArea#teaRoomScroll QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollArea#teaRoomScroll QScrollBar::add-page:vertical,
            QScrollArea#teaRoomScroll QScrollBar::sub-page:vertical {{
                background: none;
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
        scroll.setObjectName("teaRoomScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        card_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        card_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        card_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
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
        tea_row_label = self.create_label("Select Tea")
        # Match the field's height exactly and center the text inside it,
        # rather than relying on QFormLayout's own cell alignment for the
        # label widget (which wasn't centering it against the taller pill).
        tea_row_label.setFixedHeight(52)
        tea_row_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        card_layout.addRow(tea_row_label, self.tea_selector)

        # Temperature
        self.temp_slider = OnigiriStyleSlider(self.c['accent'], self.c['border'])
        self.temp_slider.setRange(0, 200)
        self.temp_slider.valueChanged.connect(self.update_temp_label)
        
        self.temp_label = QLabel("80º")
        self.temp_label.setFixedWidth(40)
        self.temp_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Icons
        snowflake_icon = QLabel()
        snowflake_icon.setPixmap(load_lucide_icon("snowflake", self.c['sub'], 18))
        flame_icon = QLabel()
        flame_icon.setPixmap(load_lucide_icon("flame", self.c['accent'], 18))
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(snowflake_icon)
        temp_layout.addWidget(self.temp_slider)
        temp_layout.addWidget(flame_icon)
        temp_layout.addWidget(self.temp_label)
        card_layout.addRow(self.create_label("Temperature"), temp_layout)
        
        # Timer Settings (no spinner arrows; unit label pinned to the right edge)
        self.prep_time_spin = FixedSpinBox()
        self.prep_time_spin.setRange(1, 120)
        attach_unit_label(self.prep_time_spin, "min", self.c['accent'])
        card_layout.addRow(self.create_label("Preparation Time"), self.prep_time_spin)

        self.brew_time_spin = FixedSpinBox()
        self.brew_time_spin.setRange(1, 60)
        attach_unit_label(self.brew_time_spin, "min", self.c['accent'])
        card_layout.addRow(self.create_label("Brewing Time"), self.brew_time_spin)

        self.cycles_spin = FixedSpinBox()
        self.cycles_spin.setRange(1, 10)
        attach_unit_label(self.cycles_spin, "cycles", self.c['accent'])
        card_layout.addRow(self.create_label("Number of Cycles"), self.cycles_spin)
        
        main_layout.addWidget(form_card)
        main_layout.addStretch()

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
        self.reviewer_opacity_slider = OnigiriStyleSlider(self.c['accent'], self.c['border'])
        self.reviewer_opacity_slider.setRange(0, 100)
        self.reviewer_opacity_slider.setValue(100)
        self.reviewer_opacity_slider.valueChanged.connect(self.update_reviewer_opacity_label)
        
        self.reviewer_opacity_label = QLabel("100%")
        self.reviewer_opacity_label.setFixedWidth(40)
        self.reviewer_opacity_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        row_opacity = QHBoxLayout()
        row_opacity.addWidget(QLabel("Opacity"))
        row_opacity.addWidget(self.reviewer_opacity_slider)
        row_opacity.addWidget(self.reviewer_opacity_label)
        pos_card_layout.addLayout(row_opacity)

        # Glassmorphism (Blur)
        self.reviewer_blur_slider = OnigiriStyleSlider(self.c['accent'], self.c['border'])
        self.reviewer_blur_slider.setRange(0, 20)
        self.reviewer_blur_slider.setValue(0)
        self.reviewer_blur_slider.valueChanged.connect(self.update_reviewer_blur_label)
        
        self.reviewer_blur_label = QLabel("0px")
        self.reviewer_blur_label.setFixedWidth(40)
        self.reviewer_blur_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        row_blur = QHBoxLayout()
        row_blur.addWidget(QLabel("Blur"))
        row_blur.addWidget(self.reviewer_blur_slider)
        row_blur.addWidget(self.reviewer_blur_label)
        pos_card_layout.addLayout(row_blur)
        
        # Minimal Mode Default
        self.reviewer_minimal_check = AnimatedToggleButton(accent_color=self.c['accent'], track_color_off=self.c['border'])
        row_minimal = QHBoxLayout()
        minimal_lbl = QLabel("Minimal mode as default")
        minimal_lbl.setStyleSheet(f"font-weight: 500; color: {self.c['fg']};")
        row_minimal.addWidget(minimal_lbl)
        row_minimal.addStretch()
        row_minimal.addWidget(self.reviewer_minimal_check)
        pos_card_layout.addLayout(row_minimal)

        # Hide Cycle Counter
        self.reviewer_hide_cycle_check = AnimatedToggleButton(accent_color=self.c['accent'], track_color_off=self.c['border'])
        row_hide_cycle = QHBoxLayout()
        hide_cycle_lbl = QLabel("Hide cycle counter")
        hide_cycle_lbl.setStyleSheet(f"font-weight: 500; color: {self.c['fg']};")
        row_hide_cycle.addWidget(hide_cycle_lbl)
        row_hide_cycle.addStretch()
        row_hide_cycle.addWidget(self.reviewer_hide_cycle_check)
        pos_card_layout.addLayout(row_hide_cycle)

        # Silence Notifications
        self.silence_check = AnimatedToggleButton(accent_color=self.c['accent'], track_color_off=self.c['border'])
        row_silence = QHBoxLayout()
        silence_lbl = QLabel("Silence notifications")
        silence_lbl.setStyleSheet(f"font-weight: 500; color: {self.c['fg']};")
        row_silence.addWidget(silence_lbl)
        row_silence.addStretch()
        row_silence.addWidget(self.silence_check)
        pos_card_layout.addLayout(row_silence)

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
        main_layout.addWidget(pos_card)

        # --- Tea Room Widget Section ---

        widget_title = QLabel("Tea Room Widget")
        widget_title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px; margin-top: 10px;")
        main_layout.addWidget(widget_title)

        widget_card = QFrame()
        widget_card.setProperty("class", "tea-card")
        widget_card_layout = QVBoxLayout()
        widget_card_layout.setContentsMargins(0, 0, 0, 0)
        widget_card_layout.setSpacing(0)
        widget_card.setLayout(widget_card_layout)

        # ── Top: Preview panel ───────────────────────────────────────────
        tea_preview_wrapper = QWidget()
        tea_preview_wrapper_layout = QVBoxLayout(tea_preview_wrapper)
        tea_preview_wrapper_layout.setContentsMargins(30, 30, 30, 20)
        tea_preview_wrapper_layout.setSpacing(12)

        tea_preview_title = QLabel("Preview")
        tea_preview_title.setStyleSheet(f"font-size: 12px; font-weight: 700; letter-spacing: 0.6px; color: {self.c['sub']};")
        tea_preview_wrapper_layout.addWidget(tea_preview_title)

        self.tea_widget_preview = SenchadoWidgetPreview(self)
        self.tea_widget_preview.setFixedHeight(320)
        tea_preview_wrapper_layout.addWidget(self.tea_widget_preview)

        widget_card_layout.addWidget(tea_preview_wrapper)

        widget_sep = QFrame()
        widget_sep.setFrameShape(QFrame.Shape.HLine)
        widget_sep.setFrameShadow(QFrame.Shadow.Sunken)
        widget_sep.setStyleSheet(f"background-color: {self.c['border']}; max-height: 1px; border: none;")
        widget_card_layout.addWidget(widget_sep)

        # ── Bottom: Controls ─────────────────────────────────────────────
        widget_controls_wrapper = QWidget()
        widget_layout = QFormLayout(widget_controls_wrapper)
        widget_layout.setContentsMargins(30, 20, 30, 30)
        widget_layout.setSpacing(20)
        widget_card_layout.addWidget(widget_controls_wrapper)

        # 1. Opacity
        self.opacity_slider = OnigiriStyleSlider(self.c['accent'], self.c['border'])
        self.opacity_slider.setRange(10, 100) # Minimum 10%
        self.opacity_slider.setSingleStep(10)

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
        self.glass_slider = OnigiriStyleSlider(self.c['accent'], self.c['border'])
        self.glass_slider.setRange(0, 20) # Blur radius 0-20px
        self.glass_slider.setSingleStep(1)

        glass_container = QHBoxLayout()
        glass_container.addWidget(self.glass_slider)
        self.glass_label = QLabel("0px")
        self.glass_label.setFixedWidth(40)
        self.glass_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        glass_container.addWidget(self.glass_label)

        self.glass_slider.valueChanged.connect(lambda v: self.glass_label.setText(f"{v}px"))

        widget_layout.addRow(self.create_label("Blur"), glass_container)



        # 4. Card Color (light/dark)
        color_container = QHBoxLayout()
        color_container.setSpacing(10)

        ui_settings_for_colors = manager.get_ui_settings()
        self.card_color_buttons = {}
        for mode_key, mode_label, default_val in (
            ("widget_card_color_light", "Light", "#FFFFFF"),
            ("widget_card_color_dark", "Dark", "#262925"),
        ):
            initial_color = ui_settings_for_colors.get(mode_key, default_val)

            color_row = QFrame()
            color_row.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.c['bg']};
                    border: 1px solid {self.c['border']};
                    border-radius: 12px;
                }}
            """)
            color_row_layout = QHBoxLayout(color_row)
            color_row_layout.setContentsMargins(12, 8, 12, 8)

            mode_lbl = QLabel(mode_label)
            mode_lbl.setStyleSheet(f"font-weight: 700; font-size: 12px; border: none; background: transparent; color: {self.c['fg']};")
            color_row_layout.addWidget(mode_lbl)
            color_row_layout.addStretch()

            btn = create_color_button(initial_color, self)
            btn.clicked.connect(lambda _=False, k=mode_key: self._pick_card_color(k))
            self.card_color_buttons[mode_key] = btn
            color_row_layout.addWidget(btn)

            color_container.addWidget(color_row)

        widget_layout.addRow(self.create_label("Card Color"), color_container)

        main_layout.addWidget(widget_card)

        # --- Onigiri Integration (part of the scrollable Tea Room content) ---
        integration_group, self.bento_width_spin, self.bento_height_spin = bento_integration.create_settings_group(
            manager.get_ui_settings(),
            default_width=400,
            default_height=400,
        )
        main_layout.addWidget(integration_group)

        # Live preview: every control that save_and_close() eventually reads
        # also feeds the in-progress preview as soon as it changes.
        self.task_name_input.textChanged.connect(self._refresh_tea_widget_preview)
        self.tea_selector.teaSelected.connect(self._refresh_tea_widget_preview)
        self.temp_slider.valueChanged.connect(self._refresh_tea_widget_preview)
        self.prep_time_spin.valueChanged.connect(self._refresh_tea_widget_preview)
        self.brew_time_spin.valueChanged.connect(self._refresh_tea_widget_preview)
        self.cycles_spin.valueChanged.connect(self._refresh_tea_widget_preview)
        self.opacity_slider.valueChanged.connect(self._refresh_tea_widget_preview)
        self.glass_slider.valueChanged.connect(self._refresh_tea_widget_preview)
        self.bento_width_spin.valueChanged.connect(self._refresh_tea_widget_preview)
        self.bento_height_spin.valueChanged.connect(self._refresh_tea_widget_preview)

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

    def _pick_card_color(self, mode_key):
        button = self.card_color_buttons[mode_key]
        current_color_str = button.text()

        try:
            onigiri_color_picker = importlib.import_module("1011095603.onigiri_color_picker")
            OnigiriColorDialog = onigiri_color_picker.OnigiriColorDialog
            new_color_hex, ok = OnigiriColorDialog.getColor(current_color_str, self, anchor=button)
            if ok:
                _apply_swatch_style(button, new_color_hex)
                self._refresh_tea_widget_preview()
            return
        except Exception as e:
            print(f"[Senchado] Failed to load OnigiriColorDialog: {e}")

        color = QColorDialog.getColor(QColor(current_color_str), self, "Choose Card Color")
        if color.isValid():
            new_color_str = color.name().upper()
            _apply_swatch_style(button, new_color_str)
            self._refresh_tea_widget_preview()

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
        accent_hex = self.c['accent'].lstrip('#')
        accent_rgb = tuple(int(accent_hex[i:i + 2], 16) for i in (0, 2, 4))
        scrollbar_thumb = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.45)"
        scrollbar_thumb_hover = f"rgba({accent_rgb[0]}, {accent_rgb[1]}, {accent_rgb[2]}, 0.75)"
        
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {scrollbar_thumb};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scrollbar_thumb_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
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
            
        # Ensure we start on a new row for the footer
        if current_col > 0:
            current_row += 1
            
        # Coming Soon / Support Hero
        coming_soon = QFrame()
        coming_soon.setProperty("class", "tea-card")
        
        cs_layout = QVBoxLayout()
        cs_layout.setContentsMargins(24, 30, 24, 30)
        cs_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        coming_soon.setLayout(cs_layout)
        
        cs_lbl = QLabel("More tea flavors coming soon!")
        cs_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cs_lbl.setStyleSheet(f"color: {self.c['sub']}; font-size: 15px; font-weight: 600;")
        cs_layout.addWidget(cs_lbl)
        
        cs_layout.addSpacing(12)
        
        # Using QFrame instead of QPushButton to bypass all button styling conflicts
        buy_btn = QFrame()
        buy_btn.setObjectName("support_btn")
        buy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buy_btn.setFixedWidth(200)
        buy_btn.setFixedHeight(40)
        buy_btn.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        buy_btn.setStyleSheet(f"""
            QFrame#support_btn {{
                background-color: {self.c['bg']};
                border: 1px solid {self.c['border']};
                border-radius: 20px;
            }}
            QFrame#support_btn:hover {{
                border: 1px solid {self.c['accent']};
                background-color: {self.c['card']};
            }}
        """)
        
        # Add label for text
        btn_layout = QHBoxLayout(buy_btn)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_label = QLabel("Support Senchadō")
        btn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btn_label.setStyleSheet(f"""
            QLabel {{
                color: {self.c['fg']};
                font-weight: 600;
                font-size: 13px;
                background: transparent;
                border: none;
            }}
        """)
        btn_layout.addWidget(btn_label)
        
        # Make clickable (must not return value to avoid sipBadCatcherResult error)
        def on_support_click(event):
            webbrowser.open("https://buymeacoffee.com/peacemonk")
        buy_btn.mousePressEvent = on_support_click
        cs_layout.addWidget(buy_btn)
        
        # Add to grid, spanning full width (2 columns)
        grid.addWidget(coming_soon, current_row, 0, 1, 2)

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
            
            details_layout = QHBoxLayout()
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setSpacing(6)
            
            def add_detail(icon_name, text, color):
                icon_lbl = QLabel()
                icon_lbl.setPixmap(load_lucide_icon(icon_name, color, 14))
                icon_lbl.setStyleSheet("border: none; background: transparent;")
                details_layout.addWidget(icon_lbl)
                text_lbl = QLabel(text)
                text_lbl.setStyleSheet(f"color: {color}; font-size: 12px;")
                details_layout.addWidget(text_lbl)

            add_detail("coffee", tea_name, self.c['accent'])
            
            dot1 = QLabel("•")
            dot1.setStyleSheet(f"color: {self.c['sub']}; font-size: 12px;")
            details_layout.addWidget(dot1)
            
            add_detail("flame", f"{fav['temperature']}º", self.c['sub'])
            
            dot2 = QLabel("•")
            dot2.setStyleSheet(f"color: {self.c['sub']}; font-size: 12px;")
            details_layout.addWidget(dot2)
            
            add_detail("timer", f"{int(fav['prep_time']/60)}/{int(fav['brew_time']/60)}m", self.c['sub'])

            if fav.get("cycles", 1) > 1:
                dot3 = QLabel("•")
                dot3.setStyleSheet(f"color: {self.c['sub']}; font-size: 12px;")
                details_layout.addWidget(dot3)
                
                cycles_lbl = QLabel(f"x{fav['cycles']}")
                cycles_lbl.setStyleSheet(f"color: {self.c['sub']}; font-size: 12px;")
                details_layout.addWidget(cycles_lbl)
                
            details_layout.addStretch()
            
            details_widget = QWidget()
            details_widget.setLayout(details_layout)
            
            info_layout.addWidget(task_lbl)
            info_layout.addWidget(details_widget)
            
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
        flavor_id = self.tea_selector.current_tea_id
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
            
            self.tea_selector.setTea(conf["flavor_id"])
            
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
            def add_stat(layout, icon_name, text, color, weight="normal"):
                icon = QLabel()
                icon.setPixmap(load_lucide_icon(icon_name, color, 14))
                icon.setStyleSheet("background: transparent; border: none;")
                layout.addWidget(icon)
                lbl = QLabel(text)
                lbl.setStyleSheet(f"color: {color}; font-weight: {weight}; font-size: 12px;")
                layout.addWidget(lbl)
                layout.addSpacing(12)

            prep_min = int(entry.get('prep_time', 0) / 60)
            brew_min = int(entry.get('brew_time', 0) / 60)

            stats_layout = QHBoxLayout()
            stats_layout.setContentsMargins(0, 0, 0, 0)
            stats_layout.setSpacing(4)
            
            # Tea
            add_stat(stats_layout, "coffee", tea_name, self.c['accent'], "500")
            
            # Temp
            add_stat(stats_layout, "flame", f"{temp}º", self.c['sub'])
            
            # Chef
            chef_lbl = QLabel(f"Chef Lvl {level}")
            chef_lbl.setStyleSheet(f"color: {self.c['sub']}; font-size: 12px;")
            stats_layout.addWidget(chef_lbl)
            stats_layout.addSpacing(12)
            
            # Timer
            add_stat(stats_layout, "timer", f"{prep_min}m / {brew_min}m", self.c['sub'])

            stats_widget = QWidget()
            stats_widget.setLayout(stats_layout)
            
            # Layout Assembly
            card_layout.addWidget(date_lbl)
            card_layout.addWidget(task_lbl, stretch=1) # Task takes available space
            card_layout.addWidget(stats_widget)
            
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

        # Hide Cycle Counter
        rev_hide_cycle = ui_settings.get("reviewer_hide_cycle_counter", False)
        if hasattr(self, 'reviewer_hide_cycle_check'):
            self.reviewer_hide_cycle_check.setChecked(rev_hide_cycle)

        self._refresh_tea_widget_preview()



    def _collect_preview_data(self):
        """Assembles the in-progress (unsaved) tea/task/appearance config for
        the live preview, mirroring save_and_close() below. Player level/XP
        isn't edited in this dialog, so that part is just the real value."""
        progress = manager.get_progress()

        flavor_id = getattr(self.tea_selector, "current_tea_id", None) or manager.get_current_tea().get("flavor_id", "sencha")
        tea_config = {
            "flavor_id": flavor_id,
            "task_name": self.task_name_input.text().strip() or "Study Session",
            "temperature": self.temp_slider.value(),
            "prep_time": self.prep_time_spin.value() * 60,
            "brew_time": self.brew_time_spin.value() * 60,
            "cycles": self.cycles_spin.value(),
        }

        ui_settings = dict(manager.get_ui_settings())
        ui_settings["widget_opacity"] = self.opacity_slider.value()
        glass_strength = self.glass_slider.value()
        ui_settings["widget_glass_strength"] = glass_strength
        ui_settings["widget_glass"] = glass_strength > 0
        ui_settings["widget_size"] = "medium"
        ui_settings["manual_widget_width"] = self.bento_width_spin.value()
        ui_settings["manual_widget_height"] = self.bento_height_spin.value()
        for mode_key, btn in getattr(self, "card_color_buttons", {}).items():
            ui_settings[mode_key] = btn.text()

        return progress, tea_config, ui_settings

    def _refresh_tea_widget_preview(self, *_args):
        if not hasattr(self, "tea_widget_preview"):
            return
        progress, tea_config, ui_settings = self._collect_preview_data()
        self.tea_widget_preview.refresh(progress, tea_config, ui_settings)

    def _cleanup_on_close(self, *args):
        preview = getattr(self, "tea_widget_preview", None)
        if preview is not None:
            preview.cleanup()
        self.deleteLater()

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

        if hasattr(self, 'card_color_buttons'):
            for mode_key, btn in self.card_color_buttons.items():
                manager.set_ui_setting(mode_key, btn.text())

        # Save Reviewer Overlay Settings
        if hasattr(self, 'reviewer_opacity_slider'):
            manager.set_ui_setting("reviewer_opacity", self.reviewer_opacity_slider.value())
            
        if hasattr(self, 'reviewer_blur_slider'):
            manager.set_ui_setting("reviewer_blur", self.reviewer_blur_slider.value())

        if hasattr(self, 'reviewer_minimal_check'):
            manager.set_ui_setting("reviewer_minimal_mode_default", self.reviewer_minimal_check.isChecked())

        if hasattr(self, 'reviewer_hide_cycle_check'):
            manager.set_ui_setting("reviewer_hide_cycle_counter", self.reviewer_hide_cycle_check.isChecked())

        manager.set_ui_setting("widget_size", "medium")

        if hasattr(self, 'bento_width_spin'):
            manager.set_ui_setting("manual_widget_width", self.bento_width_spin.value())
            manager.set_ui_setting("manual_widget_height", self.bento_height_spin.value())

        if hasattr(self, 'silence_check'):
            manager.set_ui_setting("silence_notifications", self.silence_check.isChecked())
            
        tea_timer.stop() # Reset timer to apply new settings
        self.accept()

    def update_reviewer_opacity_label(self, value):
        self.reviewer_opacity_label.setText(f"{value}%")
        
    def update_reviewer_blur_label(self, value):
        self.reviewer_blur_label.setText(f"{value}px")


# ── Bento WebUI settings -----------------------------------------------------
try:
    if getattr(mw, "onigiri_api", {}).get("id") != "1011095603":
        raise ImportError("Onigiri Bento API is not active")
    _bws = importlib.import_module("1011095603.api.widget_settings")
except Exception:
    _bws = None

_TEA_THUMB_CACHE = {}


def _tea_thumb_data_uri(path: str) -> str:
    """Return a compact 96x96 PNG data URI for tea dropdowns & shelf cards."""
    if not path or not os.path.isfile(path):
        return ""
    cached = _TEA_THUMB_CACHE.get(path)
    if cached is not None:
        return cached
    try:
        import base64
        img = QImage(path)
        if not img.isNull():
            aspect_enum = getattr(Qt, "AspectRatioMode", Qt)
            trans_enum = getattr(Qt, "TransformationMode", Qt)
            open_enum = getattr(QIODevice, "OpenModeFlag", QIODevice)
            scaled = img.scaled(
                96,
                96,
                aspect_enum.KeepAspectRatio,
                trans_enum.SmoothTransformation,
            )
            buf = QBuffer()
            buf.open(open_enum.WriteOnly)
            scaled.save(buf, "PNG")
            encoded = base64.b64encode(bytes(buf.data())).decode("ascii")
            buf.close()
            if encoded:
                uri = f"data:image/png;base64,{encoded}"
                _TEA_THUMB_CACHE[path] = uri
                return uri
    except Exception:
        pass
    uri = _bws.image_data_uri(path) if _bws is not None else ""
    _TEA_THUMB_CACHE[path] = uri
    return uri


if _bws is not None:
    class SenchadoSettings(_bws.BentoSettingsDialog):
        def __init__(self, parent=None):
            from .config import DEFAULT_CONFIG as _DEFAULT_CONFIG

            current = deepcopy(manager.config)
            defaults = deepcopy(_DEFAULT_CONFIG)
            # Resetting appearance must never erase earned progress, history,
            # or the user's saved tea recipes.
            for precious in ("user_progress", "tea_history", "favorites"):
                defaults[precious] = deepcopy(current.get(precious, defaults.get(precious)))

            progress_data = current.get("user_progress", {}) or {}
            level = int(progress_data.get("level", 1) or 1)
            xp = int(progress_data.get("xp", 0) or 0)
            total_brews = int(progress_data.get("total_brews", 0) or 0)
            current_flavor_id = (current.get("current_tea", {}) or {}).get("flavor_id", "sencha")

            sorted_teas = sorted(TEAS.values(), key=lambda t: t.unlock_level)
            next_tea = next((t for t in sorted_teas if t.unlock_level > level), None)
            next_tea_id = next_tea.id if next_tea else None
            next_unlock_summary = (
                f"Next unlock: {next_tea.name} at Level {next_tea.unlock_level} "
                f"({max(1, next_tea.unlock_level - level)} level{'s' if (next_tea.unlock_level - level) != 1 else ''} to go)."
                if next_tea
                else "All 15 teas unlocked."
            )

            available = []
            addon_dir = os.path.dirname(__file__)
            for tea in sorted_teas:
                unlocked = tea.unlock_level <= level or tea.id == current_flavor_id
                is_next = (not unlocked) and (tea.id == next_tea_id)
                img_uri = _tea_thumb_data_uri(os.path.join(addon_dir, "tea_gallery", f"{tea.id}.png"))
                available.append({
                    "value": tea.id,
                    "label": tea.name,
                    "subtitle": (
                        tea.description
                        if unlocked
                        else f"Unlocks at Level {tea.unlock_level} — {tea.description}"
                    ),
                    "description": tea.description,
                    "image": img_uri,
                    "locked": not unlocked,
                    "next": is_next,
                    "unlockLevel": tea.unlock_level,
                    "badge": (
                        f"Next · Lvl {tea.unlock_level}"
                        if is_next
                        else f"Lvl {tea.unlock_level}"
                    ),
                })

            favorites = current.get("favorites", []) or []
            history = current.get("tea_history", []) or []
            current["_favorites_summary"] = (
                f"{len(favorites)} saved configuration{'s' if len(favorites) != 1 else ''}."
            )
            history_lines = []
            for entry in history[:12]:
                stamp = str(entry.get("timestamp", ""))[:10]
                tea = TEAS.get(entry.get("flavor_id"))
                history_lines.append(f"{stamp}  ·  {entry.get('task_name', 'Study Session')}  ·  {tea.name if tea else 'Tea'}")
            current["_history_summary"] = "\n".join(history_lines) or "No tea preparations recorded in the last 30 days."

            def save(updated):
                from .main_widget import schedule_live_widget_refresh
                clean = deepcopy(updated)
                for key in list(clean):
                    if key.startswith("_"):
                        clean.pop(key, None)
                manager.config.clear(); manager.config.update(clean)
                manager.save()
                if getattr(getattr(tea_timer, "state", None), "name", "IDLE") != "IDLE":
                    tea_timer.stop()
                schedule_live_widget_refresh()

            def preview(updated, variant, theme):
                from .main_widget import generate_widget_html
                from .reviewer_overlay import generate_reviewer_html
                dark = theme == "dark"
                if variant == "reviewer":
                    return _bws.preview_document(
                        generate_reviewer_html(
                            tea_config=updated.get("current_tea"),
                            ui_settings=updated.get("ui_settings"),
                            is_dark=dark,
                        ),
                        dark=dark,
                        wallpaper=bento_integration.reviewer_wallpaper(dark),
                        body_class="bws-stage-fill",
                    )
                return _bws.preview_document(
                    generate_widget_html(
                        progress=updated.get("user_progress"),
                        tea_config=updated.get("current_tea"),
                        ui_settings=updated.get("ui_settings"),
                        is_dark=dark,
                    ),
                    dark=dark, wallpaper=bento_integration.main_menu_wallpaper(dark),
                )

            favorite_fields = [
                _bws.field("_favorites_summary", "Saved recipes", "info", default=current["_favorites_summary"]),
                _bws.field("save-current-favorite", "Save current recipe", "action", button_label="Save current configuration"),
            ]
            for index, favorite in enumerate(favorites):
                tea = TEAS.get(favorite.get("flavor_id"))
                summary = (
                    f"{favorite.get('task_name', 'Study Session')} · "
                    f"{tea.name if tea else 'Tea'} · {int(favorite.get('prep_time', 0)) // 60} "
                    f"min prep · {int(favorite.get('brew_time', 0)) // 60} min brew"
                )
                current[f"_favorite_{index}"] = summary
                favorite_fields.extend([
                    _bws.field(f"_favorite_{index}", f"Recipe {index + 1}", "info", default=summary),
                    _bws.field(f"load-favorite:{index}", f"Load recipe {index + 1}", "action", button_label="Load"),
                    _bws.field(f"delete-favorite:{index}", f"Delete recipe {index + 1}", "action", button_label="Delete"),
                ])

            pages = [
                _bws.page("tea_room", "Tea Room", [
                    _bws.section("Brewing configuration", [
                        _bws.field("current_tea.task_name", "Task name", default="Study Session", placeholder="e.g. Study Kanji"),
                        _bws.field("current_tea.flavor_id", "Tea", "select", default="sencha", options=available, description=next_unlock_summary),
                        _bws.field(
                            "current_tea.temperature", "Temperature", "range",
                            default=80, minimum=0, maximum=200, unit="°C",
                        ),
                        _bws.field("current_tea.prep_time", "Preparation time", "number", default=25, minimum=1, maximum=120, unit="min", scale=60),
                        _bws.field("current_tea.brew_time", "Brewing time", "number", default=5, minimum=1, maximum=60, unit="min", scale=60),
                        _bws.field("current_tea.cycles", "Cycles", "number", default=1, minimum=1, maximum=10),
                    ]),
                ], "Configure your tea, temperature, and brewing session.", "茶", show_preview=False),
                _bws.page("garden", "Tea Shelf", [
                    _bws.section("Level & Tea Collection", [
                        _bws.field(
                            "current_tea.flavor_id", "Tea Collection", "tea_garden",
                            default="sencha", teas=available, level=level, xp=xp,
                            nextLevelXp=level * 100, totalBrews=total_brews, hideLabel=True,
                        ),
                    ], "Choose any unlocked tea to equip it, or see which tea unlocks next as you level up."),
                ], "Track your Senchadō level, XP progress, and unlockable teas.", "❀", show_preview=False),
                _bws.page("reviewer", "Widgets", [
                    _bws.section("Main Menu widget", [
                        _bws.field(
                            "ui_settings.widget_style", "Layout style", "select",
                            default="zen",
                            options=[
                                {"value": "zen", "label": "Modern Zen"},
                                {"value": "compact", "label": "Compact"},
                                {"value": "minimal", "label": "Minimal"},
                                {"value": "classic", "label": "Classic"},
                            ],
                        ),
                        _bws.field("ui_settings.widget_tea_accent", "Tea color accent", "bool", default=False),
                        _bws.field("ui_settings.widget_show_xp", "Show level & XP", "bool", default=True),
                        _bws.field("ui_settings.widget_show_task", "Show task name", "bool", default=True),
                        _bws.field("ui_settings.widget_show_brew_details", "Show brewing details", "bool", default=True),
                        _bws.field("ui_settings.widget_opacity", "Opacity", "range", default=100, minimum=10, maximum=100, unit="%"),
                        _bws.field("ui_settings.widget_glass_strength", "Glass blur", "range", default=0, minimum=0, maximum=20, unit="px"),
                    ]),
                    _bws.section("Reviewer widget", [
                        _bws.field(
                            "ui_settings.reviewer_style", "Layout style", "select",
                            default="modern",
                            options=[
                                {"value": "modern", "label": "Modern HUD"},
                                {"value": "pill", "label": "Floating Pill"},
                                {"value": "minimal", "label": "Minimal"},
                            ],
                        ),
                        _bws.field("ui_settings.reviewer_position", "Position", "position_grid", default="top-right"),
                        _bws.field("ui_settings.reviewer_opacity", "Opacity", "range", default=100, minimum=0, maximum=100, unit="%"),
                        _bws.field("ui_settings.reviewer_blur", "Blur", "range", default=0, minimum=0, maximum=20, unit="px"),
                        _bws.field("ui_settings.reviewer_tea_accent", "Tea color accent", "bool", default=False),
                        _bws.field("ui_settings.reviewer_minimal_mode_default", "Start minimized", "bool", default=False),
                        _bws.field("ui_settings.reviewer_show_task", "Show task name", "bool", default=True),
                        _bws.field("ui_settings.reviewer_hide_cycle_counter", "Hide cycle counter", "bool", default=False),
                        _bws.field("ui_settings.silence_notifications", "Silence notifications", "bool", default=False),
                    ]),
                ], "Customize your Tea Room widgets for the Main Menu and Reviewer.", "R", show_preview=True, preview_variant="main_menu"),
                _bws.page("appearance", "Appearance", [
                    _bws.section("Tea Room widget", [
                        _bws.field("ui_settings.widget_opacity", "Opacity", "range", default=100, minimum=10, maximum=100, unit="%"),
                        _bws.field("ui_settings.widget_glass_strength", "Glass blur", "range", default=0, minimum=0, maximum=20, unit="px"),
                        _bws.field("ui_settings.widget_card_color_light", "Light card color", "color", default="#FFFFFF"),
                        _bws.field("ui_settings.widget_card_color_dark", "Dark card color", "color", default="#262925"),
                    ]),
                ], "Card colors, glass, and opacity.", "◐", show_preview=True, preview_variant="main_menu"),
                _bws.page("favorites", "Favorites", [
                    _bws.section("Favorite tea configurations", favorite_fields),
                ], "Save or recall complete brewing configurations.", "★", show_preview=False),
                _bws.page("history", "History", [
                    _bws.section("Past 30 days", [
                        _bws.field("_history_summary", "Recent preparations", "info", default=current["_history_summary"]),
                    ]),
                ], "A read-only view of the real preparation history.", "↺", show_preview=False),
            ]
            super().__init__(
                parent, title="Senchadō", subtitle="Tea timer for focused study", accent="#3F6D49",
                pages=pages, config=current, defaults=defaults, save_callback=save,
                logo_path=os.path.join(os.path.dirname(__file__), "senchado_timer_logo.svg"),
                mini_logo_path=os.path.join(os.path.dirname(__file__), "senchado_timer_mini_logo.svg"),
                preview_callback=preview,
                preview_variants=[
                    {"value": "main_menu", "label": "Main Menu"},
                    {"value": "reviewer", "label": "Reviewer"},
                ],
                bugs_url="https://github.com/thepeacemonk/Komori",
            )

        def _render(self):
            html_doc = super()._render()
            addon_block = self._senchado_webui_addon_block()
            if "</body>" in html_doc:
                return html_doc.replace("</body>", addon_block + "</body>", 1)
            return html_doc + addon_block

        def _senchado_webui_addon_block(self):
            import json as _json

            def _read_lucide_inner(filename, fallback):
                svg_path = os.path.join(_ICONS_DIR, filename)
                if os.path.isfile(svg_path):
                    try:
                        with open(svg_path, "r", encoding="utf-8") as handle:
                            raw = handle.read()
                        start = raw.find(">", raw.find("<svg"))
                        end = raw.rfind("</svg>")
                        if start >= 0 and end > start:
                            return raw[start + 1:end].strip()
                    except OSError:
                        pass
                return fallback

            coffee_inner = _read_lucide_inner(
                "lucide-coffee.svg",
                '<path d="M10 2v2"/><path d="M14 2v2"/>'
                '<path d="M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1"/>'
                '<path d="M6 2v2"/>',
            )
            snowflake_inner = _read_lucide_inner(
                "lucide-snowflake.svg",
                '<path d="m10 20-1.25-2.5L6 18"/><path d="M10 4 8.75 6.5 6 6"/>'
                '<path d="m14 20 1.25-2.5L18 18"/><path d="m14 4 1.25 2.5L18 6"/>'
                '<path d="m17 21-3-6h-4"/><path d="m17 3-3 6 1.5 3"/>'
                '<path d="M2 12h6.5L10 9"/><path d="m20 10-1.5 2 1.5 2"/>'
                '<path d="M22 12h-6.5L14 15"/><path d="m4 10 1.5 2L4 14"/>'
                '<path d="m7 21 3-6-1.5-3"/><path d="m7 3 3 6h4"/>',
            )
            flame_inner = _read_lucide_inner(
                "lucide-flame.svg",
                '<path d="M12 3q1 4 4 6.5t3 5.5a1 1 0 0 1-14 0 5 5 0 0 1 1-3 1 1 0 0 0 5 0c0-2-1.5-3-1.5-5q0-2 2.5-4"/>',
            )
            thermometer_snowflake_inner = (
                '<path d="m10 20-1.25-2.5L6 18"/><path d="M10 4 8.75 6.5 6 6"/>'
                '<path d="M10.585 15H10"/><path d="M2 12h6.5L10 9"/>'
                '<path d="M20 14.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0z"/>'
                '<path d="m4 10 1.5 2L4 14"/><path d="m7 21 3-6-1.5-3"/>'
                '<path d="m7 3 3 6h2"/>'
            )
            thermometer_sun_inner = (
                '<path d="M12 9a4 4 0 0 0-2 7.5"/><path d="M12 3v2"/>'
                '<path d="m6.6 18.4-1.4 1.4"/>'
                '<path d="M20 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/>'
                '<path d="M4 13H2"/><path d="M6.34 7.34 4.93 5.93"/>'
            )

            icons_json = _json.dumps({
                "coffee": coffee_inner,
                "cold": snowflake_inner,
                "cool": thermometer_snowflake_inner,
                "warm": coffee_inner,
                "hot": thermometer_sun_inner,
                "boiling": flame_inner,
            }).replace("</", "<\\/")

            return (
                '<style id="senchado-webui-ext">'
                '.bws-pos-card-hint { display: none !important; }'
                '.bws-field.senchado-pos-hidden,'
                '.senchado-variant-hidden { display: none !important; }'
                '.bws-pos-puck svg { width: 15px; height: 15px; flex: 0 0 auto; pointer-events: none; }'
                'html body .bws-field[data-path="current_tea.flavor_id"] .bws-select-trigger,'
                'body.fancy .bws-field[data-path="current_tea.flavor_id"] .bws-select-trigger {'
                '  background: var(--bws-inset);'
                '  border: 1px solid var(--bws-hairline);'
                '  border-radius: var(--bws-radius-control);'
                '}'
                'html body .bws-field[data-path="current_tea.flavor_id"] .bws-select-trigger:hover,'
                'body.fancy .bws-field[data-path="current_tea.flavor_id"] .bws-select-trigger:hover {'
                '  background: var(--bws-inset-hover);'
                '  border-color: var(--bws-accent-line-strong);'
                '}'
                'html body .bws-field[data-path="current_tea.flavor_id"] .bws-select-menu.is-open .bws-select-trigger,'
                'body.fancy .bws-field[data-path="current_tea.flavor_id"] .bws-select-menu.is-open .bws-select-trigger {'
                '  background: var(--bws-inset);'
                '  border-color: var(--bws-accent);'
                '}'
                '.bws-field[data-path="current_tea.temperature"] .bws-slider.senchado-has-temp-icon {'
                '  grid-template-columns: 20px 54px minmax(0, 1fr);'
                '  column-gap: 6px;'
                '}'
                '.bws-field[data-path="current_tea.temperature"] .bws-slider.senchado-has-temp-icon .bws-slider-track {'
                '  margin-left: 6px;'
                '}'
                '.senchado-temp-icon-stack {'
                '  position: relative;'
                '  display: inline-flex;'
                '  align-items: center;'
                '  justify-content: center;'
                '  width: 18px;'
                '  height: 18px;'
                '  flex: 0 0 18px;'
                '  pointer-events: none;'
                '}'
                '.senchado-temp-icon-layer {'
                '  position: absolute;'
                '  inset: 0;'
                '  display: flex;'
                '  align-items: center;'
                '  justify-content: center;'
                '  opacity: 0;'
                '  transform: scale(0.68) translateY(2px);'
                '  will-change: opacity, transform;'
                '  transition:'
                '    opacity 220ms cubic-bezier(.22, 1, .36, 1),'
                '    transform 260ms cubic-bezier(.22, 1, .36, 1);'
                '}'
                '.senchado-temp-icon-layer.is-active {'
                '  opacity: 1;'
                '  transform: scale(1) translateY(0);'
                '}'
                '.senchado-temp-icon-layer svg {'
                '  width: 16px;'
                '  height: 16px;'
                '  display: block;'
                '}'
                '</style>'
                '<script id="senchado-webui-ext-js">(function(){'
                '  var ICONS = ' + icons_json + ';'
                '  var TEMP_STAGES = ['
                '    { id: "cold", max: 39, color: "#38bdf8" },'
                '    { id: "cool", max: 74, color: "#0ea5e9" },'
                '    { id: "warm", max: 109, color: "#d97706" },'
                '    { id: "hot", max: 149, color: "#f97316" },'
                '    { id: "boiling", max: 999, color: "#ef4444" }'
                '  ];'
                '  function lucideSvg(inner) {'
                '    return \'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">\' + inner + "</svg>";'
                '  }'
                '  function stageForTemp(val) {'
                '    var n = Number(val);'
                '    if (!isFinite(n)) n = 80;'
                '    for (var i = 0; i < TEMP_STAGES.length; i++) {'
                '      if (n <= TEMP_STAGES[i].max) return TEMP_STAGES[i].id;'
                '    }'
                '    return "boiling";'
                '  }'
                '  function enhancePositionControl() {'
                '    document.querySelectorAll(".bws-pos-card-hint").forEach(function(el) { el.remove(); });'
                '    document.querySelectorAll(".bws-pos-puck").forEach(function(puck) {'
                '      if (puck.dataset.senchadoCup === "1") return;'
                '      puck.dataset.senchadoCup = "1";'
                '      puck.innerHTML = lucideSvg(ICONS.coffee);'
                '    });'
                '  }'
                '  function currentPreviewVariant() {'
                '    var activeBtn = document.querySelector(".bws-preview-variants button.is-active");'
                '    if (activeBtn && activeBtn.dataset.variant) return activeBtn.dataset.variant;'
                '    if (typeof BENTO_SETTINGS_CONTEXT === "object" && BENTO_SETTINGS_CONTEXT && BENTO_SETTINGS_CONTEXT.previewVariant) {'
                '      return String(BENTO_SETTINGS_CONTEXT.previewVariant);'
                '    }'
                '    return "reviewer";'
                '  }'
                '  function syncWidgetVariantSections() {'
                '    var variant = currentPreviewVariant();'
                '    var isReviewer = variant === "reviewer";'
                '    var mainField = document.querySelector(\'.bws-field[data-path="ui_settings.widget_style"]\');'
                '    var revField = document.querySelector(\'.bws-field[data-path="ui_settings.reviewer_position"]\');'
                '    if (mainField && revField) {'
                '      var mainSec = mainField.closest("#bwsPage > *") || mainField.closest("section, .bws-section, .bws-card");'
                '      var revSec = revField.closest("#bwsPage > *") || revField.closest("section, .bws-section, .bws-card");'
                '      if (mainSec && revSec && mainSec !== revSec) {'
                '        mainSec.classList.toggle("senchado-variant-hidden", isReviewer);'
                '        revSec.classList.toggle("senchado-variant-hidden", !isReviewer);'
                '      }'
                '    }'
                '    if (revField) {'
                '      revField.classList.toggle("senchado-pos-hidden", !isReviewer);'
                '    }'
                '  }'
                '  function enhanceTemperatureSlider() {'
                '    var row = document.querySelector(\'.bws-field[data-path="current_tea.temperature"]\');'
                '    if (!row) return;'
                '    var slider = row.querySelector(".bws-slider");'
                '    var output = row.querySelector(".bws-value");'
                '    if (!slider || !output || slider.dataset.senchadoTempIcon === "1") return;'
                '    slider.dataset.senchadoTempIcon = "1";'
                '    slider.classList.add("senchado-has-temp-icon");'
                '    var stack = document.createElement("span");'
                '    stack.className = "senchado-temp-icon-stack";'
                '    stack.setAttribute("aria-hidden", "true");'
                '    TEMP_STAGES.forEach(function(st) {'
                '      var layer = document.createElement("span");'
                '      layer.className = "senchado-temp-icon-layer";'
                '      layer.dataset.stage = st.id;'
                '      layer.style.color = st.color;'
                '      layer.innerHTML = lucideSvg(ICONS[st.id]);'
                '      stack.appendChild(layer);'
                '    });'
                '    slider.insertBefore(stack, output);'
                '    function updateIcon() {'
                '      var raw = slider.getAttribute("aria-valuenow");'
                '      if (raw == null || raw === "") raw = parseFloat(output.textContent);'
                '      var activeId = stageForTemp(raw);'
                '      if (stack.dataset.activeStage === activeId) return;'
                '      stack.dataset.activeStage = activeId;'
                '      stack.querySelectorAll(".senchado-temp-icon-layer").forEach(function(layer) {'
                '        layer.classList.toggle("is-active", layer.dataset.stage === activeId);'
                '      });'
                '    }'
                '    updateIcon();'
                '    var obs = new MutationObserver(updateIcon);'
                '    obs.observe(slider, { attributes: true, attributeFilter: ["aria-valuenow"] });'
                '  }'
                '  function applyAll() {'
                '    enhancePositionControl();'
                '    syncWidgetVariantSections();'
                '    enhanceTemperatureSlider();'
                '  }'
                '  applyAll();'
                '  var pageHost = document.getElementById("bwsPage");'
                '  if (pageHost) {'
                '    new MutationObserver(applyAll).observe(pageHost, { childList: true, subtree: false });'
                '  }'
                '  document.addEventListener("click", function(ev) {'
                '    if (ev.target && ev.target.closest && (ev.target.closest(".bws-preview-variants") || ev.target.closest(".bws-nav-btn"))) {'
                '      requestAnimationFrame(applyAll);'
                '    }'
                '  }, true);'
                '})();</script>'
            )

        def _apply_patch(self, patch):
            if isinstance(patch, dict) and patch and all(
                str(key).startswith("current_tea.") for key in patch
            ):
                prev_cb = self.preview_callback
                self.preview_callback = lambda *_args: ""
                try:
                    result = super()._apply_patch(patch)
                finally:
                    self.preview_callback = prev_cb
                if isinstance(result, dict):
                    result.pop("preview", None)
                return result
            return super()._apply_patch(patch)

        def normalize_patch(self, patch):
            if "ui_settings.widget_glass_strength" in patch:
                self.config.setdefault("ui_settings", {})["widget_glass"] = bool(
                    float(patch["ui_settings.widget_glass_strength"] or 0) > 0
                )
            return patch

        def _refresh_favorite_fields(self):
            favorites = self.config.get("favorites", []) or []
            summary = (
                f"{len(favorites)} saved configuration"
                f"{'s' if len(favorites) != 1 else ''}."
            )
            self.config["_favorites_summary"] = summary
            fields = [
                _bws.field(
                    "_favorites_summary", "Saved recipes", "info",
                    default=summary,
                ),
                _bws.field(
                    "save-current-favorite", "Save current recipe", "action",
                    button_label="Save current configuration",
                ),
            ]
            for index, favorite in enumerate(favorites):
                tea = TEAS.get(favorite.get("flavor_id"))
                recipe = (
                    f"{favorite.get('task_name', 'Study Session')} · "
                    f"{tea.name if tea else 'Tea'} · "
                    f"{int(favorite.get('prep_time', 0)) // 60} min prep · "
                    f"{int(favorite.get('brew_time', 0)) // 60} min brew"
                )
                key = f"_favorite_{index}"
                self.config[key] = recipe
                fields.extend([
                    _bws.field(
                        key, f"Recipe {index + 1}", "info", default=recipe
                    ),
                    _bws.field(
                        f"load-favorite:{index}", f"Load recipe {index + 1}",
                        "action", button_label="Load",
                    ),
                    _bws.field(
                        f"delete-favorite:{index}",
                        f"Delete recipe {index + 1}", "action",
                        button_label="Delete",
                    ),
                ])
            for page_spec in self.pages:
                if page_spec.get("id") == "favorites":
                    page_spec["sections"][0]["fields"] = fields
                    break

        def handle_action(self, action):
            if action == "save-current-favorite":
                self.config.setdefault("favorites", []).append(deepcopy(self.config.get("current_tea", {})))
            elif action.startswith("load-favorite:"):
                index = int(action.partition(":")[2])
                favorite = self.config.get("favorites", [])[index]
                self.config["current_tea"] = deepcopy(favorite)
            elif action.startswith("delete-favorite:"):
                index = int(action.partition(":")[2])
                self.config.get("favorites", []).pop(index)
            else:
                return {"ok": False, "error": "Unknown favorite action"}
            self._refresh_favorite_fields()
            self._save()
            return {"ok": True}
