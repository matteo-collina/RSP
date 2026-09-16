"""Parsing for scripts/scalebars.csv (marker1,marker2,distance_m,accuracy_m; no header)."""

import os
from dataclasses import dataclass

_DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scalebars.csv")


@dataclass
class ScalebarSpec:
    marker1: str
    marker2: str
    distance: float
    accuracy: float


def load_rsp_scalebars(path=None):
    if path is None:
        path = _DEFAULT_CSV_PATH

    if not os.path.isfile(path):
        raise FileNotFoundError(f"RSP scalebars CSV not found: {path}")

    specs = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(",")]
            marker1, marker2, distance, accuracy = parts

            specs.append(
                ScalebarSpec(
                    marker1=marker1,
                    marker2=marker2,
                    distance=float(distance),
                    accuracy=float(accuracy),
                )
            )

    return specs
