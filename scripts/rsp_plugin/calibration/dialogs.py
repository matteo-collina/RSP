"""Qt dialogs for the Calibration Wizard: the combined setup dialog, the
custom-marker table builder, and the final results dialog.

This module only ever sees plain Python values and never imports Metashape
or touches a chunk/camera/marker/scalebar object -- that plumbing lives in
flow.py. Must import cleanly even when no Qt binding is available.
"""

from dataclasses import dataclass
from typing import Optional

from ..common import theme
from ..common.charts import LineChart
from ..common.qt import QtCore, QtWidgets

DEFAULT_ACCURACY_M = 0.01

TARGET_TYPE_NAMES = [
    "CircularTarget12bit",
    "CircularTarget14bit",
    "CircularTarget16bit",
    "CircularTarget20bit",
    "CircularTarget",
    "CrossTarget",
    "AprilTag16h5",
    "AprilTag25h9",
    "AprilTag36h10",
    "AprilTag36h11",
    "AprilTagCircle21h7",
    "AprilTagStandard41h12",
    "AprilTagStandard52h13",
]

DEFAULT_TARGET_TYPE_NAME = "CircularTarget12bit"

# RPC (satellite/pushbroom) is excluded -- never applicable to an RSP rig.
SENSOR_TYPE_NAMES = [
    "Frame",
    "Fisheye",
    "EquidistantFisheye",
    "EquisolidFisheye",
    "Spherical",
    "Cylindrical",
]

DEFAULT_SENSOR_TYPE_NAME = "Frame"


@dataclass
class CalibrationSetupResult:
    left_folder: str
    right_folder: str
    center_folder: Optional[str]
    used_rsp_target: bool
    target_type_name: str
    sensor_type_name: str


if QtWidgets is not None:

    class CalibrationSetupDialog(QtWidgets.QDialog):
        """First step of the Calibration Wizard: Left/Right/Center folder
        pickers, the RSP-target-vs-custom-markers choice, the marker
        target-type dropdown (custom markers only), and the camera/lens
        model dropdown (always shown)."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("RSP Calibration Wizard - Setup")
            self.setModal(True)

            self.left_edit = QtWidgets.QLineEdit(self)
            self.left_edit.setReadOnly(True)
            self.right_edit = QtWidgets.QLineEdit(self)
            self.right_edit.setReadOnly(True)
            self.center_edit = QtWidgets.QLineEdit(self)
            self.center_edit.setReadOnly(True)

            left_browse = QtWidgets.QPushButton("Browse...", self)
            left_browse.clicked.connect(lambda: self._browse(self.left_edit, "Select left camera folder"))
            right_browse = QtWidgets.QPushButton("Browse...", self)
            right_browse.clicked.connect(lambda: self._browse(self.right_edit, "Select right camera folder"))
            center_browse = QtWidgets.QPushButton("Browse...", self)
            center_browse.clicked.connect(
                lambda: self._browse(self.center_edit, "Select center camera folder (optional)")
            )

            folder_form = QtWidgets.QFormLayout()
            folder_form.addRow("Left (required):", self._folder_row(self.left_edit, left_browse))
            folder_form.addRow("Right (required):", self._folder_row(self.right_edit, right_browse))
            folder_form.addRow("Center (optional):", self._folder_row(self.center_edit, center_browse))

            self.rsp_radio = QtWidgets.QRadioButton("I used RSP's printed calibration target", self)
            self.rsp_radio.setChecked(True)
            self.custom_radio = QtWidgets.QRadioButton("I used custom markers", self)
            self.target_choice_group = QtWidgets.QButtonGroup(self)
            self.target_choice_group.addButton(self.rsp_radio)
            self.target_choice_group.addButton(self.custom_radio)

            self.target_type_label = QtWidgets.QLabel("Marker target type:", self)
            self.target_type_combo = QtWidgets.QComboBox(self)
            self.target_type_combo.addItems(TARGET_TYPE_NAMES)
            index = self.target_type_combo.findText(DEFAULT_TARGET_TYPE_NAME)
            self.target_type_combo.setCurrentIndex(index if index >= 0 else 0)
            self.target_type_label.setVisible(False)
            self.target_type_combo.setVisible(False)
            self.custom_radio.toggled.connect(self._update_target_type_visibility)

            target_form = QtWidgets.QFormLayout()
            target_form.addRow(self.rsp_radio)
            target_form.addRow(self.custom_radio)
            target_form.addRow(self.target_type_label, self.target_type_combo)

            self.sensor_type_combo = QtWidgets.QComboBox(self)
            self.sensor_type_combo.addItems(SENSOR_TYPE_NAMES)
            sensor_index = self.sensor_type_combo.findText(DEFAULT_SENSOR_TYPE_NAME)
            self.sensor_type_combo.setCurrentIndex(sensor_index if sensor_index >= 0 else 0)

            sensor_form = QtWidgets.QFormLayout()
            sensor_form.addRow("Camera / lens model:", self.sensor_type_combo)

            self.buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self
            )
            ok_button = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
            if ok_button is not None:
                ok_button.setObjectName("processButton")
            self.buttons.accepted.connect(self.accept)
            self.buttons.rejected.connect(self.reject)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addLayout(folder_form)
            layout.addLayout(target_form)
            layout.addLayout(sensor_form)
            layout.addWidget(self.buttons)
            self.resize(480, 400)

            self.left_edit.textChanged.connect(self._update_ok_enabled)
            self.right_edit.textChanged.connect(self._update_ok_enabled)
            self._update_ok_enabled()

            theme.apply_theme(self)

        def _folder_row(self, line_edit, browse_button):
            row = QtWidgets.QHBoxLayout()
            row.addWidget(line_edit)
            row.addWidget(browse_button)
            return row

        def _browse(self, line_edit, caption):
            path = QtWidgets.QFileDialog.getExistingDirectory(self, caption)
            if path:
                line_edit.setText(path)

        def _update_target_type_visibility(self):
            visible = self.custom_radio.isChecked()
            self.target_type_label.setVisible(visible)
            self.target_type_combo.setVisible(visible)

        def _update_ok_enabled(self):
            ok_button = self.buttons.button(QtWidgets.QDialogButtonBox.Ok)
            if ok_button is not None:
                ok_button.setEnabled(bool(self.left_edit.text()) and bool(self.right_edit.text()))

        @property
        def setup_result(self):
            center = self.center_edit.text().strip()
            used_rsp_target = self.rsp_radio.isChecked()
            return CalibrationSetupResult(
                left_folder=self.left_edit.text().strip(),
                right_folder=self.right_edit.text().strip(),
                center_folder=center or None,
                used_rsp_target=used_rsp_target,
                target_type_name=(
                    DEFAULT_TARGET_TYPE_NAME if used_rsp_target else self.target_type_combo.currentText()
                ),
                sensor_type_name=self.sensor_type_combo.currentText(),
            )

        @classmethod
        def get_setup(cls, parent=None):
            """Return a CalibrationSetupResult, or None if cancelled."""
            dialog = cls(parent=parent)
            exec_method = dialog.exec if hasattr(dialog, "exec") else dialog.exec_
            result = exec_method()
            if result != QtWidgets.QDialog.Accepted:
                return None
            return dialog.setup_result

    class MarkerTableDialog(QtWidgets.QDialog):
        """Custom-markers branch: builds a list of (marker1, marker2,
        distance, accuracy) scalebar specs from detected marker labels."""

        def __init__(self, marker_labels, parent=None):
            super().__init__(parent)
            self.setWindowTitle("RSP Calibration Wizard - Custom Marker Distances")
            self.setModal(True)
            self._rows = []

            self.marker1_combo = QtWidgets.QComboBox(self)
            self.marker1_combo.addItems(list(marker_labels))
            self.marker2_combo = QtWidgets.QComboBox(self)
            self.marker2_combo.addItems(list(marker_labels))

            self.distance_spin = QtWidgets.QDoubleSpinBox(self)
            self.distance_spin.setDecimals(4)
            self.distance_spin.setRange(0.0001, 1_000_000.0)
            self.distance_spin.setSingleStep(0.01)
            self.distance_spin.setValue(0.197)
            self.distance_spin.setSuffix(" m")

            self.accuracy_spin = QtWidgets.QDoubleSpinBox(self)
            self.accuracy_spin.setDecimals(4)
            self.accuracy_spin.setRange(0.0001, 1_000_000.0)
            self.accuracy_spin.setSingleStep(0.001)
            self.accuracy_spin.setValue(DEFAULT_ACCURACY_M)
            self.accuracy_spin.setSuffix(" m")

            self.add_button = QtWidgets.QPushButton("Add Row", self)
            self.add_button.clicked.connect(self._on_add_clicked)
            self.remove_button = QtWidgets.QPushButton("Remove Selected", self)
            self.remove_button.clicked.connect(self._on_remove_clicked)

            self.status_label = QtWidgets.QLabel("", self)

            picker_form = QtWidgets.QFormLayout()
            picker_form.addRow("Marker 1:", self.marker1_combo)
            picker_form.addRow("Marker 2:", self.marker2_combo)
            picker_form.addRow("Distance:", self.distance_spin)
            picker_form.addRow("Accuracy:", self.accuracy_spin)

            row_buttons = QtWidgets.QHBoxLayout()
            row_buttons.addWidget(self.add_button)
            row_buttons.addWidget(self.remove_button)

            self.table = QtWidgets.QTableWidget(0, 4, self)
            self.table.setHorizontalHeaderLabels(["Marker 1", "Marker 2", "Distance (m)", "Accuracy (m)"])
            self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.table.setAlternatingRowColors(True)
            self.table.horizontalHeader().setStretchLastSection(True)

            buttons = QtWidgets.QDialogButtonBox(
                QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self
            )
            ok_button = buttons.button(QtWidgets.QDialogButtonBox.Ok)
            if ok_button is not None:
                ok_button.setObjectName("processButton")
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addLayout(picker_form)
            layout.addLayout(row_buttons)
            layout.addWidget(self.status_label)
            layout.addWidget(self.table)
            layout.addWidget(buttons)
            self.resize(480, 420)

            theme.apply_theme(self)

        def _on_add_clicked(self):
            marker1 = self.marker1_combo.currentText()
            marker2 = self.marker2_combo.currentText()
            if not marker1 or not marker2:
                self.status_label.setText("No detected markers available to pick.")
                return
            if marker1 == marker2:
                self.status_label.setText("Marker 1 and Marker 2 must be different markers.")
                return

            self._rows.append((marker1, marker2, self.distance_spin.value(), self.accuracy_spin.value()))
            self.status_label.setText("")
            self._refresh_table()

        def _on_remove_clicked(self):
            row = self.table.currentRow()
            if row < 0 or row >= len(self._rows):
                return
            del self._rows[row]
            self._refresh_table()

        def _refresh_table(self):
            self.table.setRowCount(len(self._rows))
            for i, (marker1, marker2, distance, accuracy) in enumerate(self._rows):
                self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(marker1))
                self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(marker2))
                self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(f"{distance:.4f}"))
                self.table.setItem(i, 3, QtWidgets.QTableWidgetItem(f"{accuracy:.4f}"))

        @property
        def entries(self):
            return list(self._rows)

        @classmethod
        def get_entries(cls, marker_labels, parent=None):
            """Return the built entries list, or None if cancelled."""
            dialog = cls(marker_labels, parent=parent)
            exec_method = dialog.exec if hasattr(dialog, "exec") else dialog.exec_
            result = exec_method()
            if result != QtWidgets.QDialog.Accepted:
                return None
            return dialog.entries

    class ResultDialog(QtWidgets.QDialog):
        """One-shot modal results dialog: baseline stats + a per-pair
        estimated-distance chart. "Save calibration file" emits
        save_requested rather than doing file I/O itself; flow.py writes
        the file and reports back via set_save_status()."""

        save_requested = QtCore.Signal()

        def __init__(self, computed_stats, quality_text, points, parent=None):
            super().__init__(parent)
            self.setWindowTitle("RSP Calibration Wizard - Results")
            self.setModal(True)

            self.chart = LineChart(self)
            self.chart.set_data(points)

            p = theme.Palette
            stats_html = (
                f"<div style='font-size:15pt; font-weight:700; color:{p.accent};'>"
                f"{computed_stats.median:.6f} m</div>"
                f"<div style='color:{p.text_secondary}; font-size:8pt; font-weight:700;'>"
                f"RECOMMENDED BASELINE (MEDIAN)</div>"
                f"<div style='margin-top:10px; color:{p.text_secondary};'>"
                f"Mean: {computed_stats.mean:.6f} m &nbsp;&middot;&nbsp; "
                f"Std dev: {computed_stats.stdev:.6f} m &nbsp;&middot;&nbsp; "
                f"Range: {computed_stats.min:.6f}-{computed_stats.max:.6f} m &nbsp;&middot;&nbsp; "
                f"CV: {computed_stats.cv:.2f}%</div>"
                f"<div style='margin-top:8px; font-weight:600;'>{quality_text}</div>"
            )
            self.stats_label = QtWidgets.QLabel(stats_html, self)
            self.stats_label.setTextFormat(QtCore.Qt.RichText)
            self.stats_label.setWordWrap(True)

            self.save_button = QtWidgets.QPushButton("Save calibration file...", self)
            self.save_button.setObjectName("processButton")
            self.save_button.clicked.connect(self.save_requested.emit)

            self.save_status_label = QtWidgets.QLabel("", self)
            self.save_status_label.setWordWrap(True)

            close_buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close, self)
            close_buttons.rejected.connect(self.accept)

            layout = QtWidgets.QVBoxLayout(self)
            layout.addWidget(self.chart)
            layout.addWidget(self.stats_label)
            layout.addWidget(self.save_button)
            layout.addWidget(self.save_status_label)
            layout.addWidget(close_buttons)
            self.resize(520, 420)

            theme.apply_theme(self)

        def set_save_status(self, text):
            self.save_status_label.setText(text)

else:

    class _NoQtDialog:
        """Raises clearly when no Qt binding is available."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "No Qt binding (PySide6/PySide2) is available; cannot create the Calibration Wizard dialogs."
            )

    CalibrationSetupDialog = _NoQtDialog
    MarkerTableDialog = _NoQtDialog
    ResultDialog = _NoQtDialog
