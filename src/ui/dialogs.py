"""
Custom dialog windows for the application.
"""

import os
import platform
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QMessageBox, QLineEdit, QFileDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from config.settings import (GOPRO_QR_CODE, ABOUT_TEXT, GOPRO_SETTINGS_TEXT,
                             METASHAPE_PLUGIN_SOURCE_DIR)
from src.core import metashape_plugin


class GoProDialog(QDialog):
    """Dialog showing GoPro QR code and settings."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GoPro QR Code")
        self.setWindowIcon(parent.windowIcon() if parent else None)
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Load and display QR code image
        if os.path.isfile(GOPRO_QR_CODE):
            image_label = QLabel()
            pixmap = QPixmap(GOPRO_QR_CODE)
            # Scale the QR code to a reasonable size
            scaled_pixmap = pixmap.scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio, 
                                        Qt.TransformationMode.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(image_label)
        
        # Add settings text
        text_label = QLabel(GOPRO_SETTINGS_TEXT)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        # Add OK button
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Set dialog size
        self.resize(500, 600)


class AboutDialog(QDialog):
    """About dialog showing application information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setWindowIcon(parent.windowIcon() if parent else None)
        self.setModal(True)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Add about text
        text_label = QLabel(ABOUT_TEXT)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)
        
        # Add OK button
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        # Set dialog size
        self.resize(400, 300)


class PluginInstallDialog(QDialog):
    """Install RSP Metashape Plugin: copies the RSP Metashape plugin into Metashape
    Pro's startup scripts folder for this OS (see src/core/metashape_plugin.py)."""

    _OS_NAMES = {"Windows": "Windows", "Darwin": "macOS", "Linux": "Linux"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Install RSP Metashape Plugin")
        self.setWindowIcon(parent.windowIcon() if parent else None)
        self.setModal(True)

        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)

        system = platform.system()
        heading = QLabel("Install RSP Metashape Plugin")
        heading_font = heading.font()
        heading_font.setBold(True)
        heading.setFont(heading_font)
        layout.addWidget(heading)

        layout.addWidget(QLabel(f"Detected operating system: {self._OS_NAMES.get(system, system)}"))

        layout.addWidget(QLabel("Metashape scripts folder:"))
        folder_row = QHBoxLayout()
        default_dir = metashape_plugin.default_scripts_dir()
        self.folder_edit = QLineEdit(str(default_dir) if default_dir else "")
        self.folder_edit.setPlaceholderText("Choose Metashape's scripts folder")
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_folder)
        folder_row.addWidget(self.folder_edit)
        folder_row.addWidget(browse_button)
        layout.addLayout(folder_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        self.install_button = QPushButton("Install")
        self.install_button.setObjectName("processButton")
        self.install_button.clicked.connect(self.install)
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        button_layout.addWidget(self.install_button)
        layout.addLayout(button_layout)

        self.setMinimumWidth(560)
        self._fit_height()

    def _fit_height(self):
        """Grow to the height the word-wrapped labels need at the current
        width; sizeHint() alone measures them at a wider width and clips."""
        width = max(self.width(), self.minimumWidth())
        self.resize(width, self.layout().totalHeightForWidth(width))

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Metashape scripts folder",
                                                  self.folder_edit.text())
        if folder:
            self.folder_edit.setText(folder)

    def install(self):
        target_dir = self.folder_edit.text().strip()
        if not target_dir:
            show_message_box(self, "No Folder", "Please choose Metashape's scripts folder.", "warning")
            return

        try:
            notes = metashape_plugin.install_plugin(METASHAPE_PLUGIN_SOURCE_DIR, target_dir)
        except (OSError, FileNotFoundError) as e:
            show_message_box(self, "Installation Failed", f"Could not install the plugin:\n{e}", "critical")
            return

        message = "\n".join(
            [f"RSP plugin installed in:\n{target_dir}"]
            + notes
            + ["Restart Metashape to see the RSP menu."]
        )
        self.status_label.setText(message)
        self._fit_height()
        show_message_box(self, "Plugin Installed", message)


def show_message_box(parent, title, message, icon_type="information"):
    """Show a message box with the specified parameters."""
    if icon_type == "information":
        QMessageBox.information(parent, title, message)
    elif icon_type == "warning":
        QMessageBox.warning(parent, title, message)
    elif icon_type == "critical":
        QMessageBox.critical(parent, title, message)
    elif icon_type == "question":
        return QMessageBox.question(parent, title, message)
