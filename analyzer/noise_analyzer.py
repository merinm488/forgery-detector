"""Noise Pattern Analysis — detects splicing from different sources via noise inconsistency."""

import numpy as np
from PIL import Image, ImageFilter
import config
from .utils import image_to_grid, normalize_score


def run_noise_analysis(image_path):
    """
    Analyze noise patterns for inconsistency.

    Steps:
    1. Convert to grayscale float
    2. Apply median filter to get denoised version
    3. Compute noise residual = original - denoised
    4. Block-based noise std deviation analysis
    5. Compare spatial halves (left/right, top/bottom) for asymmetry
    6. Identify outlier blocks with anomalous noise levels

    Returns: dict with score, findings, details
    """
    img = Image.open(image_path).convert('L')
    img_array = np.array(img, dtype=np.float64)

    # Denoise using median filter
    pil_img = Image.fromarray(img_array.astype(np.uint8))
    filtered = pil_img.filter(ImageFilter.MedianFilter(size=config.NOISE_MEDIAN_FILTER_SIZE))
    denoised = np.array(filtered, dtype=np.float64)

    # Noise residual
    noise = img_array - denoised

    h, w = noise.shape
    block_size = config.NOISE_BLOCK_SIZE

    # Block-based analysis
    blocks, positions = image_to_grid(noise, block_size)
    if not blocks:
        return {
            'score': 0.0,
            'findings': ['Image too small for noise block analysis.'],
            'details': {},
        }

    block_stds = np.array([np.std(b) for b in blocks])
    n_blocks = len(blocks)

    overall_mean = np.mean(block_stds)
    overall_std = np.std(block_stds)

    # --- Signal 1: Spatial asymmetry (left vs right, top vs bottom) ---
    # Split blocks into spatial halves
    mid_x = w / 2
    mid_y = h / 2
    left_stds, right_stds = [], []
    top_stds, bottom_stds = [], []

    for std_val, (bx, by) in zip(block_stds, positions):
        block_center_x = bx + block_size / 2
        block_center_y = by + block_size / 2
        if block_center_x < mid_x:
            left_stds.append(std_val)
        else:
            right_stds.append(std_val)
        if block_center_y < mid_y:
            top_stds.append(std_val)
        else:
            bottom_stds.append(std_val)

    # Asymmetry = ratio of std difference to overall mean
    lr_diff = abs(np.mean(left_stds) - np.mean(right_stds)) if left_stds and right_stds else 0
    tb_diff = abs(np.mean(top_stds) - np.mean(bottom_stds)) if top_stds and bottom_stds else 0
    max_asymmetry = max(lr_diff, tb_diff) / (overall_mean if overall_mean > 0 else 1)

    # Genuine images have layout-driven variation; spliced images show strong asymmetry
    # Structured documents naturally have high asymmetry, so threshold must be generous
    asymmetry_score = normalize_score(max_asymmetry, 2.5)

    # --- Signal 2: Outlier blocks using robust statistics ---
    median_std = np.median(block_stds)
    mad = np.median(np.abs(block_stds - median_std))
    scaled_mad = mad * 1.4826 if mad > 0 else overall_std * 0.5
    outlier_threshold = median_std + 3.5 * scaled_mad
    outliers = int(np.sum(block_stds > outlier_threshold))
    outlier_ratio = outliers / n_blocks
    outlier_score = normalize_score(outlier_ratio, 0.3)

    # Combined score — asymmetry is the primary signal for splicing
    score = min((asymmetry_score * 0.6 + outlier_score * 0.4), 1.0)

    findings = []
    if score > 0.6:
        findings.append(
            f'High noise inconsistency (LR diff={lr_diff:.1f}, TB diff={tb_diff:.1f}) '
            f'suggests splicing from different sources.'
        )
    if outliers > 0:
        findings.append(f'{outliers} of {n_blocks} blocks have anomalous noise levels.')
    if score < 0.3:
        findings.append('Noise patterns appear consistent across the image.')

    return {
        'score': round(score, 4),
        'findings': findings,
        'details': {
            'mean_noise_std': round(float(overall_mean), 2),
            'std_of_noise_stds': round(float(overall_std), 2),
            'left_right_asymmetry': round(float(lr_diff), 2),
            'top_bottom_asymmetry': round(float(tb_diff), 2),
            'max_asymmetry_ratio': round(float(max_asymmetry), 4),
            'outlier_block_count': outliers,
            'total_blocks': n_blocks,
        },
    }
