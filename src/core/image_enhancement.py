"""
Image enhancement algorithms.
"""

import cv2

from src.core.gray_world import apply_gray_world_enhancement, DEFAULT_PARAMS as GRAY_WORLD_DEFAULTS


def apply_clahe_enhancement(image, clip_limit=2.0, tile_grid_size=(4, 4)):
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization) enhancement to an image.
    
    Args:
        image (numpy.ndarray): Input image (BGR format)
        clip_limit (float): Threshold for contrast limiting. Default is 2.0
        tile_grid_size (tuple): Size of grid for histogram equalization. Default is (4, 4)
    
    Returns:
        numpy.ndarray: Enhanced image
    """
    if image is None:
        raise ValueError("Input image cannot be None")
    
    if len(image.shape) != 3 or image.shape[2] != 3:
        raise ValueError("Input image must be a 3-channel BGR image")
    
    # Create CLAHE object
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    
    # Apply CLAHE to each channel
    enhanced_image = image.copy()
    for channel in range(3):
        enhanced_image[:, :, channel] = clahe.apply(enhanced_image[:, :, channel])

    return enhanced_image


# Registry: every enhancement method shares the signature
# f(image: np.ndarray BGR uint8, **params) -> np.ndarray BGR uint8, so
# callers (batch processing, CLI, the compare viewer) never need to know
# which algorithm they're dispatching to.
ENHANCEMENT_METHODS = {
    "clahe": apply_clahe_enhancement,
    "gray_world": apply_gray_world_enhancement,
}

# Display names for the UI (kept separate from the internal registry key,
# since "gray_world" only names one of the pipeline's twelve operations).
METHOD_DISPLAY_NAMES = {
    "clahe": "CLAHE",
    "gray_world": "Adaptive Grading",
}

DEFAULT_PARAMS = {
    "clahe": {"clip_limit": 2.0, "tile_grid_size": (4, 4)},
    "gray_world": GRAY_WORLD_DEFAULTS,
}

# UI slider specs for gray_world's user-facing parameters: (min, max, step).
# dehaze_omega is deliberately excluded -- it's an internal dark-channel-prior
# tuning constant (see gray_world.py), not something meaningfully judged by
# eye, so it stays fixed at its default rather than exposed as a slider.
GRAY_WORLD_PARAM_SPECS = {
    "gray_world": (0.0, 1.0, 0.05),
    "warmth": (-2.0, 2.0, 0.1),
    "tint": (-2.0, 2.0, 0.1),
    "saturation": (0.0, 2.0, 0.05),
    "blue_reduction": (0.0, 0.8, 0.05),
    "brightness": (-0.5, 0.5, 0.02),
    "contrast": (-0.5, 0.5, 0.02),
    "shadows": (0.0, 0.5, 0.02),
    "blacks": (0.0, 0.3, 0.02),
    "highlights": (0.0, 0.5, 0.02),
    "dehaze_strength": (0.0, 0.6, 0.02),
}


def get_enhancement_function(method):
    """Look up an enhancement method by its registry key (e.g. "clahe")."""
    try:
        return ENHANCEMENT_METHODS[method]
    except KeyError:
        raise ValueError(f"Unknown enhancement method: {method!r}") from None


def warmup_method(method):
    """Force any one-time backend initialization `method` needs to happen
    now, on the calling thread. Call once before dispatching a batch of
    process_single_image calls across a ThreadPoolExecutor -- see
    gray_world.warmup()'s docstring for why this matters on Windows."""
    if method == "gray_world":
        from src.core.gray_world import warmup
        warmup()
