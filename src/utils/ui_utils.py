"""
UI utility functions.

"""


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


def cv2_to_qpixmap(cv2_img):
    """Convert an in-memory BGR OpenCV image to a QPixmap, no temp files."""
    import cv2
    from PyQt6.QtGui import QPixmap, QImage

    rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb_img.shape
    bytes_per_line = ch * w
    q_image = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
    # .copy(): rgb_img's buffer must not be freed once this function returns
    return QPixmap.fromImage(q_image.copy())


