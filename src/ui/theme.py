"""
Dark, "liquid glass"-inspired theme for the RSP application.

"""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication


class Palette:
    """Central color/metric palette. Single source of truth for all theming."""

    # Surfaces (dark base -> elevated "glass" cards)
    bg_base = "#0F1115"
    bg_panel = "#161920"
    bg_panel_glass = "rgba(22, 25, 32, 0.72)"
    bg_elevated = "#1E222B"
    bg_elevated_glass = "rgba(30, 34, 43, 0.80)"
    bg_input = "rgba(255, 255, 255, 0.06)"
    bg_input_hover = "rgba(255, 255, 255, 0.10)"

    # Borders / hairlines
    border_subtle = "rgba(255, 255, 255, 0.08)"
    border_strong = "rgba(255, 255, 255, 0.16)"

    # Text
    text_primary = "#E8EAED"
    text_secondary = "#9AA0AA"
    text_disabled = "#5B606B"

    # Accents
    accent = "#2FD1C6"
    accent_hover = "#4FE0D6"
    accent_pressed = "#26A99F"
    accent_glow = "rgba(47, 209, 198, 0.35)"

    error = "#E5484D"

    # Metrics
    radius_panel = 16
    radius_card = 12
    radius_control = 8


def _qcolor(hex_or_rgba: str) -> QColor:
    """Best-effort QColor from a hex string (QPalette needs opaque colors)."""
    if hex_or_rgba.startswith("#"):
        return QColor(hex_or_rgba)
    # rgba(...) strings are QSS-only; fall back to a solid approximation.
    return QColor(Palette.bg_panel)


def build_qpalette() -> QPalette:
    """Fallback QPalette so native chrome (QFileDialog, tooltips, menus)
    that QSS doesn't fully reach still matches the dark theme."""
    palette = QPalette()
    p = Palette
    palette.setColor(QPalette.ColorRole.Window, _qcolor(p.bg_base))
    palette.setColor(QPalette.ColorRole.WindowText, _qcolor(p.text_primary))
    palette.setColor(QPalette.ColorRole.Base, _qcolor(p.bg_elevated))
    palette.setColor(QPalette.ColorRole.AlternateBase, _qcolor(p.bg_panel))
    palette.setColor(QPalette.ColorRole.ToolTipBase, _qcolor(p.bg_elevated))
    palette.setColor(QPalette.ColorRole.ToolTipText, _qcolor(p.text_primary))
    palette.setColor(QPalette.ColorRole.Text, _qcolor(p.text_primary))
    palette.setColor(QPalette.ColorRole.Button, _qcolor(p.bg_elevated))
    palette.setColor(QPalette.ColorRole.ButtonText, _qcolor(p.text_primary))
    palette.setColor(QPalette.ColorRole.BrightText, _qcolor(p.error))
    palette.setColor(QPalette.ColorRole.Link, _qcolor(p.accent))
    palette.setColor(QPalette.ColorRole.Highlight, _qcolor(p.accent))
    palette.setColor(QPalette.ColorRole.HighlightedText, _qcolor(p.bg_base))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, _qcolor(p.text_disabled))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, _qcolor(p.text_disabled))
    return palette


def build_stylesheet() -> str:
    p = Palette
    return f"""
    QMainWindow, QDialog {{
        background-color: {p.bg_base};
        color: {p.text_primary};
    }}

    QWidget {{
        color: {p.text_primary};
        font-size: 10.5pt;
    }}

    QMenuBar {{
        background-color: {p.bg_base};
        color: {p.text_primary};
        border-bottom: 1px solid {p.border_subtle};
    }}
    QMenuBar::item:selected {{
        background-color: {p.bg_input_hover};
        border-radius: {p.radius_control}px;
    }}
    QMenu {{
        background-color: {p.bg_elevated};
        color: {p.text_primary};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_card}px;
    }}
    QMenu::item:selected {{
        background-color: {p.bg_input_hover};
    }}

    QWidget#leftPanel {{
        background-color: {p.bg_panel_glass};
        border-right: 1px solid {p.border_subtle};
    }}

    QWidget#galleryPanel, QWidget#rightPanel {{
        background-color: {p.bg_base};
    }}

    QLabel {{
        background: transparent;
    }}
    QLabel#sectionLabel {{
        color: {p.text_secondary};
        font-weight: 600;
    }}
    QLabel#panelHeader {{
        color: {p.accent};
        font-size: 10.5pt;
        font-weight: 700;
        letter-spacing: 1px;
        padding-bottom: 2px;
        border-bottom: 1px solid {p.border_subtle};
    }}
    QLabel#deviceStatusBar {{
        color: {p.text_secondary};
        background-color: {p.bg_elevated};
        border-top: 1px solid {p.border_subtle};
        padding: 5px 8px;
        font-size: 8.5pt;
    }}

    QLabel#pathDisplay {{
        background-color: {p.bg_input};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_control}px;
        padding: 6px 10px;
        color: {p.text_secondary};
    }}
    QLabel#pathDisplay[hasPath="true"] {{
        color: {p.text_primary};
        border: 1px solid {p.accent};
    }}
    QLabel#pathDisplay[dragActive="true"] {{
        border: 2px dashed {p.accent};
        background-color: {p.accent_glow};
    }}

    QLineEdit, QSpinBox, QComboBox {{
        background-color: {p.bg_input};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_control}px;
        padding: 5px 8px;
        selection-background-color: {p.accent};
        selection-color: {p.bg_base};
    }}
    QLineEdit:hover, QSpinBox:hover, QComboBox:hover {{
        background-color: {p.bg_input_hover};
    }}
    QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {p.accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border_subtle};
        selection-background-color: {p.bg_input_hover};
        outline: none;
    }}

    QPushButton {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_control}px;
        padding: 6px 14px;
        color: {p.text_primary};
    }}
    QPushButton:hover {{
        background-color: {p.bg_input_hover};
        border: 1px solid {p.border_strong};
    }}
    QPushButton:pressed {{
        background-color: {p.bg_input};
    }}
    QPushButton:disabled {{
        color: {p.text_disabled};
        border: 1px solid {p.border_subtle};
    }}

    QPushButton#compactButton {{
        padding: 6px 6px;
        font-size: 9pt;
        font-weight: 600;
    }}

    QPushButton#processButton {{
        background-color: {p.accent};
        color: {p.bg_base};
        border: none;
        border-radius: {p.radius_control}px;
        font-weight: 700;
    }}
    QPushButton#processButton:hover {{
        background-color: {p.accent_hover};
    }}
    QPushButton#processButton:pressed {{
        background-color: {p.accent_pressed};
    }}
    QPushButton#processButton:disabled {{
        background-color: {p.bg_elevated};
        color: {p.text_disabled};
    }}

    QCheckBox {{
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {p.border_strong};
        background-color: {p.bg_input};
    }}
    QCheckBox::indicator:checked {{
        background-color: {p.accent};
        border: 1px solid {p.accent};
    }}

    QProgressBar {{
        background-color: {p.bg_input};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_control}px;
        text-align: center;
        color: {p.text_primary};
    }}
    QProgressBar::chunk {{
        background-color: {p.accent};
        border-radius: {p.radius_control}px;
    }}

    QTabWidget::pane {{
        background-color: {p.bg_panel};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_panel}px;
        top: -1px;
    }}
    QTabBar::tab {{
        background-color: transparent;
        color: {p.text_secondary};
        padding: 8px 18px;
        margin-right: 4px;
        border-top-left-radius: {p.radius_control}px;
        border-top-right-radius: {p.radius_control}px;
    }}
    QTabBar::tab:selected {{
        background-color: {p.bg_elevated_glass};
        color: {p.text_primary};
        border-bottom: 2px solid {p.accent};
    }}
    QTabBar::tab:hover:!selected {{
        color: {p.text_primary};
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background: {p.bg_input};
        border-radius: 2px;
    }}
    QSlider::sub-page:horizontal {{
        background: {p.accent};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        background: {p.text_primary};
        width: 14px;
        height: 14px;
        margin: -6px 0;
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {p.accent_hover};
    }}

    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {p.border_strong};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p.accent};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 10px;
        margin: 0;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.border_strong};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {p.accent};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0;
    }}

    QSplitter::handle {{
        background-color: {p.border_subtle};
    }}
    QSplitter::handle:hover {{
        background-color: {p.accent};
    }}

    QWidget#thumbnailCard {{
        background-color: {p.bg_elevated};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_card}px;
    }}
    QWidget#thumbnailCard:hover {{
        border: 1px solid {p.accent};
    }}
    QLabel#thumbnailImage {{
        background-color: {p.bg_input};
        border-radius: {p.radius_control}px;
    }}
    QLabel#thumbnailCaption {{
        color: {p.text_secondary};
        font-size: 9pt;
    }}

    QToolTip {{
        background-color: {p.bg_elevated};
        color: {p.text_primary};
        border: 1px solid {p.border_subtle};
        padding: 4px 8px;
        border-radius: {p.radius_control}px;
    }}
    """


def apply_theme(app: QApplication) -> None:
    """Apply the dark theme to the whole application.

    Call after app.setStyle('Fusion') so QSS renders consistently
    cross-platform; sets a matching QPalette first as a fallback layer for
    native chrome QSS doesn't fully reach (e.g. QFileDialog, tooltips).
    """
    app.setPalette(build_qpalette())
    app.setStyleSheet(build_stylesheet())
