"""
Application configuration and constants.
"""

import os
import multiprocessing

# Application metadata
APP_NAME = "GPSP Image Processor"
APP_VERSION = "1.0"
APP_DATE = "September 2024"
CONTACT_EMAIL = "matteo.collina@vuw.ac.nz"

# File handling
VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
TEMP_FOLDER = "TempImages"

# Processing defaults
DEFAULT_CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_THREADS = max(4, min(DEFAULT_CPU_COUNT - 2, 12))
MAX_THREADS = 32
MIN_THREADS = 1

# Asset paths
ASSETS_DIR = "assets"
APP_ICON = os.path.join(ASSETS_DIR, "app_icon.png")
UNIVERSITY_LOGO = os.path.join(ASSETS_DIR, "university_logo.png")
GOPRO_QR_CODE = os.path.join(ASSETS_DIR, "gopro_qr_code.png")

# UI settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
LEFT_PANEL_WIDTH = 400
IMAGE_PREVIEW_MIN_WIDTH = 600
IMAGE_PREVIEW_MIN_HEIGHT = 400

# Documentation URL
DOCUMENTATION_URL = "https://www.google.com"

# About text
ABOUT_TEXT = """GPSP Image Processor
A Victoria University of Wellington project
Developed by Seammetry

CREDITS:
Software Development: Matteo Collina
Testing: Manon Payne Broadribb, Miriam Pierotti
Supervision: Prof. James Bell

Version: {version}
Date: {date}
Contact: {contact}""".format(
    version=APP_VERSION,
    date=APP_DATE,
    contact=CONTACT_EMAIL
)

# GoPro settings text
GOPRO_SETTINGS_TEXT = """SETTINGS

White-Balance: Auto


YOU NEED THE LABS FIRMWARE IN ORDER TO USE IT. PLEASE, REFER TO DOCUMENTATION.

PLEASE, REMEMBER TO TURN ON INTERVALOMETER FUNCTION ON THE GOPRO."""
