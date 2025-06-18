"""
UI utility functions.
"""

from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt


def format_time(seconds):
    """Format time in seconds to a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {minutes}m {remaining_seconds:.1f}s"


def scale_pixmap_to_label(image_path, label_size):
    """Scale a pixmap to fit within a label while maintaining aspect ratio."""
    try:
        pixmap = QPixmap(image_path)
        scaled_pixmap = pixmap.scaled(
            label_size, 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        return scaled_pixmap
    except Exception as e:
        print(f"Warning: Could not scale image {image_path}: {e}")
        return None
