"""Metashape environment helpers shared by the scaling and calibration flows."""

import Metashape


def get_active_chunk():
    document = Metashape.app.document
    if document is None or document.chunk is None:
        Metashape.app.messageBox("No active chunk found. Please open a Metashape project with a chunk first.")
        return None

    return document.chunk


def estimated_distance(scalebar, chunk):
    """Real-world distance between a scalebar's two endpoints, or None if it
    can't be measured: an endpoint camera isn't aligned (center is None) or
    the chunk has no scale yet. Metashape raises a bare "invalid arguments"
    AttributeError on Vector arithmetic with None, so check first."""
    center0 = scalebar.point0.center
    center1 = scalebar.point1.center
    scale = chunk.transform.scale
    if center0 is None or center1 is None or scale is None:
        return None
    return (center1 - center0).norm() * scale
