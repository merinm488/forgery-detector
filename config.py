import os

# Flask settings
SECRET_KEY = 'lucid-plus-forgery-detector-dev'
UPLOAD_FOLDER = os.path.join('static', 'uploads')
OUTPUT_FOLDER = os.path.join('output')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}

# ELA settings
ELA_QUALITY = 85
ELA_SCALE = 15
ELA_GRID_SIZE = 32

# Noise analysis
NOISE_BLOCK_SIZE = 64
NOISE_MEDIAN_FILTER_SIZE = 5

# Edge analysis
EDGE_BLOCK_SIZE = 32
EDGE_THRESHOLD = 128

# Copy-move detection
COPY_MOVE_BLOCK_SIZE = 16
COPY_MOVE_STEP = 8
COPY_MOVE_SIMILARITY_THRESHOLD = 0.95
COPY_MOVE_DISTANCE_THRESHOLD = 50
COPY_MOVE_MAX_DIMENSION = 512
COPY_MOVE_MAX_SAMPLES = 500

# Scoring weights
TECHNIQUE_WEIGHTS = {
    'ela': 0.30,
    'metadata': 0.20,
    'noise': 0.20,
    'edge': 0.15,
    'copy_move': 0.15
}

# Risk level thresholds
RISK_THRESHOLDS = [
    (0.0,  0.2,  'LOW',          'Document appears genuine based on automated analysis.'),
    (0.2,  0.4,  'LOW-MODERATE', 'Minor anomalies detected, but within acceptable range.'),
    (0.4,  0.6,  'MODERATE',     'Some suspicious patterns detected. Manual review recommended.'),
    (0.6,  0.8,  'HIGH',         'Significant indicators of potential forgery detected.'),
    (0.8,  1.01, 'CRITICAL',     'Strong evidence of image manipulation detected.'),
]
