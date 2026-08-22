"""
Full-screen (panel-filling) image viewer with a before/after color
correction compare slider.
"""

import os
import cv2
from PyQt6.QtCore import Qt, QObject, QRunnable, QThreadPool, QRect, QPointF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QRadialGradient
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QStackedLayout
)

from src.core.image_enhancement import get_enhancement_function
from src.utils.ui_utils import cv2_to_qpixmap

HANDLE_HIT_RADIUS = 16  # px on either side of the divider that counts as "grabbing" it


class CompareSliderWidget(QWidget):
    """Before/after reveal slider: drag the handle left-right to wipe
    between the 'before' (right side) and 'after' (left side) image."""

    def __init__(self, before_pixmap, after_pixmap, parent=None):
        super().__init__(parent)
        self._before_source = before_pixmap
        self._after_source = after_pixmap
        self._before_scaled = before_pixmap
        self._after_scaled = after_pixmap
        self._handle_ratio = 0.5  # 0 = fully "before", 1 = fully "after"
        self._dragging = False
        self.setMouseTracking(True)
        self.setMinimumSize(200, 200)

    def set_images(self, before_pixmap, after_pixmap):
        self._before_source = before_pixmap
        self._after_source = after_pixmap
        self._rescale()
        self.update()

    def reset_handle(self):
        self._handle_ratio = 0.5
        self.update()

    def _rescale(self):
        target = self.size()
        if target.width() <= 0 or target.height() <= 0:
            return
        self._before_scaled = self._before_source.scaled(
            target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self._after_scaled = self._after_source.scaled(
            target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _image_rect(self):
        """Centered rect the (equal-size) before/after pixmaps are drawn into."""
        pw, ph = self._before_scaled.width(), self._before_scaled.height()
        x = (self.width() - pw) // 2
        y = (self.height() - ph) // 2
        return QRect(x, y, pw, ph)

    def _divider_x(self, rect):
        return rect.x() + int(rect.width() * self._handle_ratio)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self._image_rect()
        painter.drawPixmap(rect, self._before_scaled)

        divider_x = self._divider_x(rect)
        if divider_x > rect.x():
            painter.setClipRect(QRect(rect.x(), rect.y(), divider_x - rect.x(), rect.height()))
            painter.drawPixmap(rect, self._after_scaled)
            painter.setClipping(False)

        # Divider line + grip handle: plain white, no border -- depth comes
        # from a soft drop shadow instead, so the grip blends into the line
        # rather than reading as a bordered dot sitting on top of it.
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        white = QColor("#FFFFFF")
        shadow_color = QColor(0, 0, 0, 45)

        shadow_offset = 1.5
        shadow_pen = QPen(shadow_color)
        shadow_pen.setWidth(3)
        painter.setPen(shadow_pen)
        # QPointF (not the plain-int drawLine overload): shadow_offset is a
        # float, and mixing int/float args on the 4-int-argument overload
        # raises inside paintEvent, which PyQt6 has no safe way to recover
        # from -- it takes the whole process down without a Python traceback.
        painter.drawLine(
            QPointF(divider_x + shadow_offset, rect.y()),
            QPointF(divider_x + shadow_offset, rect.y() + rect.height()),
        )

        line_pen = QPen(white)
        line_pen.setWidth(2)
        painter.setPen(line_pen)
        painter.drawLine(divider_x, rect.y(), divider_x, rect.y() + rect.height())

        grip_radius = 10
        grip_y = rect.y() + rect.height() // 2

        # Wider, gentler falloff (extra mid-stop) reads as a soft glow
        # rather than a hard dark ring around the handle.
        shadow_radius = grip_radius + 14
        shadow_center = QPointF(divider_x + shadow_offset, grip_y + shadow_offset)
        shadow_gradient = QRadialGradient(shadow_center, shadow_radius)
        shadow_gradient.setColorAt(0.0, QColor(0, 0, 0, 70))
        shadow_gradient.setColorAt(0.5, QColor(0, 0, 0, 30))
        shadow_gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_gradient))
        painter.drawEllipse(shadow_center, shadow_radius, shadow_radius)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(white))
        painter.drawEllipse(divider_x - grip_radius, grip_y - grip_radius, grip_radius * 2, grip_radius * 2)

    def _on_handle(self, x, rect):
        return abs(x - self._divider_x(rect)) <= HANDLE_HIT_RADIUS

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._on_handle(
            event.position().toPoint().x(), self._image_rect()
        ):
            self._dragging = True

    def mouseMoveEvent(self, event):
        if self._dragging:
            rect = self._image_rect()
            if rect.width() > 0:
                ratio = (event.position().toPoint().x() - rect.x()) / rect.width()
                self._handle_ratio = max(0.0, min(1.0, ratio))
                self.update()

    def mouseReleaseEvent(self, event):
        self._dragging = False


class _EnhancementSignals(QObject):
    result_ready = pyqtSignal(object, int)  # enhanced BGR numpy array, generation
    failed = pyqtSignal(str, int)  # message, generation


class _EnhancementTask(QRunnable):
    """Runs a color-correction method off the GUI thread."""

    def __init__(self, cv2_image, method_fn, params, generation, signals):
        super().__init__()
        self.cv2_image = cv2_image
        self.method_fn = method_fn
        self.params = params
        self.generation = generation
        self.signals = signals

    def run(self):
        try:
            result = self.method_fn(self.cv2_image, **self.params)
        except Exception as e:
            self.signals.failed.emit(str(e), self.generation)
            return
        self.signals.result_ready.emit(result, self.generation)


class ImageViewerOverlay(QWidget):
    """Fills the app window when open: shows the clicked image, lets the
    user run color correction, then reveals a before/after compare slider."""

    closed = pyqtSignal()

    def __init__(self, method_provider=None):
        """method_provider: optional callable returning (method_key, params)
        for whatever's currently selected in the main panel -- so the
        preview here always matches what the real batch run would do.
        Defaults to always-CLAHE-with-defaults if not supplied."""
        super().__init__()
        self.setObjectName("imageViewerOverlay")
        self._method_provider = method_provider or (lambda: ("clahe", {}))
        # Needed so this widget (rather than whatever had focus in the
        # gallery/controls panel) actually receives the Esc key press.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._image_path = None
        self._cv2_image = None
        self._before_pixmap = None
        self._slider = None
        self._generation = 0  # bumped on each open_image(); guards stale results
        self._alive = True  # set False on shutdown() so late signals no-op
        # A dedicated pool, deliberately NOT QThreadPool.globalInstance():
        # that instance is shared with the gallery's bulk background
        # thumbnail loading (src/ui/gallery.py), so an interactive,
        # latency-sensitive "Run Color Correction" click would otherwise
        # queue behind however many thumbnail jobs are still in flight.
        self._threadpool = QThreadPool()
        self._threadpool.setMaxThreadCount(1)
        self._signals = _EnhancementSignals()
        self._signals.result_ready.connect(self._on_enhancement_ready)
        self._signals.failed.connect(self._on_enhancement_failed)

        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Top bar: filename + close button
        top_bar = QHBoxLayout()
        self._filename_label = QLabel()
        self._filename_label.setObjectName("sectionLabel")
        top_bar.addWidget(self._filename_label)
        top_bar.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close_viewer)
        top_bar.addWidget(close_btn)
        outer.addLayout(top_bar)

        # Image area: a stacked layout, before/plain preview OR compare slider
        self._image_container = QWidget()
        self._image_stack = QStackedLayout(self._image_container)
        self._plain_preview = QLabel()
        self._plain_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_stack.addWidget(self._plain_preview)
        outer.addWidget(self._image_container, stretch=1)

        # Bottom control strip
        controls = QHBoxLayout()
        self._status_label = QLabel("")
        self._status_label.setObjectName("sectionLabel")
        # Without word wrap, QLabel's minimumSizeHint demands enough width
        # to fit its longest-ever text on one line -- once this got set to
        # a long status message, that dragged the whole window's minimum
        # width up with it, growing the top-level window on the spot.
        self._status_label.setWordWrap(True)
        # Pin the height too (room for 2 lines), so switching between an
        # empty status and a longer one doesn't itself resize the layout.
        self._status_label.setFixedHeight(2 * self._status_label.fontMetrics().lineSpacing())
        controls.addWidget(self._status_label)
        controls.addStretch()
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        self._reset_btn.setEnabled(False)
        controls.addWidget(self._reset_btn)
        self._run_btn = QPushButton("Run Color Correction")
        self._run_btn.setObjectName("processButton")
        self._run_btn.clicked.connect(self._on_run_clicked)
        controls.addWidget(self._run_btn)
        outer.addLayout(controls)

    def open_image(self, image_path):
        """Load and display `image_path` as the 'before' image, ready to
        run color correction against."""
        self._generation += 1  # invalidate any enhancement task still in flight
        self._image_path = image_path
        self._filename_label.setText(os.path.basename(image_path))
        self._status_label.setText("")
        self._run_btn.setEnabled(False)
        self._reset_btn.setEnabled(False)

        self._cv2_image = cv2.imread(image_path)
        if self._cv2_image is None:
            self._status_label.setText("Could not load image.")
            return

        self._before_pixmap = cv2_to_qpixmap(self._cv2_image)
        self._refresh_plain_preview()
        self._image_stack.setCurrentWidget(self._plain_preview)
        if self._slider is not None:
            self._image_stack.removeWidget(self._slider)
            self._slider.deleteLater()
            self._slider = None
        self._run_btn.setEnabled(True)

    def _refresh_plain_preview(self):
        """Rescale the pre-correction preview to the container's *current*
        size. Needed in addition to the one-shot call in open_image():
        when the viewer is opened for the first time, content_stack hasn't
        switched to it yet at that point, so _image_container can still
        report a stale/default size — the resizeEvent below catches that
        once real layout geometry is assigned. Keeps this in lockstep with
        CompareSliderWidget, which fills the same area the same way, so
        the image doesn't visibly change size when correction is run."""
        if self._before_pixmap is None:
            return
        self._plain_preview.setPixmap(
            self._before_pixmap.scaled(
                self._image_container.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_plain_preview()

    def _on_run_clicked(self):
        if self._cv2_image is None:
            return
        self._run_btn.setEnabled(False)
        self._status_label.setText("Running color correction...")
        method_key, params = self._method_provider()
        method_fn = get_enhancement_function(method_key)
        task = _EnhancementTask(
            self._cv2_image, method_fn, params, self._generation, self._signals
        )
        self._threadpool.start(task)

    def _on_enhancement_ready(self, enhanced_bgr, generation):
        if not self._alive or generation != self._generation:
            return  # a different (or closed) image was opened while this ran
        after_pixmap = cv2_to_qpixmap(enhanced_bgr)
        if self._slider is None:
            self._slider = CompareSliderWidget(self._before_pixmap, after_pixmap)
            self._image_stack.addWidget(self._slider)
        else:
            self._slider.set_images(self._before_pixmap, after_pixmap)
        self._slider.reset_handle()
        self._image_stack.setCurrentWidget(self._slider)
        self._status_label.setText("Drag the divider to compare before/after.")
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(True)

    def _on_enhancement_failed(self, message, generation):
        if not self._alive or generation != self._generation:
            return
        self._status_label.setText(f"Color correction failed: {message}")
        self._run_btn.setEnabled(True)

    def _on_reset_clicked(self):
        if self._slider is not None:
            self._slider.reset_handle()

    def close_viewer(self):
        self.closed.emit()

    def shutdown(self):
        """Stop reacting to any enhancement result and wait briefly for a
        running job to finish. The _alive flag is the real safety net --
        it's set first so a straggling result is a no-op even if
        waitForDone's timeout is hit before the job actually completes.
        Call on application close."""
        self._alive = False
        self._threadpool.clear()
        self._threadpool.waitForDone(2000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close_viewer()
        else:
            super().keyPressEvent(event)
