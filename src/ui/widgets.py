"""
Custom widgets for the application.
"""

import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QLineEdit, QFileDialog, QCheckBox,
                            QProgressBar, QSpinBox, QComboBox, QAbstractSpinBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from config.settings import (LEFT_PANEL_WIDTH, OPTIMAL_THREADS, GUI_MAX_THREADS,
                           MIN_THREADS, DEFAULT_CPU_COUNT)
from src.core.image_enhancement import ENHANCEMENT_METHODS, METHOD_DISPLAY_NAMES


class DropTargetLabel(QLabel):
    """A path-display QLabel that also accepts a dropped folder from Explorer."""

    directory_dropped = pyqtSignal(str)

    def __init__(self, text=""):
        super().__init__(text)
        self.setAcceptDrops(True)

    def _dropped_directory(self, mime_data):
        """Return the first locally-dropped directory path, or None."""
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if url.isLocalFile():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    return path
        return None

    def dragEnterEvent(self, event):
        if self._dropped_directory(event.mimeData()):
            event.acceptProposedAction()
            self._set_drag_active(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        # Qt requires the most recent dragMoveEvent to be accepted, or the
        # drop is refused even though dragEnterEvent succeeded.
        if self._dropped_directory(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._set_drag_active(False)

    def dropEvent(self, event):
        self._set_drag_active(False)
        directory = self._dropped_directory(event.mimeData())
        if directory:
            event.acceptProposedAction()
            self.directory_dropped.emit(directory)
        else:
            event.ignore()

    def _set_drag_active(self, active):
        self.setProperty("dragActive", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class LeftPanel(QWidget):
    """Left panel containing controls and inputs."""

    # Fires whenever the enhancement checkbox or method combo changes, so
    # main_window can keep the external params panel (and its visibility)
    # and the compute-device status label in sync without LeftPanel needing
    # to know either of those exist.
    enhancement_selection_changed = pyqtSignal()


    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setObjectName("leftPanel")
        self.setFixedWidth(LEFT_PANEL_WIDTH)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the left panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(8)

        # Filename prefixes
        layout.addWidget(self._section_header("Prefixes"))

        self.prefix_inputs = []
        for i in range(1, 4):
            prefix_layout = QHBoxLayout()
            prefix_label = QLabel(f"{i}:")
            prefix_label.setFixedWidth(16)
            prefix_input = QLineEdit()
            prefix_layout.addWidget(prefix_label)
            prefix_layout.addWidget(prefix_input)
            layout.addLayout(prefix_layout)
            self.prefix_inputs.append(prefix_input)

        # The stretches between sections share whatever vertical space the
        # panel has left over, so the column stays filled top-to-bottom
        # (progress bar flush with the bottom edge) instead of piling all
        # the slack into a single gap. They collapse to nothing on short
        # windows, where the sections simply pack together again.
        layout.addStretch(1)

        # Directory selection
        layout.addWidget(self._section_header("Directories"))

        self.path_labels = {}
        self.browse_buttons = {}
        self.clear_buttons = {}

        for prefix in self.parent.paths:
            # Directory label
            dir_label = QLabel(prefix.capitalize())
            dir_label.setObjectName("sectionLabel")
            layout.addWidget(dir_label)

            # Path display (also a drag-and-drop target for a folder from Explorer)
            path_label = DropTargetLabel("No directory selected")
            path_label.setObjectName("pathDisplay")
            path_label.setProperty("hasPath", "false")
            path_label.directory_dropped.connect(
                lambda directory, p=prefix: self.set_directory(p, directory)
            )
            layout.addWidget(path_label)
            self.path_labels[prefix] = path_label

            # Buttons
            button_layout = QHBoxLayout()
            browse_btn = QPushButton("Browse")
            browse_btn.clicked.connect(lambda checked, p=prefix: self.browse_directory(p))
            clear_btn = QPushButton("Clear")
            clear_btn.clicked.connect(lambda checked, p=prefix: self.clear_directory(p))

            button_layout.addWidget(browse_btn)
            button_layout.addWidget(clear_btn)
            layout.addLayout(button_layout)

            self.browse_buttons[prefix] = browse_btn
            self.clear_buttons[prefix] = clear_btn

        # Clear all button
        clear_all_btn = QPushButton("Clear All Directories")
        clear_all_btn.clicked.connect(self.clear_all_directories)
        layout.addWidget(clear_all_btn)

        layout.addStretch(1)

        # Options
        layout.addWidget(self._section_header("Options"))

        self.enhancement_checkbox = QCheckBox("Image Enhancement")
        self.enhancement_checkbox.toggled.connect(self._on_enhancement_toggled)
        layout.addWidget(self.enhancement_checkbox)

        # Enhancement method selector (visible only when "Image Enhancement"
        # is checked). The chosen method's tunable parameters, if any,
        # live in a separate panel next to the gallery/viewer (see
        # AdaptiveGradingPanel in src/ui/enhancement_panel.py, owned and
        # placed by main_window.py) -- self.params_panel is set to that
        # external panel post-construction so get_enhancement_selection()
        # below has a single, consistent place to read current values from.
        self.enhancement_options = QWidget()
        options_layout = QVBoxLayout(self.enhancement_options)
        options_layout.setContentsMargins(16, 4, 0, 4)
        options_layout.setSpacing(6)

        method_layout = QHBoxLayout()
        method_label = QLabel("Method:")
        method_label.setObjectName("sectionLabel")
        self._method_keys = list(ENHANCEMENT_METHODS.keys())
        self.method_combo = QComboBox()
        self.method_combo.addItems([METHOD_DISPLAY_NAMES[k] for k in self._method_keys])
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo)
        options_layout.addLayout(method_layout)

        layout.addWidget(self.enhancement_options)
        self.enhancement_options.setVisible(False)
        self.params_panel = None  # set by main_window once the external panel exists

        self.rename_checkbox = QCheckBox("Rename Images")
        self.rename_checkbox.setChecked(True)
        layout.addWidget(self.rename_checkbox)

        # Sorting method selection
        sorting_layout = QHBoxLayout()
        sorting_label = QLabel("Sort images by:")
        self.sorting_combo = QComboBox()
        self.sorting_combo.addItems([
            "EXIF Date Taken (Recommended)", 
            "Filename (Alphabetical)", 
            "File Modification Time"
        ])
        self.sorting_combo.setToolTip("Choose how to sort images before renaming:\n"
                                    "• EXIF Date Taken: Uses camera timestamp (most accurate)\n"
                                    "• Filename: Alphabetical order\n"
                                    "• File Modification Time: When file was last modified")
        sorting_layout.addWidget(sorting_label)
        sorting_layout.addWidget(self.sorting_combo)
        layout.addLayout(sorting_layout)

        layout.addStretch(1)

        # Processing
        layout.addWidget(self._section_header("Processing"))

        # Thread count selection
        thread_layout = QHBoxLayout()
        thread_label = QLabel("Processing Threads:")
        self.thread_spinbox = QSpinBox()
        self.thread_spinbox.setMinimum(MIN_THREADS)
        self.thread_spinbox.setMaximum(GUI_MAX_THREADS)
        self.thread_spinbox.setValue(OPTIMAL_THREADS)
        self.thread_spinbox.setMaximumWidth(72)
        self.thread_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
        self.thread_spinbox.setToolTip(f"Number of threads for image enhancement\n"
                                     f"Detected {DEFAULT_CPU_COUNT} logical CPU cores\n"
                                     f"Default: {OPTIMAL_THREADS} threads (optimized for image processing)\n"
                                     f"Apple Silicon: Uses ALL Performance cores\n"
                                     f"Intel/AMD: Uses estimated physical cores (no hyperthreading)")

        # AUTO button to reset to optimal threads
        auto_btn = QPushButton("AUTO")
        auto_btn.setObjectName("compactButton")
        auto_btn.setMaximumWidth(72)
        auto_btn.setToolTip(f"Reset to optimal thread count ({OPTIMAL_THREADS} threads)\n"
                           f"Automatically optimized for your CPU architecture")
        auto_btn.clicked.connect(lambda: self.thread_spinbox.setValue(OPTIMAL_THREADS))

        thread_layout.addWidget(thread_label)
        thread_layout.addWidget(self.thread_spinbox)
        thread_layout.addWidget(auto_btn)
        layout.addLayout(thread_layout)

        # Process button
        self.process_btn = QPushButton("Process Images")
        self.process_btn.setObjectName("processButton")
        self.process_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.process_btn.setMinimumHeight(50)
        self.process_btn.clicked.connect(self.parent.process_images)
        layout.addWidget(self.process_btn)

        # Progress status and bar
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)  # Ensure percentage is visible
        layout.addWidget(self.progress_bar)

    def _section_header(self, text):
        """Build one of the panel's section titles ("Prefixes",
        "Directories", ...). They're what keeps the column readable now
        that the sections are spread over the panel's full height."""
        header = QLabel(text)
        header.setObjectName("panelHeader")
        return header
    
    def browse_directory(self, prefix):
        """Browse for a directory."""
        directory = QFileDialog.getExistingDirectory(self, f"Select {prefix} directory")
        if directory:
            self.set_directory(prefix, directory)

    def set_directory(self, prefix, directory):
        """Assign a directory to a prefix. Shared assignment path for both
        Browse and drag-and-drop, also refreshing that camera's gallery tab."""
        self.parent.paths[prefix] = directory
        label = self.path_labels[prefix]
        label.setText(directory)
        label.setProperty("hasPath", "true")
        label.style().unpolish(label)
        label.style().polish(label)
        self.parent.gallery_panel.set_directory(prefix, directory)

    def clear_directory(self, prefix):
        """Clear a directory selection."""
        self.parent.paths[prefix] = ""
        label = self.path_labels[prefix]
        label.setText("No directory selected")
        label.setProperty("hasPath", "false")
        label.style().unpolish(label)
        label.style().polish(label)
        self.parent.gallery_panel.set_directory(prefix, "")
    
    def clear_all_directories(self):
        """Clear all directory selections."""
        for prefix in self.parent.paths:
            self.clear_directory(prefix)

    def _on_enhancement_toggled(self, checked):
        self.enhancement_options.setVisible(checked)
        self.enhancement_selection_changed.emit()

    def _on_method_changed(self, index):
        self.enhancement_selection_changed.emit()

    def get_enhancement_selection(self):
        """Return (method_key, params_dict) for the currently selected
        enhancement method, read live from the UI controls. Used both by
        the real batch run and by the gallery/viewer preview, so the two
        never disagree about what "the selected method" means."""
        method_key = self._method_keys[self.method_combo.currentIndex()]
        if method_key == "gray_world" and self.params_panel is not None:
            return method_key, self.params_panel.get_params()
        return method_key, {}
