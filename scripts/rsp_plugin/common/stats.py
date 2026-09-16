"""Pure numeric stats used by scaling and calibration flows. No Metashape dependency."""

import statistics
from dataclasses import dataclass


@dataclass
class Stats:
    median: float
    mean: float
    stdev: float
    min: float
    max: float
    cv: float


def compute_stats(distances):
    median = statistics.median(distances)
    mean = statistics.mean(distances)
    stdev = statistics.stdev(distances) if len(distances) > 1 else 0.0
    cv = (stdev / median) * 100 if median > 0 else 0

    return Stats(
        median=median,
        mean=mean,
        stdev=stdev,
        min=min(distances),
        max=max(distances),
        cv=cv,
    )


def quality_label(cv):
    if cv < 2.0:
        return "Excellent consistency (CV < 2%)"
    elif cv < 5.0:
        return "Good consistency (CV < 5%)"
    elif cv < 10.0:
        return "Moderate consistency (CV < 10%) - consider recalibration"
    else:
        return "High variation (CV >= 10%) - recalibrate cameras"


def scalebar_error(estimated_distance, reference_distance):
    return estimated_distance - reference_distance


def rms(values):
    """Root-mean-square of a list of signed values. Unlike a plain mean,
    RMS can't cancel out large positive and negative errors, so it reflects
    the real spread and matches Metashape's Reference-pane scalebar error."""
    if not values:
        return 0.0
    return (sum(v * v for v in values) / len(values)) ** 0.5


def filter_by_threshold(errors, threshold):
    """Split keys by |error| vs threshold.

    A value exactly equal to threshold is kept (removal requires strictly
    greater), so re-applying the same threshold repeatedly is idempotent.
    """
    keep_keys = []
    remove_keys = []

    for key, error in errors.items():
        if abs(error) > threshold:
            remove_keys.append(key)
        else:
            keep_keys.append(key)

    return keep_keys, remove_keys
