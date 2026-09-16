"""Dark "liquid glass" theme for the RSP Metashape plugin, mirroring
src/ui/theme.py (the main RSP desktop app's PyQt6 theme) by value, since
this plugin can't depend on PyQt6. Must import cleanly with no Qt binding
available; only apply_theme() requires one.
"""

from .qt import QtWidgets, QT_BINDING  # noqa: F401  (re-exported for callers)


class Palette:

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


def build_stylesheet() -> str:
    """QSS for this plugin's own QDialogs."""
    p = Palette
    return f"""
    QDialog, QWidget {{
        background-color: {p.bg_base};
        color: {p.text_primary};
        font-size: 10.5pt;
    }}

    QLabel {{
        background: transparent;
    }}

    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
        background-color: {p.bg_input};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_control}px;
        padding: 5px 8px;
        selection-background-color: {p.accent};
        selection-color: {p.bg_base};
    }}
    QLineEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover, QComboBox:hover {{
        background-color: {p.bg_input_hover};
    }}
    QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{
        border: 1px solid {p.accent};
    }}
    QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled, QComboBox:disabled {{
        color: {p.text_disabled};
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

    QTableWidget {{
        background-color: {p.bg_panel};
        alternate-background-color: {p.bg_elevated};
        gridline-color: {p.border_subtle};
        border: 1px solid {p.border_subtle};
        border-radius: {p.radius_card}px;
        selection-background-color: {p.accent_glow};
        selection-color: {p.text_primary};
    }}
    QTableWidget::item {{
        padding: 4px 6px;
    }}
    QHeaderView::section {{
        background-color: {p.bg_elevated};
        color: {p.text_secondary};
        padding: 6px 8px;
        border: none;
        border-bottom: 1px solid {p.border_subtle};
        font-weight: 600;
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
    """


def apply_theme(widget) -> None:
    """Apply the plugin's QSS to one dialog/widget."""
    if QtWidgets is None:
        raise RuntimeError("No Qt binding (PySide6/PySide2) is available; cannot apply the theme.")
    widget.setStyleSheet(build_stylesheet())
