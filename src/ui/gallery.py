"""
Thumbnail gallery: a tabbed (Left/Center/Right) grid of clickable image
thumbnails per camera folder, with background-loaded thumbnails so large
folders don't freeze the UI.
"""

import os
from PyQt6.QtCore import Qt, QObject, QRunnable, QThreadPool, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QGridLayout, QScrollArea, QTabWidget
)
from PIL import Image, ImageOps

from src.core.file_manager import FileManager

THUMB_SIZE = 140
THUMB_CARD_MARGIN = 16  # extra width/height a ThumbnailWidget adds around the image
THUMB_MAX_CONCURRENCY = 6


class _ThumbnailSignals(QObject):
    """QRunnable has no signals of its own; relay results through a QObject
    so the decoded image can be handed back to the GUI thread safely."""

    loaded = pyqtSignal(str, int, QImage)  # image_path, generation, image


class ThumbnailLoadTask(QRunnable):
    """Background job: decode + downscale one image for its thumbnail.

    Uses PIL's Image.thumbnail() (draft-mode capable JPEG decoding) rather
    than cv2.imread + resize, since it's substantially cheaper for
    downscaling large GoPro JPEGs.
    """

    def __init__(self, image_path, generation, signals):
        super().__init__()
        self.image_path = image_path
        self.generation = generation
        self.signals = signals

    def run(self):
        try:
            with Image.open(self.image_path) as im:
                im = ImageOps.exif_transpose(im)  # respect camera rotation
                im.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)
                im = im.convert("RGB")
                data = im.tobytes("raw", "RGB")
                qimage = QImage(
                    data, im.width, im.height, im.width * 3, QImage.Format.Format_RGB888
                ).copy()  # copy: 'data' buffer goes out of scope when run() returns
        except Exception:
            return
        self.signals.loaded.emit(self.image_path, self.generation, qimage)


class ThumbnailWidget(QWidget):
    """One clickable thumbnail card: image + filename caption."""

    clicked = pyqtSignal(str)  # image_path

    def __init__(self, image_path):
        super().__init__()
        self.image_path = image_path
        self.setObjectName("thumbnailCard")
        self.setFixedSize(THUMB_SIZE + THUMB_CARD_MARGIN, THUMB_SIZE + THUMB_CARD_MARGIN + 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(4)

        self.image_label = QLabel()
        self.image_label.setObjectName("thumbnailImage")
        self.image_label.setFixedSize(THUMB_SIZE, THUMB_SIZE)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        caption = QLabel()
        caption.setObjectName("thumbnailCaption")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fm = caption.fontMetrics()
        basename = os.path.basename(image_path)
        caption.setText(fm.elidedText(basename, Qt.TextElideMode.ElideMiddle, THUMB_SIZE))
        caption.setToolTip(basename)
        layout.addWidget(caption)

    def set_pixmap(self, pixmap):
        self.image_label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.image_path)
        super().mousePressEvent(event)


class CameraGalleryTab(QScrollArea):
    """Scrollable grid of thumbnails for one camera folder."""

    image_clicked = pyqtSignal(str)  # image_path

    def __init__(self, prefix):
        super().__init__()
        self.prefix = prefix
        self.setObjectName("galleryTab")
        self.setWidgetResizable(True)

        self._container = QWidget()
        self._grid = QGridLayout(self._container)
        self._grid.setSpacing(12)
        self._grid.setContentsMargins(16, 16, 16, 16)
        self.setWidget(self._container)

        threadpool = QThreadPool.globalInstance()
        if threadpool.maxThreadCount() > THUMB_MAX_CONCURRENCY:
            threadpool.setMaxThreadCount(THUMB_MAX_CONCURRENCY)
        self._threadpool = threadpool
        self._signals = _ThumbnailSignals()
        self._signals.loaded.connect(self._on_thumbnail_loaded)

        self._generation = 0
        self._cards = {}  # image_path -> ThumbnailWidget
        self._columns = 0
        self._directory = ""
        self._alive = True  # set False on shutdown() so late results no-op

        self._show_empty_state("No folder selected")

    def populate(self, directory):
        """List and display all images in `directory`, loading thumbnails
        in the background. Safe to call repeatedly (e.g. re-selecting the
        same or a different folder)."""
        self._directory = directory
        self._generation += 1
        generation = self._generation
        self._clear_grid()

        if not directory or not os.path.isdir(directory):
            self._show_empty_state("No folder selected")
            return

        try:
            files = FileManager.get_image_files_with_timestamps(directory, "filename")
        except OSError:
            files = []

        if not files:
            self._show_empty_state("No images found in this folder")
            return

        filenames = sorted(filename for filename, _ in files)
        self._columns = max(1, self._compute_columns())
        for index, filename in enumerate(filenames):
            image_path = os.path.join(directory, filename)
            card = ThumbnailWidget(image_path)
            card.clicked.connect(self.image_clicked.emit)
            row, col = divmod(index, self._columns)
            self._grid.addWidget(card, row, col)
            self._cards[image_path] = card

            self._threadpool.start(ThumbnailLoadTask(image_path, generation, self._signals))

    def _on_thumbnail_loaded(self, image_path, generation, qimage):
        if not self._alive or generation != self._generation:
            return  # stale result from a folder that's since been replaced (or shut down)
        card = self._cards.get(image_path)
        if card is None:
            return
        card.set_pixmap(QPixmap.fromImage(qimage))

    def shutdown(self):
        """Stop reacting to any in-flight thumbnail result. Call on
        application close, before draining the shared thread pool."""
        self._alive = False

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._cards = {}

    def _show_empty_state(self, text):
        self._clear_grid()
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._grid.addWidget(label, 0, 0)

    def _card_cell_width(self):
        return THUMB_SIZE + THUMB_CARD_MARGIN + self._grid.spacing()

    def _compute_columns(self):
        available = max(self.viewport().width(), self._card_cell_width())
        return max(1, available // self._card_cell_width())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._cards:
            return
        columns = max(1, self._compute_columns())
        if columns != self._columns:
            self._columns = columns
            self._reflow()

    def _reflow(self):
        """Re-lay-out existing cards into the current column count without
        recreating or re-fetching them."""
        widgets = []
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                widgets.append(item.widget())
        for index, widget in enumerate(widgets):
            row, col = divmod(index, self._columns)
            self._grid.addWidget(widget, row, col)


class GalleryPanel(QTabWidget):
    """Tabbed thumbnail gallery: Left / Center / Right camera folders."""

    image_clicked = pyqtSignal(str)  # image_path, re-emitted from whichever tab

    def __init__(self):
        super().__init__()
        self.setObjectName("galleryPanel")
        self.tabs = {}
        for prefix, label in (("left", "Left"), ("center", "Center"), ("right", "Right")):
            tab = CameraGalleryTab(prefix)
            tab.image_clicked.connect(self.image_clicked.emit)
            self.tabs[prefix] = tab
            self.addTab(tab, label)

    def set_directory(self, prefix, directory):
        self.tabs[prefix].populate(directory)

    def shutdown(self):
        for tab in self.tabs.values():
            tab.shutdown()
