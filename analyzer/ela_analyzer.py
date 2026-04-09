"""Error Level Analysis — detects localized editing via re-compression artifacts."""

import numpy as np
from PIL import Image
import io
import config
from .utils import image_to_grid, normalize_score, save_visualization


def run_ela(image_path, analysis_id=''):
    """
    Perform Error Level Analysis on an image.

    Steps:
    1. Open original image, convert to RGB
    2. Re-compress at JPEG quality ELA_QUALITY
    3. Compute pixel-wise absolute difference, amplify by ELA_SCALE
    4. Analyze grid-based variance of error levels
    5. Generate visual ELA heatmap

    Returns: dict with score, findings, details, visualization_path
    """
    original = Image.open(image_path).convert('RGB')
    original_array = np.array(original, dtype=np.float64)

    # Re-compress at configured quality
    buffer = io.BytesIO()
    original.save(buffer, format='JPEG', quality=config.ELA_QUALITY)
    buffer.seek(0)
    recompressed = Image.open(buffer).convert('RGB')
    recompressed_array = np.array(recompressed, dtype=np.float64)

    # Compute error (pixel-wise diff), amplified
    diff = np.abs(original_array - recompressed_array) * config.ELA_SCALE
    diff = np.clip(diff, 0, 255).astype(np.uint8)

    # Grayscale error map for analysis
    gray_diff = np.mean(diff, axis=2)

    # Grid-based variance analysis
    blocks, positions = image_to_grid(gray_diff, config.ELA_GRID_SIZE)
    if not blocks:
        return {
            'score': 0.0,
            'findings': ['Image too small for grid-based ELA analysis.'],
            'details': {},
            'visualization_path': None,
        }

    block_means = [np.mean(b) for b in blocks]
    block_stds = [np.std(b) for b in blocks]

    overall_mean = np.mean(block_means)
    overall_std = np.std(block_means)

    findings = []
    anomaly_count = 0

    # Detect blocks with error level significantly different from average
    threshold = overall_mean + 1.5 * (overall_std if overall_std > 0 else 1)
    for i, (mean_val, pos) in enumerate(zip(block_means, positions)):
        if mean_val > threshold:
            anomaly_count += 1

    anomaly_ratio = anomaly_count / len(blocks) if blocks else 0

    # High variance in error levels across blocks suggests inconsistent editing
    variance_score = normalize_score(overall_std, 40.0)
    anomaly_score = normalize_score(anomaly_ratio, 0.3)

    score = min((variance_score * 0.5 + anomaly_score * 0.5), 1.0)

    if score > 0.6:
        findings.append(f'High ELA variance (std={overall_std:.1f}) suggests localized editing.')
    if score > 0.3:
        findings.append(f'{anomaly_count} of {len(blocks)} blocks show anomalous error levels ({anomaly_ratio:.1%}).')
    if score < 0.3:
        findings.append('Error levels appear consistent across the image.')

    # Generate visualization heatmap
    ela_vis = Image.fromarray(diff)
    vis_path = save_visualization(ela_vis, 'ela', analysis_id)

    return {
        'score': round(score, 4),
        'findings': findings,
        'details': {
            'overall_mean_error': round(float(overall_mean), 2),
            'error_std_across_blocks': round(float(overall_std), 2),
            'anomalous_block_count': anomaly_count,
            'total_blocks': len(blocks),
            'anomaly_ratio': round(float(anomaly_ratio), 4),
        },
        'visualization_path': vis_path,
    }
