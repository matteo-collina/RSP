"""Metashape environment helpers shared by the scaling and calibration flows."""

import Metashape


def get_active_chunk():
    document = Metashape.app.document
    if document is None or document.chunk is None:
        Metashape.app.messageBox("No active chunk found. Please open a Metashape project with a chunk first.")
        return None

    return document.chunk


def estimated_distance(scalebar, chunk):
    """Real-world distance between a scalebar's two endpoints."""
    return (scalebar.point1.center - scalebar.point0.center).norm() * chunk.transform.scale
