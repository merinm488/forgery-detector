"""Copy-Move Detection — finds duplicated regions via block matching."""

import numpy as np
from PIL import Image
import config
from .utils import normalize_score


def _extract_block_features(block):
    """Extract a richer feature vector from a block using DCT-like coefficients."""
    # Use row and column averages as features (like a poor man's DCT)
    row_means = np.mean(block, axis=1)  # one value per row
    col_means = np.mean(block, axis=0)  # one value per column

    # Downsample to fixed length
    n_features = 8
    row_sampled = np.interp(
        np.linspace(0, len(row_means) - 1, n_features),
        np.arange(len(row_means)),
        row_means,
    )
    col_sampled = np.interp(
        np.linspace(0, len(col_means) - 1, n_features),
        np.arange(len(col_means)),
        col_means,
    )

    # Add local gradient info
    grad_x = np.mean(np.abs(np.diff(block, axis=1)))
    grad_y = np.mean(np.abs(np.diff(block, axis=0)))

    features = np.concatenate([row_sampled, col_sampled, [grad_x, grad_y]])
    return features


def _is_low_variance(block, threshold=5.0):
    """Check if a block is low-variance (uniform region like background)."""
    return np.std(block) < threshold


def run_copy_move_analysis(image_path):
    """
    Detect duplicated (copy-moved) regions.

    Steps:
    1. Resize large images for tractability
    2. Divide into overlapping blocks
    3. Skip low-variance (uniform) blocks to avoid false matches
    4. Extract feature vector per block
    5. Find similar block pairs that are spatially distant
    6. Require match clustering for scoring

    Returns: dict with score, findings, details
    """
    img = Image.open(image_path).convert('L')

    # Resize for performance if needed
    original_size = img.size
    if max(img.size) > config.COPY_MOVE_MAX_DIMENSION:
        ratio = config.COPY_MOVE_MAX_DIMENSION / max(img.size)
        new_size = (int(img.width * ratio), int(img.height * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    img_array = np.array(img, dtype=np.float64)
    h, w = img_array.shape
    block_size = config.COPY_MOVE_BLOCK_SIZE
    step = config.COPY_MOVE_STEP

    # Extract overlapping blocks with features, skipping uniform regions
    features_list = []
    positions = []
    skipped_uniform = 0

    for y in range(0, h - block_size, step):
        for x in range(0, w - block_size, step):
            block = img_array[y:y + block_size, x:x + block_size]
            if _is_low_variance(block):
                skipped_uniform += 1
                continue
            features = _extract_block_features(block)
            features_list.append(features)
            positions.append((x, y))

    if len(features_list) < 2:
        return {
            'score': 0.0,
            'findings': ['Not enough textured regions for copy-move analysis.'],
            'details': {
                'total_blocks': 0,
                'skipped_uniform': skipped_uniform,
            },
        }

    # Subsample if too many blocks
    if len(features_list) > config.COPY_MOVE_MAX_SAMPLES:
        indices = np.random.choice(len(features_list), config.COPY_MOVE_MAX_SAMPLES, replace=False)
        features_list = [features_list[i] for i in indices]
        positions = [positions[i] for i in indices]

    # Normalize features per-dimension (z-score normalization)
    features_matrix = np.array(features_list)
    col_mean = features_matrix.mean(axis=0)
    col_std = features_matrix.std(axis=0)
    col_std[col_std == 0] = 1
    features_matrix = (features_matrix - col_mean) / col_std

    # Find similar pairs using Euclidean distance
    sim_threshold = 0.8  # Tight threshold in normalized feature space
    dist_threshold = config.COPY_MOVE_DISTANCE_THRESHOLD

    match_count = 0
    match_details = []
    match_positions = []

    for i in range(len(features_matrix)):
        if match_count >= 100:
            break
        # Euclidean distance to all blocks after i
        diffs = features_matrix[i + 1:] - features_matrix[i]
        distances = np.sqrt(np.sum(diffs ** 2, axis=1))

        for j_offset in np.where(distances < sim_threshold)[0]:
            j = i + 1 + j_offset
            x1, y1 = positions[i]
            x2, y2 = positions[j]
            spatial_dist = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

            if spatial_dist > dist_threshold:
                match_count += 1
                match_positions.append(((x1, y1), (x2, y2)))
                if len(match_details) < 5:
                    match_details.append({
                        'block_a': (int(x1), int(y1)),
                        'block_b': (int(x2), int(y2)),
                        'distance': round(float(distances[j_offset]), 4),
                        'spatial_dist': round(float(spatial_dist), 1),
                    })

    # Scoring: compute match ratio and check spatial coherence
    # match_ratio = proportion of blocks involved in matches
    match_ratio = match_count / max(len(features_list), 1)

    # For genuine images, some incidental matches are expected (similar textures).
    # True copy-move produces dense, spatially coherent clusters of matches.
    # We check for spatial coherence: matches should form tight spatial clusters
    # with consistent offset vectors (source→dest translation is roughly constant).
    coherence_score = 0.0
    if match_count >= 5:
        # Compute offset vectors for all matches
        offsets = []
        for (x1, y1), (x2, y2) in match_positions:
            offsets.append((x2 - x1, y2 - y1))

        # Cluster offsets by rounding to block_size multiples
        offset_buckets = {}
        for dx, dy in offsets:
            key = (round(dx / (block_size * 2)), round(dy / (block_size * 2)))
            offset_buckets[key] = offset_buckets.get(key, 0) + 1

        # The largest cluster of consistent offsets indicates a true copy-move
        if offset_buckets:
            max_cluster = max(offset_buckets.values())
            # A coherent copy-move has many matches with the same offset
            coherence_score = normalize_score(max_cluster, max(len(features_list) * 0.05, 5))

    # Match ratio contributes but is downweighted (noisy)
    ratio_score = normalize_score(match_ratio, 0.5)

    score = min(ratio_score * 0.3 + coherence_score * 0.7, 1.0)

    findings = []
    if match_count > 10:
        findings.append(f'{match_count} similar region pairs found — strong copy-move evidence.')
    elif match_count > 3:
        findings.append(f'{match_count} similar region pairs detected — possible copy-move.')
    elif match_count > 0:
        findings.append(f'{match_count} similar region pair(s) detected — minor similarity.')
    else:
        findings.append('No duplicated regions detected.')

    return {
        'score': round(score, 4),
        'findings': findings,
        'details': {
            'total_blocks_analyzed': len(features_list),
            'skipped_uniform_blocks': skipped_uniform,
            'matching_pairs': match_count,
            'similarity_threshold': sim_threshold,
            'min_spatial_distance': dist_threshold,
            'sample_matches': match_details,
            'original_image_size': f'{original_size[0]}x{original_size[1]}',
        },
    }
