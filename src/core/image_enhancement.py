"""
Image enhancement algorithms.
"""

import cv2
import numpy as np


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
