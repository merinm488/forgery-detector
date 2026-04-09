import os
import time
from PIL import Image
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
VIS_DIR = os.path.join(BASE_DIR, 'static', 'visualizations')


def save_visualization(image, prefix, analysis_id=''):
    """Save a PIL image as a visualization and return its web-accessible path."""
    os.makedirs(VIS_DIR, exist_ok=True)
    filename = f"{prefix}_{analysis_id or int(time.time())}.png"
    path = os.path.join(VIS_DIR, filename)
    image.save(path)
    return f"visualizations/{filename}"


def image_to_grid(image_array, block_size):
    """Split a 2D numpy array into non-overlapping blocks with positions."""
    h, w = image_array.shape[:2]
    blocks = []
    positions = []
    for y in range(0, h - block_size, block_size):
        for x in range(0, w - block_size, block_size):
            blocks.append(image_array[y:y + block_size, x:x + block_size])
            positions.append((x, y))
    return blocks, positions


def normalize_score(raw_value, max_value):
    """Clamp and normalize a value to [0.0, 1.0]."""
    return min(max(raw_value / max_value, 0.0), 1.0)
