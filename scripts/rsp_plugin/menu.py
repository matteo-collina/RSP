"""RSP menu registration for Metashape's Tools menu.

Registers, via Metashape.app.addMenuItem ("/" nests a label under a
top-level submenu):

    RSP/Scaling              -> rsp_plugin.scaling.flow.run
    RSP/Filter Scalebars     -> rsp_plugin.scaling.flow.run_filter_only
    RSP/----separator----
    RSP/Calibration Wizard   -> rsp_plugin.calibration.flow.run

register() is idempotent: each label is removed (if present) before being
re-added, so importing this module more than once in a session replaces
entries instead of duplicating them. Failures propagate to the caller
(rsp_plugin/__init__.py), which turns them into a messageBox.
"""

import traceback

import Metashape

from .calibration import flow as calibration_flow
from .scaling import flow as scaling_flow

SCALING_LABEL = "RSP/Scaling"
FILTER_LABEL = "RSP/Filter Scalebars"
SEPARATOR_LABEL = "RSP"
CALIBRATION_LABEL = "RSP/Calibration Wizard"


def _remove_if_present(label):
    try:
        Metashape.app.removeMenuItem(label)
    except Exception:
        pass


def _reported(label, callback):
    """Wrap a menu callback so an exception prints its full traceback to the
    Console and shows a messageBox, instead of a bare one-line error."""

    def wrapper():
        try:
            callback()
        except Exception as e:
            details = traceback.format_exc()
            print(f"{label} failed:\n{details}")
            Metashape.app.messageBox(f"{label} failed: {type(e).__name__}: {e}\n\n{details}")

    return wrapper


def register():
    _remove_if_present(SCALING_LABEL)
    Metashape.app.addMenuItem(SCALING_LABEL, _reported(SCALING_LABEL, scaling_flow.run))

    _remove_if_present(FILTER_LABEL)
    Metashape.app.addMenuItem(FILTER_LABEL, _reported(FILTER_LABEL, scaling_flow.run_filter_only))

    Metashape.app.addMenuSeparator(SEPARATOR_LABEL)

    _remove_if_present(CALIBRATION_LABEL)
    Metashape.app.addMenuItem(CALIBRATION_LABEL, _reported(CALIBRATION_LABEL, calibration_flow.run))
