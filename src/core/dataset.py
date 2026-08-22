"""
Dataset state for the three camera slots (left/center/right).

"""

from collections.abc import MutableMapping
from dataclasses import dataclass, field


@dataclass
class CameraSlot:
    """State for one camera folder (left/center/right)."""

    prefix: str
    directory: str = ""


@dataclass
class DatasetState:
    """Per-camera folder state."""

    slots: dict = field(default_factory=lambda: {
        "center": CameraSlot("center"),
        "left": CameraSlot("left"),
        "right": CameraSlot("right"),
    })


class PathsView(MutableMapping):
    """Live dict-like view over a DatasetState's per-camera directories.

    Kept so code written against the old `self.paths` flat dict (browse
    buttons, drag-and-drop, validation, CLI-mirroring report generation)
    doesn't need to change: reads/writes go straight through to the
    same CameraSlot objects the gallery uses, so there is exactly one
    source of truth.
    """

    def __init__(self, dataset_state):
        self._dataset = dataset_state

    def __getitem__(self, key):
        return self._dataset.slots[key].directory

    def __setitem__(self, key, value):
        self._dataset.slots[key].directory = value

    def __delitem__(self, key):
        # There are always exactly three fixed camera slots -- "deleting"
        # one isn't a meaningful operation (and resetting its directory to
        # "" here would violate MutableMapping's contract that `del d[k]`
        # makes `k in d` False afterward, since the slot itself remains).
        # Use `paths[prefix] = ""` to clear a folder selection instead.
        raise TypeError(
            f"camera slot {key!r} cannot be deleted; assign paths[{key!r}] = '' to clear it"
        )

    def __iter__(self):
        return iter(self._dataset.slots)

    def __len__(self):
        return len(self._dataset.slots)

    def __repr__(self):
        return repr(dict(self))
