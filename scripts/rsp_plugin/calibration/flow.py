"""Calibration Wizard flow: import photos, set the camera/lens model, detect
markers, scale from either RSP's provided calibration target or custom
marker distances, align, then compute a survey stereo-pair baseline directly
from the live chunk.

Like scaling/flow.py, this is the only module in rsp_plugin.calibration that
imports Metashape directly; dialogs.py stays pure Qt over plain Python
values.
"""

import os
from datetime import datetime

import Metashape

from ..common import csv_io, pairs, stats
from ..common.metashape_helpers import estimated_distance
from ..common.qt import QtWidgets
from . import dialogs

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def _collect_image_files(folder):
    try:
        entries = sorted(os.listdir(folder))
    except OSError:
        return []

    files = []
    for name in entries:
        if os.path.splitext(name)[1].lower() in IMAGE_EXTENSIONS:
            files.append(os.path.join(folder, name))
    return files


def _apply_sensor_type(chunk, sensor_type_name):
    # Must run before detectMarkers()/matchPhotos()/alignCameras(): Frame vs.
    # Fisheye are different distortion models, and Metashape groups cameras
    # into shared Sensor objects, so this is set per sensor, not per camera.
    sensor_type = getattr(Metashape.Sensor.Type, sensor_type_name)
    for sensor in chunk.sensors:
        sensor.type = sensor_type


def _normalize_marker_label(label):
    return label.strip().casefold()


def _add_scalebars_from_entries(chunk, entries):
    """entries: (marker1_label, marker2_label, distance, accuracy) tuples.
    Returns (created_scalebars, skipped_entries); an entry is skipped if
    either marker label isn't in chunk.markers."""
    markers_by_label = {}
    for marker in chunk.markers:
        markers_by_label.setdefault(_normalize_marker_label(marker.label), marker)

    created = []
    skipped = []
    for entry in entries:
        marker1_label, marker2_label, distance, accuracy = entry
        marker1 = markers_by_label.get(_normalize_marker_label(marker1_label))
        marker2 = markers_by_label.get(_normalize_marker_label(marker2_label))
        if marker1 is None or marker2 is None:
            skipped.append(entry)
            continue

        scalebar = chunk.addScalebar(marker1, marker2)
        scalebar.reference.distance = distance
        scalebar.reference.accuracy = accuracy
        created.append(scalebar)

    return created, skipped


def _create_rsp_scalebars(chunk):
    specs = csv_io.load_rsp_scalebars()
    entries = [(spec.marker1, spec.marker2, spec.distance, spec.accuracy) for spec in specs]

    _created, skipped_entries = _add_scalebars_from_entries(chunk, entries)
    skipped_pairs = {(marker1, marker2) for marker1, marker2, _, _ in skipped_entries}
    skipped = [spec for spec in specs if (spec.marker1, spec.marker2) in skipped_pairs]

    return _created, skipped


def _create_custom_scalebars(chunk, entries):
    created, _skipped = _add_scalebars_from_entries(chunk, entries)
    return created


def _create_scalebars_for_pairs(chunk, stereo_pairs):
    created = []
    for left, right in stereo_pairs:
        try:
            created.append(chunk.addScalebar(left, right))
        except Exception:
            continue
    return created


def _build_report_text(distances, computed_stats):
    seen = set()
    unique_distances = []
    for d in distances:
        if d not in seen:
            unique_distances.append(d)
            seen.add(d)

    quality = stats.quality_label(computed_stats.cv)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "STEREO BASELINE CALIBRATION RESULTS",
        f"Generated: {timestamp}",
        "Source: RSP Calibration Wizard (computed directly from the live chunk)",
        "",
        "MEASUREMENTS:",
        f"Total measurements: {len(distances)}",
        f"Unique measurements: {len(unique_distances)}",
        "",
        "BASELINE DISTANCE:",
        f"Median: {computed_stats.median:.6f} m  <- RECOMMENDED",
        f"Mean: {computed_stats.mean:.6f} m",
        f"Standard deviation: {computed_stats.stdev:.6f} m",
        f"Range: {computed_stats.min:.6f} m to {computed_stats.max:.6f} m",
        "",
        "QUALITY ASSESSMENT:",
        f"Coefficient of variation: {computed_stats.cv:.2f}%",
        f"Status: {quality}",
        "",
        "ALL UNIQUE MEASUREMENTS:",
    ]
    for i, d in enumerate(sorted(unique_distances), 1):
        lines.append(f"  {i:2d}. {d:.6f} m")

    return "\n".join(lines) + "\n"


def run():
    if QtWidgets is None:
        Metashape.app.messageBox(
            "No Qt binding (PySide6/PySide2) is available in this Metashape "
            "Python environment, so the Calibration Wizard cannot be shown."
        )
        return

    document = Metashape.app.document
    if document is None:
        Metashape.app.messageBox("No active Metashape document. Please open or create a project first.")
        return

    setup = dialogs.CalibrationSetupDialog.get_setup()
    if setup is None:
        return

    image_files = []
    for folder in (setup.left_folder, setup.right_folder, setup.center_folder):
        if folder:
            image_files.extend(_collect_image_files(folder))

    if not image_files:
        Metashape.app.messageBox(
            "No supported image files (.jpg/.jpeg/.png/.tif/.tiff) were found "
            "in the selected folder(s). Calibration Wizard cancelled."
        )
        return

    chunk = document.addChunk()
    chunk.addPhotos(image_files)
    _apply_sensor_type(chunk, setup.sensor_type_name)

    used_rsp_target = setup.used_rsp_target
    chunk.detectMarkers(target_type=getattr(Metashape.TargetType, setup.target_type_name))

    if not chunk.markers:
        Metashape.app.messageBox(
            "No calibration markers were detected in the imported photos. "
            "Check target visibility/lighting and try again. The imported "
            "photos remain in the new chunk."
        )
        return

    if used_rsp_target:
        matched, skipped = _create_rsp_scalebars(chunk)
        if skipped:
            skipped_labels = ", ".join(f"{spec.marker1}/{spec.marker2}" for spec in skipped)
            Metashape.app.messageBox(
                "Some of RSP's calibration scalebars were skipped because "
                f"their markers were not detected: {skipped_labels}"
            )
    else:
        entries = dialogs.MarkerTableDialog.get_entries([marker.label for marker in chunk.markers])
        if entries is None:
            return
        matched = _create_custom_scalebars(chunk, entries)

    if not matched:
        Metashape.app.messageBox(
            "No calibration scalebars could be created, so the chunk can't "
            "be scaled. Calibration Wizard stopped."
        )
        return

    chunk.matchPhotos()
    chunk.alignCameras()
    chunk.updateTransform()

    found_pairs = pairs.find_stereo_pairs(chunk.cameras)
    if not found_pairs:
        Metashape.app.messageBox(
            "No survey stereo camera pairs were found after alignment "
            "(expected camera labels like <prefix>_left_<n> / "
            "<prefix>_right_<n>). Calibration Wizard finished without a "
            "computed baseline."
        )
        return

    survey_scalebars = _create_scalebars_for_pairs(chunk, found_pairs)
    if not survey_scalebars:
        Metashape.app.messageBox(
            "No survey scalebars could be created from the detected stereo "
            "pairs. Calibration Wizard finished without a computed baseline."
        )
        return

    chunk.updateTransform()

    # None = unmeasurable (an endpoint camera isn't aligned); left out of the stats.
    estimated_distances = [
        d for d in (estimated_distance(scalebar, chunk) for scalebar in survey_scalebars) if d is not None
    ]
    if not estimated_distances:
        Metashape.app.messageBox(
            "None of the survey scalebars could be measured (their cameras "
            "aren't aligned). Calibration Wizard finished without a computed "
            "baseline."
        )
        return
    computed_stats = stats.compute_stats(estimated_distances)
    quality_text = stats.quality_label(computed_stats.cv)
    points = list(enumerate(estimated_distances))

    dialog = dialogs.ResultDialog(computed_stats, quality_text, points)

    def _on_save_requested():
        path = Metashape.app.getSaveFileName(
            "Save Calibration Results", filter="Text files (*.txt);;All files (*.*)"
        )
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"

        report_text = _build_report_text(estimated_distances, computed_stats)
        try:
            with open(path, "w") as f:
                f.write(report_text)
        except OSError as exc:
            dialog.set_save_status(f"Save failed: {exc}")
            return
        dialog.set_save_status(f"Saved to {path}")

    dialog.save_requested.connect(_on_save_requested)
    exec_method = dialog.exec if hasattr(dialog, "exec") else dialog.exec_
    exec_method()
