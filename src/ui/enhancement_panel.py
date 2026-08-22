"""
Right-side panel showing the currently selected enhancement method's
tunable parameters, next to the gallery/viewer content area. Only
populated/shown for methods that have parameters (currently: Adaptive
Grading / gray_world).
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea
)

from src.core.image_enhancement import DEFAULT_PARAMS, GRAY_WORLD_PARAM_SPECS
from src.ui.param_slider import EnhancementParamsPanel


class AdaptiveGradingPanel(QWidget):
    """Fixed-width side panel: title, parameter sliders, reset button."""

    def __init__(self):
        super().__init__()
        self.setObjectName("adaptiveGradingPanel")
        self.setFixedWidth(280)

        # Zero-margin outer layout so the footer status bar below can span
        # the panel's full width and sit flush against its bottom edge,
        # rather than living inside the same padded column as everything
        # else.
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        title = QLabel("Adaptive Grading Parameters")
        title.setObjectName("sectionLabel")
        title.setWordWrap(True)
        content_layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.params_panel = EnhancementParamsPanel(GRAY_WORLD_PARAM_SPECS, DEFAULT_PARAMS["gray_world"])
        scroll.setWidget(self.params_panel)
        content_layout.addWidget(scroll, stretch=1)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.params_panel.reset_to_defaults)
        content_layout.addWidget(reset_btn)

        outer.addWidget(content, stretch=1)

        # Footer: compute device Adaptive Grading will run on (CUDA/Metal/
        # CPU), full width, flush to the bottom edge. Populated lazily, the
        # first time this method is selected, not at app startup -- see
        # main_window's enhancement_selection_changed handler.
        self.device_status_label = QLabel("")
        self.device_status_label.setObjectName("deviceStatusBar")
        self.device_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.device_status_label)

    def get_params(self):
        return self.params_panel.get_params()
