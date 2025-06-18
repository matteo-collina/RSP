#!/usr/bin/env python3
"""
GPSP Image Processor Application
Entry point for the application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from src.ui.main_window import ImageProcessor


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = ImageProcessor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
