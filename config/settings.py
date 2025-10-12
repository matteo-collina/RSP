"""
Application configuration and constants.
"""

import os
import sys
import multiprocessing

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Running in development mode
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# Application metadata
APP_NAME = "RSP Image Processor"
APP_VERSION = "0.2.1-dev"
APP_DATE = "July 2025"
CONTACT_EMAIL = "matteo.collina@vuw.ac.nz"

# File handling
VALID_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}

# Processing defaults
DEFAULT_CPU_COUNT = multiprocessing.cpu_count()

# Smart thread calculation based on CPU architecture
def calculate_optimal_threads():
    """Calculate optimal thread count for CPU-intensive image processing."""
    import platform
    import subprocess
    
    logical_cores = multiprocessing.cpu_count()
    
    # Apple Silicon - detect and use ALL Performance cores
    if platform.system() == 'Darwin' and platform.machine() == 'arm64':
        try:
            # Try to get Performance core count from system_profiler
            result = subprocess.run(['system_profiler', 'SPHardwareDataType'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'Total Number of Cores:' in line and 'performance' in line:
                        # Parse "16 (12 performance and 4 efficiency)"
                        parts = line.split('(')[1].split()
                        p_cores = int(parts[0])
                        # Use ALL Performance cores - they're designed for intensive tasks
                        return p_cores
        except Exception:
            pass
        
        # Fallback: estimate based on known Apple Silicon configs
        if logical_cores >= 16:      # M3 Max/M2 Max: typically 12P + 4E or 8P + 8E
            return logical_cores - 4  # Conservative estimate: assume 4 E-cores
        elif logical_cores >= 12:   # M2 Pro: typically 8P + 4E  
            return logical_cores - 4
        else:                       # M1/M2/M3: typically 4P + 4E
            return logical_cores // 2
    
    # Intel/AMD processors - assume hyperthreading, use physical cores
    else:
        # Most Intel/AMD use hyperthreading (2 logical per physical)
        # For CPU-intensive tasks, use estimated physical cores
        estimated_physical = max(1, logical_cores // 2)
        return estimated_physical

OPTIMAL_THREADS = calculate_optimal_threads()
MIN_THREADS = 1

# Set a reasonable upper limit to prevent UI issues
GUI_MAX_THREADS = 32

# Asset paths
ASSETS_DIR = get_resource_path("assets")
APP_ICON = os.path.join(ASSETS_DIR, "app_icon.png")
UNIVERSITY_LOGO = os.path.join(ASSETS_DIR, "university_logo.png")
GOPRO_QR_CODE = os.path.join(ASSETS_DIR, "gopro_qr_code.png")

# UI settings
WINDOW_WIDTH = 550
WINDOW_HEIGHT = 800
LEFT_PANEL_WIDTH = 400
IMAGE_PREVIEW_MIN_WIDTH = 600
IMAGE_PREVIEW_MIN_HEIGHT = 400

# Documentation URL
DOCUMENTATION_URL = "https://www.google.com"

# About text
ABOUT_TEXT = """RSP Image Processor
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
