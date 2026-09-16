"""Stereo camera pair matching (case-insensitive left/right naming convention)."""

import Metashape


def _group_by_side(cameras):
    left_cameras = {}
    right_cameras = {}

    for camera in cameras:
        if camera.type != Metashape.Camera.Type.Regular:
            continue

        parts = camera.label.split("_")
        if len(parts) < 3:
            continue

        prefix = "_".join(parts[:-2])
        side = parts[-2]
        number = parts[-1]
        key = f"{prefix}_{number}"

        side_lower = side.lower()
        if side_lower == "left":
            left_cameras[key] = camera
        elif side_lower == "right":
            right_cameras[key] = camera

    return left_cameras, right_cameras


def find_stereo_pairs(cameras):
    """Return a list of (left_camera, right_camera) tuples matched by naming key."""
    left_cameras, right_cameras = _group_by_side(cameras)

    pairs = []
    for key in left_cameras:
        if key in right_cameras:
            pairs.append((left_cameras[key], right_cameras[key]))

    return pairs
