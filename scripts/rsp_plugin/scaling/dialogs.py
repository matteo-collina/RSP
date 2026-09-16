"""Qt dialogs for the Scaling flow: the one-shot BaselineDialog prompt and
the persistent, non-modal StatsPanel.

This module only ever sees plain Python values and never imports Metashape
or touches a chunk/camera/scalebar object -- that plumbing lives in flow.py.
Must import cleanly even when no Qt binding is available; only instantiating
a class here requires PySide6/PySide2 to be present.
"""

from ..common import theme
from ..common.charts import CountTiles, LineChart
from ..common.qt import QtCore, QtWidgets

DEFAULT_BASELINE_M = 1.0
DEFAULT_THRESHOLD_M = 0.01


if QtWidgets is not None:

    class _StatTile(QtWidgets.QFrame):
        """Glass-card stat tile: a small-caps caption over a big number.
        value_scale/bold/color rank tiles against each other."""

        def __init__(self, caption, value_scale=1.0, bold=False, color=None, parent=None):
            super().__init__(parent)
            p = theme.Palette
            self.setObjectName("statTile")
            self.setStyleSheet(
                f"QFrame#statTile {{ background-color: {p.bg_elevated}; "
                f"border-radius: {p.radius_card}px; }}"
            )

            self.caption_label = QtWidgets.QLabel(caption.upper(), self)
            self.caption_label.setAlignment(QtCore.Qt.AlignCenter)
            self.caption_label.setStyleSheet(f"background: transparent; color: {p.text_secondary};")
            caption_font = self.caption_label.font()
            caption_font.setPointSizeF(max(caption_font.pointSizeF() * 0.75, 7))
            caption_font.setBold(True)
            self.caption_label.setFont(caption_font)

            self.value_label = QtWidgets.QLabel("N/A", self)
            self.value_label.setAlignment(QtCore.Qt.AlignCenter)
            self.value_label.setStyleSheet(f"background: transparent; color: {color or p.text_primary};")
            value_font = self.value_label.font()
            value_font.setPointSizeF(value_font.pointSizeF() * value_scale)
            value_font.setBold(bold)
            self.value_label.setFont(value_font)

            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(4)
            layout.addWidget(self.value_label)
            layout.addWidget(self.caption_label)

        def set_value(self, text):
            self.value_label.setText(text)

    class BaselineDialog(QtWidgets.QDialog):
        """Modal prompt: baseline distance (m) + "optimize cameras" checkbox."""

        def __init__(self, parent=None, default_distance=DEFAULT_BASELINE_M):
            super().__init__(parent)
            self.setWindowTitle("RSP Scaling - Baseline Distance")
            self.setModal(True)

            self.distance_spin = QtWidgets.QDoubleSpinBox(self)
            self.distance_spin.setDecimals(4)
            self.distance_spin.setRange(0.0001, 1_000_000.0)
            self.distance_spin.setSingleStep(0.1)
            self.distance_spin.setValue(default_distance)
            self.distance_spin.setSuffix(" m")

            self.optimize_checkbox = QtWidgets.QCheckBox("Optimize cameras after scaling", self)
            self.optimize_checkbox.setChecked(True)

            form = QtWidgets.QFormLayout()
            form.addRow("Baseline distance:", self.distance_spin)
            form.addRow(self.optimize_checkbox)

            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self
            )
            ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)
            if ok_button is not None:
                ok_button.setObjectName("processButton")
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addLayout(form)
            layout.addWidget(buttons)

            theme.apply_theme(self)

        @property
        def distance(self):
            return self.distance_spin.value()

        @property
        def optimize_cameras(self):
            return self.optimize_checkbox.isChecked()

        @classmethod
        def get_values(cls, parent=None, default_distance=DEFAULT_BASELINE_M):
            """Return (distance, optimize_cameras), or None if cancelled."""
            dialog = cls(parent=parent, default_distance=default_distance)
            exec_method = dialog.exec if hasattr(dialog, "exec") else dialog.exec_
            result = exec_method()
            if result != QtWidgets.QDialog.Accepted:
                return None
            return dialog.distance, dialog.optimize_cameras

    class StatsPanel(QtWidgets.QDialog):
        """Persistent, non-modal panel: live counts + error chart + a
        repeatable filter step. filter_requested(float) fires when the user
        clicks "Apply Filter"; flow.py filters the chunk and refreshes this
        same panel in place.

        RMS leads the four summary tiles, not the mean: a signed mean of
        per-scalebar errors tends toward zero even when individual errors
        are large, while RMS matches Metashape's own Reference-pane
        scalebar error. Std Dev gets similar weight to RMS since the two
        coincide whenever the mean is near zero. Mean and Max |error| are
        secondary.
        """

        filter_requested = QtCore.Signal(float)

        def __init__(self, parent=None):
            super().__init__(parent, QtCore.Qt.Window)
            self.setWindowTitle("RSP Scaling - Scalebar Stats")
            self.setModal(False)
            self.setWindowModality(QtCore.Qt.NonModal)

            self.count_tiles = CountTiles(self)
            self.chart = LineChart(self)

            p = theme.Palette
            self.rms_tile = _StatTile("RMS", value_scale=1.7, bold=True, color=p.accent)
            self.stdev_tile = _StatTile("Std Dev", value_scale=1.35, bold=True, color=p.accent)
            self.mean_tile = _StatTile("Mean (bias)", value_scale=1.0, bold=False, color=p.text_secondary)
            self.max_tile = _StatTile("Max |error|", value_scale=1.0, bold=False, color=p.text_secondary)
            summary_layout = QtWidgets.QHBoxLayout()
            summary_layout.addWidget(self.rms_tile)
            summary_layout.addWidget(self.stdev_tile)
            summary_layout.addWidget(self.mean_tile)
            summary_layout.addWidget(self.max_tile)

            self.threshold_spin = QtWidgets.QDoubleSpinBox(self)
            self.threshold_spin.setDecimals(4)
            self.threshold_spin.setRange(0.0, 1_000_000.0)
            self.threshold_spin.setSingleStep(0.001)
            self.threshold_spin.setValue(DEFAULT_THRESHOLD_M)
            self.threshold_spin.setSuffix(" m")
            self.threshold_spin.valueChanged.connect(self.chart.set_threshold)

            self.apply_button = QtWidgets.QPushButton("Apply Filter", self)
            self.apply_button.setObjectName("processButton")
            self.apply_button.clicked.connect(self._on_apply_clicked)

            filter_layout = QtWidgets.QHBoxLayout()
            filter_layout.addWidget(QtWidgets.QLabel("Error threshold:"))
            filter_layout.addWidget(self.threshold_spin)
            filter_layout.addWidget(self.apply_button)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addWidget(self.count_tiles)
            layout.addWidget(self.chart)
            layout.addLayout(summary_layout)
            layout.addLayout(filter_layout)

            theme.apply_theme(self)

            self.chart.threshold_dragged.connect(self._on_chart_threshold_dragged)

        @property
        def current_threshold(self):
            return self.threshold_spin.value()

        def _on_chart_threshold_dragged(self, value):
            self.threshold_spin.blockSignals(True)
            try:
                self.threshold_spin.setValue(value)
            finally:
                self.threshold_spin.blockSignals(False)

        def _on_apply_clicked(self):
            self.filter_requested.emit(self.threshold_spin.value())

        def update_counts(self, should_exist, created, remaining):
            self.count_tiles.set_counts(should_exist, created, remaining)

        def update_chart(self, points, threshold=None):
            self.chart.set_data(points, threshold=threshold)

        def update_summary(self, rms_text, mean_text, stdev_text, max_text):
            self.rms_tile.set_value(rms_text)
            self.mean_tile.set_value(mean_text)
            self.stdev_tile.set_value(stdev_text)
            self.max_tile.set_value(max_text)

else:

    class _NoQtDialog:
        """Raises clearly when no Qt binding is available, instead of a
        confusing "NoneType is not callable"."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "No Qt binding (PySide6/PySide2) is available; cannot create "
                "the Scaling dialogs."
            )

    BaselineDialog = _NoQtDialog
    StatsPanel = _NoQtDialog
