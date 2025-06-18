"""
Custom dialog windows for the application.
"""

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from config.settings import GOPRO_QR_CODE, ABOUT_TEXT, GOPRO_SETTINGS_TEXT


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
