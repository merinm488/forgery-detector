"""Edge Analysis — detects splice boundaries via edge density anomalies."""

import numpy as np
from PIL import Image, ImageFilter
import config
from .utils import image_to_grid, normalize_score


def run_edge_analysis(image_path):
    """
    Analyze edge patterns to detect splice boundaries.

    Steps:
    1. Convert to grayscale
    2. Apply edge detection (PIL edge enhancement + threshold)
    3. Block-based edge density analysis
    4. Identify outlier blocks with unusually high edge density

    Returns: dict with score, findings, details
    """
    img = Image.open(image_path).convert('L')

    # Edge detection via PIL
    edge_enhanced = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
    edge_array = np.array(edge_enhanced, dtype=np.float64)

    # Simple gradient-based edge detection (Sobel-like)
    img_array = np.array(img, dtype=np.float64)
    h, w = img_array.shape

    # Horizontal gradient
    grad_x = np.zeros_like(img_array)
    grad_x[:, 1:] = np.abs(img_array[:, 1:] - img_array[:, :-1])

    # Vertical gradient
    grad_y = np.zeros_like(img_array)
    grad_y[1:, :] = np.abs(img_array[1:, :] - img_array[:-1, :])

    # Combined edge magnitude
    edge_magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)

    # Block-based edge density
    blocks, positions = image_to_grid(edge_magnitude, config.EDGE_BLOCK_SIZE)
    if not blocks:
        return {
            'score': 0.0,
            'findings': ['Image too small for edge block analysis.'],
            'details': {},
        }

    block_densities = [np.mean(b) for b in blocks]

    overall_mean = np.mean(block_densities)
    overall_std = np.std(block_densities)

    # Identify outlier blocks
    outlier_threshold = overall_mean + 2 * (overall_std if overall_std > 0 else 1)
    outliers = [(pos, d) for pos, d in zip(positions, block_densities) if d > outlier_threshold]
    outlier_ratio = len(outliers) / len(blocks)

    # Check for clustering of edge outliers (splice boundary would be a line, not random)
    outlier_score = normalize_score(outlier_ratio, 0.2)

    # Check variance of edge densities
    variance_score = normalize_score(overall_std, 30.0)

    score = min((outlier_score * 0.6 + variance_score * 0.4), 1.0)

    findings = []
    if score > 0.6:
        findings.append(f'High edge density anomalies ({len(outliers)} outlier blocks) suggest splice boundaries.')
    if score > 0.3:
        findings.append(f'{len(outliers)} of {len(blocks)} blocks show unusual edge density.')
    if score < 0.3:
        findings.append('Edge patterns appear natural and consistent.')

    return {
        'score': round(score, 4),
        'findings': findings,
        'details': {
            'mean_edge_density': round(float(overall_mean), 2),
            'edge_density_std': round(float(overall_std), 2),
            'outlier_block_count': len(outliers),
            'total_blocks': len(blocks),
            'outlier_ratio': round(float(outlier_ratio), 4),
        },
    }
