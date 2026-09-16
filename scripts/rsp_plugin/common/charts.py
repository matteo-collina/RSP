"""Hand-painted chart widgets for the RSP Metashape plugin.

No matplotlib: both widgets draw themselves with QPainter, so the plugin
adds no plotting dependency beyond whatever Qt binding Metashape bundles.
Must import cleanly with no Qt binding available; only instantiating the
widgets requires one. Neither widget creates a QApplication.
"""

from .qt import QtWidgets, QtGui, QtCore
from .theme import Palette


def _parse_color(value):
    """QColor from a Palette value -- either "#RRGGBB" or QSS "rgba(...)",
    which Qt's own QColor constructor can't parse directly."""
    value = value.strip()
    if value.startswith("rgba"):
        r, g, b, a = (part.strip() for part in value[value.index("(") + 1 : value.rindex(")")].split(","))
        color = QtGui.QColor(int(float(r)), int(float(g)), int(float(b)))
        color.setAlphaF(float(a))
        return color
    return QtGui.QColor(value)


class _PlotGeometry:
    """Pixel<->data-space mapping for LineChart's plot area. Kept Qt-free
    and defined unconditionally so the math can be unit-tested without a
    Qt binding (see tests/test_chart_geometry.py). Shared by paint and
    hit-testing/dragging so the two can't drift apart."""

    __slots__ = ("plot_x0", "plot_y0", "plot_w", "plot_h", "x_min", "x_span", "y_extent")

    def __init__(self, plot_x0, plot_y0, plot_w, plot_h, x_min, x_span, y_extent):
        self.plot_x0 = plot_x0
        self.plot_y0 = plot_y0
        self.plot_w = plot_w
        self.plot_h = plot_h
        self.x_min = x_min
        self.x_span = x_span
        self.y_extent = y_extent

    def to_px(self, x, y):
        px = self.plot_x0 + (x - self.x_min) / self.x_span * self.plot_w
        py = self.plot_y0 + self.plot_h / 2 - (y / self.y_extent) * (self.plot_h / 2)
        return px, py

    def y_from_px(self, py):
        return (self.plot_h / 2 - (py - self.plot_y0)) / (self.plot_h / 2) * self.y_extent


def _compute_plot_geometry(
    points,
    threshold,
    width,
    height,
    margin_left=40,
    margin_right=12,
    margin_top=12,
    margin_bottom=10,
):
    """_PlotGeometry for a point list/threshold/widget size, or None if
    there's nothing to plot."""
    if not points:
        return None

    plot_w = max(width - margin_left - margin_right, 1)
    plot_h = max(height - margin_top - margin_bottom, 1)

    xs = [pt[0] for pt in points]
    ys = [pt[1] for pt in points]
    y_extent = max(abs(min(ys)), abs(max(ys)), threshold or 0.0, 1e-9) * 1.15
    x_min, x_max = min(xs), max(xs)
    x_span = (x_max - x_min) or 1.0

    return _PlotGeometry(margin_left, margin_top, plot_w, plot_h, x_min, x_span, y_extent)


def _event_pos(event):
    """(x, y) from a QMouseEvent -- .position() on PySide6, .pos() on PySide2."""
    if hasattr(event, "position"):
        point = event.position()
    else:
        point = event.pos()
    return point.x(), point.y()


if QtWidgets is not None:

    class LineChart(QtWidgets.QWidget):
        """Per-index line/scatter plot for scalebar error by camera sequence
        index. If a threshold is set, dashed +/-threshold lines are drawn
        and are draggable (within _DRAG_TOLERANCE_PX) to adjust it live,
        emitting threshold_dragged. Points beyond the threshold render in
        Palette.error as a preview of what "Apply Filter" would remove;
        the connecting line itself stays a neutral color.
        """

        threshold_dragged = QtCore.Signal(float)

        _DRAG_TOLERANCE_PX = 7

        def __init__(self, parent=None):
            super().__init__(parent)
            self._points = []
            self._threshold = None
            self._dragging = False
            self.setMinimumSize(280, 150)
            self.setMouseTracking(True)

        def sizeHint(self):
            return QtCore.QSize(460, 220)

        def set_data(self, points, threshold=None):
            """points: floats (plotted against index) or (index, value) pairs."""
            normalized = []
            for i, item in enumerate(points):
                if isinstance(item, (tuple, list)):
                    x, y = item
                else:
                    x, y = i, item
                normalized.append((float(x), float(y)))
            self._points = normalized
            self.set_threshold(threshold)

        def set_threshold(self, threshold):
            self._threshold = threshold
            self.update()

        def _plot_geometry(self):
            rect = self.rect()
            return _compute_plot_geometry(self._points, self._threshold, rect.width(), rect.height())

        def _threshold_line_pixel_ys(self, geom):
            if self._threshold is None:
                return []
            return [geom.to_px(geom.x_min, sign * self._threshold)[1] for sign in (1, -1)]

        def _line_hit_test(self, pixel_y):
            geom = self._plot_geometry()
            if geom is None:
                return False
            return any(abs(pixel_y - line_py) <= self._DRAG_TOLERANCE_PX for line_py in self._threshold_line_pixel_ys(geom))

        def _drag_to(self, pixel_y):
            geom = self._plot_geometry()
            if geom is None:
                return
            value = max(abs(geom.y_from_px(pixel_y)), 0.0)
            self.set_threshold(value)
            self.threshold_dragged.emit(value)

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                _, y = _event_pos(event)
                if self._line_hit_test(y):
                    self._dragging = True
                    self._drag_to(y)
                    event.accept()
                    return
            super().mousePressEvent(event)

        def mouseMoveEvent(self, event):
            _, y = _event_pos(event)
            if self._dragging:
                self._drag_to(y)
                event.accept()
                return
            if self._line_hit_test(y):
                self.setCursor(QtCore.Qt.SizeVerCursor)
            else:
                self.unsetCursor()
            super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event):
            if self._dragging and event.button() == QtCore.Qt.LeftButton:
                _, y = _event_pos(event)
                self._drag_to(y)
                self._dragging = False
                event.accept()
                return
            super().mouseReleaseEvent(event)

        def leaveEvent(self, event):
            if not self._dragging:
                self.unsetCursor()
            super().leaveEvent(event)

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                self._paint(painter)
            finally:
                painter.end()

        def _paint(self, painter):
            p = Palette
            rect = self.rect()
            painter.fillRect(rect, _parse_color(p.bg_panel))

            geom = self._plot_geometry()
            if geom is None:
                painter.setPen(_parse_color(p.text_secondary))
                painter.drawText(rect, QtCore.Qt.AlignCenter, "No data")
                return

            plot_x0, plot_y0, plot_w, plot_h = geom.plot_x0, geom.plot_y0, geom.plot_w, geom.plot_h
            x_min, y_extent = geom.x_min, geom.y_extent
            to_px = geom.to_px

            grid_pen = QtGui.QPen(_parse_color(p.border_subtle))
            grid_pen.setWidth(1)
            painter.setPen(grid_pen)
            for frac in (-1.0, -0.5, 0.5, 1.0):
                _, py = to_px(x_min, frac * y_extent)
                painter.drawLine(QtCore.QPointF(plot_x0, py), QtCore.QPointF(plot_x0 + plot_w, py))

            zero_pen = QtGui.QPen(_parse_color(p.border_strong))
            zero_pen.setWidth(2)
            painter.setPen(zero_pen)
            _, zero_py = to_px(x_min, 0.0)
            painter.drawLine(QtCore.QPointF(plot_x0, zero_py), QtCore.QPointF(plot_x0 + plot_w, zero_py))

            if self._threshold is not None:
                dash_pen = QtGui.QPen(_parse_color(p.error))
                dash_pen.setStyle(QtCore.Qt.DashLine)
                dash_pen.setWidth(1)
                painter.setPen(dash_pen)
                for line_py in self._threshold_line_pixel_ys(geom):
                    painter.drawLine(QtCore.QPointF(plot_x0, line_py), QtCore.QPointF(plot_x0 + plot_w, line_py))

            line_pen = QtGui.QPen(_parse_color(p.border_strong))
            line_pen.setWidth(2)
            painter.setPen(line_pen)
            prev_px = None
            for x, y in self._points:
                cx, cy = to_px(x, y)
                if prev_px is not None:
                    painter.drawLine(QtCore.QPointF(*prev_px), QtCore.QPointF(cx, cy))
                prev_px = (cx, cy)

            painter.setPen(QtCore.Qt.NoPen)
            for x, y in self._points:
                cx, cy = to_px(x, y)
                would_be_cut = self._threshold is not None and abs(y) > self._threshold
                painter.setBrush(_parse_color(p.error if would_be_cut else p.accent))
                painter.drawEllipse(QtCore.QPointF(cx, cy), 3, 3)

            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(_parse_color(p.text_secondary))
            font = painter.font()
            font.setPointSizeF(max(font.pointSizeF() * 0.8, 7))
            painter.setFont(font)
            painter.drawText(
                QtCore.QRectF(0, plot_y0 - 8, plot_x0 - 6, 16),
                QtCore.Qt.AlignRight,
                f"+{y_extent:.3g}",
            )
            painter.drawText(
                QtCore.QRectF(0, plot_y0 + plot_h - 8, plot_x0 - 6, 16),
                QtCore.Qt.AlignRight,
                f"-{y_extent:.3g}",
            )

    class CountTiles(QtWidgets.QWidget):
        """Three-tile horizontal readout: "Should exist" / "Created" / "Remaining"."""

        _LABELS = ("Should exist", "Created", "Remaining")

        def __init__(self, parent=None):
            super().__init__(parent)
            self._counts = (0, 0, 0)
            self.setMinimumSize(300, 74)

        def sizeHint(self):
            return QtCore.QSize(420, 90)

        def set_counts(self, should_exist: int, created: int, remaining: int) -> None:
            self._counts = (int(should_exist), int(created), int(remaining))
            self.update()

        def paintEvent(self, event):
            painter = QtGui.QPainter(self)
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                self._paint(painter)
            finally:
                painter.end()

        def _paint(self, painter):
            p = Palette
            rect = self.rect()
            gap = 10.0
            tile_w = (rect.width() - gap * 2) / 3.0

            for i in range(3):
                tx = i * (tile_w + gap)
                tile_rect = QtCore.QRectF(tx, 0, tile_w, rect.height())

                painter.setPen(QtCore.Qt.NoPen)
                painter.setBrush(_parse_color(p.bg_elevated))
                painter.drawRoundedRect(tile_rect, p.radius_card, p.radius_card)

                number_font = QtGui.QFont(painter.font())
                number_font.setPointSizeF(number_font.pointSizeF() * 2.1)
                number_font.setBold(True)
                painter.setFont(number_font)
                painter.setPen(_parse_color(p.text_primary))
                number_rect = QtCore.QRectF(
                    tile_rect.x(), tile_rect.y() + 6, tile_rect.width(), tile_rect.height() * 0.62
                )
                painter.drawText(number_rect, QtCore.Qt.AlignCenter, str(self._counts[i]))

                label_font = QtGui.QFont(painter.font())
                label_font.setPointSizeF(max(label_font.pointSizeF() * 0.5, 7))
                label_font.setBold(False)
                painter.setFont(label_font)
                painter.setPen(_parse_color(p.text_secondary))
                label_rect = QtCore.QRectF(tile_rect.x(), tile_rect.bottom() - 24, tile_rect.width(), 20)
                painter.drawText(label_rect, QtCore.Qt.AlignCenter, self._LABELS[i])

else:

    class _NoQtWidget:
        """Raises clearly when no Qt binding is available."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("No Qt binding (PySide6/PySide2) is available; cannot create chart widgets.")

    LineChart = _NoQtWidget
    CountTiles = _NoQtWidget
