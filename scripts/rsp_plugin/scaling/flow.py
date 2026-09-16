"""Scaling flow: baseline distance -> scalebar creation -> live stats/filter panel.

run() creates scalebars for stereo pairs at a given baseline and opens the
stats/filter panel. run_filter_only() opens the same panel against scalebars
that already exist in the chunk, skipping baseline entry and creation. Both
share _open_stats_panel().

This is the only module in rsp_plugin.scaling that imports Metashape
directly; dialogs.py stays pure Qt over plain Python values.

"Our" scalebars are identified by the label pair of their two endpoint
cameras, not by Python object identity, since chunk.scalebars isn't
guaranteed to hand back the same wrapper object on repeated reads.
"""

import Metashape

from ..common import pairs, stats
from ..common.metashape_helpers import estimated_distance, get_active_chunk
from ..common.qt import QtWidgets
from . import dialogs

_active_panel = None

_NO_STEREO_PAIRS_MESSAGE = (
    "No stereo camera pairs were found in the active chunk "
    "(expected camera labels like <prefix>_left_<n> / <prefix>_right_<n>)."
)


def _parse_sequence_number(label):
    parts = label.split("_")
    if len(parts) < 3:
        return None
    try:
        return int(parts[-1])
    except ValueError:
        return None


def _pair_key(camera_a, camera_b):
    return frozenset({camera_a.label, camera_b.label})


def _scalebar_pair_key(scalebar):
    # None for a non-camera scalebar (e.g. marker-to-marker) rather than
    # matching it by accident.
    try:
        return frozenset({scalebar.point0.label, scalebar.point1.label})
    except AttributeError:
        return None


def _find_existing_scalebar(chunk, camera_a, camera_b):
    key = _pair_key(camera_a, camera_b)
    for scalebar in chunk.scalebars:
        if _scalebar_pair_key(scalebar) == key:
            return scalebar
    return None


def _our_scalebars(chunk, pair_keys):
    return [sb for sb in chunk.scalebars if _scalebar_pair_key(sb) in pair_keys]


def _scalebar_error(scalebar, chunk):
    return stats.scalebar_error(estimated_distance(scalebar, chunk), scalebar.reference.distance)


def _sequence_index(scalebar, fallback):
    seq = _parse_sequence_number(scalebar.point0.label)
    if seq is None:
        seq = _parse_sequence_number(scalebar.point1.label)
    return fallback if seq is None else seq


def _collect(chunk, pair_keys):
    live = _our_scalebars(chunk, pair_keys)
    points = [(_sequence_index(sb, i), _scalebar_error(sb, chunk)) for i, sb in enumerate(live)]
    points.sort(key=lambda point: point[0])
    return live, points


def _summary_texts(errors):
    """(rms, mean, stdev, max |error|) as display strings, or "N/A" for all
    four if empty.

    RMS leads: a signed mean of per-scalebar errors tends toward zero even
    when individual errors are large, since updateTransform() fits one
    chunk-wide scale via least squares. RMS matches Metashape's own
    Reference-pane scalebar error; the mean is kept only as a secondary
    bias indicator.
    """
    if not errors:
        return "N/A", "N/A", "N/A", "N/A"
    s = stats.compute_stats(errors)
    error_rms = stats.rms(errors)
    max_abs_error = max(abs(e) for e in errors)
    return f"{error_rms:.4f} m", f"{s.mean:.4f} m", f"{s.stdev:.4f} m", f"{max_abs_error:.4f} m"


def _refresh_panel(panel, chunk, pair_keys, should_exist, created, threshold=None):
    live, points = _collect(chunk, pair_keys)
    errors = [error for _, error in points]
    panel.update_counts(should_exist, created, len(live))
    panel.update_chart(points, threshold=threshold)
    panel.update_summary(*_summary_texts(errors))
    return live


def _get_chunk_and_pairs():
    """Shared guards for both entry points. Returns (chunk, found_pairs), or
    None after showing a messageBox."""
    if QtWidgets is None:
        Metashape.app.messageBox(
            "No Qt binding (PySide6/PySide2) is available in this Metashape "
            "Python environment, so the Scaling panel cannot be shown."
        )
        return None

    chunk = get_active_chunk()
    if chunk is None:
        return None

    found_pairs = pairs.find_stereo_pairs(chunk.cameras)
    if not found_pairs:
        Metashape.app.messageBox(_NO_STEREO_PAIRS_MESSAGE)
        return None

    return chunk, found_pairs


def _open_stats_panel(chunk, pair_keys, should_exist, created):
    global _active_panel

    if _active_panel is not None:
        try:
            _active_panel.close()
        except Exception:
            pass

    panel = dialogs.StatsPanel()

    def _on_filter_requested(threshold):
        live, _points = _collect(chunk, pair_keys)
        errors_by_index = {i: _scalebar_error(sb, chunk) for i, sb in enumerate(live)}
        _keep_indices, remove_indices = stats.filter_by_threshold(errors_by_index, threshold)
        to_remove = [live[i] for i in remove_indices]
        if to_remove:
            chunk.remove(to_remove)
            chunk.updateTransform()
        _refresh_panel(panel, chunk, pair_keys, should_exist, created, threshold=threshold)

    panel.filter_requested.connect(_on_filter_requested)
    _refresh_panel(panel, chunk, pair_keys, should_exist, created, threshold=panel.current_threshold)
    panel.show()

    _active_panel = panel
    return panel


def run():
    result = _get_chunk_and_pairs()
    if result is None:
        return
    chunk, found_pairs = result

    values = dialogs.BaselineDialog.get_values(default_distance=dialogs.DEFAULT_BASELINE_M)
    if values is None:
        return
    distance, optimize = values

    pair_keys = {_pair_key(left, right) for left, right in found_pairs}

    created = 0
    for left, right in found_pairs:
        if _find_existing_scalebar(chunk, left, right) is None:
            scalebar = chunk.addScalebar(left, right)
            scalebar.reference.distance = distance
            created += 1

    chunk.updateTransform()
    if optimize:
        chunk.optimizeCameras()

    should_exist = len(found_pairs)
    _open_stats_panel(chunk, pair_keys, should_exist, created)


def run_filter_only():
    result = _get_chunk_and_pairs()
    if result is None:
        return
    chunk, found_pairs = result

    pair_keys = {_pair_key(left, right) for left, right in found_pairs}
    live = _our_scalebars(chunk, pair_keys)
    if not live:
        Metashape.app.messageBox(
            "No existing scalebars were found for this chunk's stereo "
            "pairs, so there is nothing to filter yet. Run \"Scaling\" "
            "first to create scalebars."
        )
        return

    should_exist = len(found_pairs)
    _open_stats_panel(chunk, pair_keys, should_exist, len(live))
