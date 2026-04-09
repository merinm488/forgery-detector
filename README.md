# LucidPlus — ID Document Forgery Detector

A Flask web application that analyzes ID document images for signs of digital manipulation using 5 algorithmic forgery detection techniques. No machine learning models required — built entirely with **Pillow** and **NumPy**.

**Live Demo:** [https://forgery-detector-pt2k.onrender.com](https://forgery-detector-pt2k.onrender.com)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Live Demo](#live-demo)
- [Quick Start (Local)](#quick-start-local)
- [How It Works](#how-it-works)
- [Detection Techniques](#detection-techniques)
- [Scoring System](#scoring-system)
- [Project Structure](#project-structure)
- [Sample Test Images](#sample-test-images)
- [Configuration](#configuration)
- [Dependencies](#dependencies)
- [Technical Design Decisions](#technical-design-decisions)
- [Limitations & Future Improvements](#limitations--future-improvements)

---

## Overview

This project addresses the problem of detecting digital manipulation in ID document images (passports, national ID cards, driver's licenses, etc.) using purely algorithmic techniques. It was built as part of a **Junior AI/ML Engineer assignment** to demonstrate:

1. **Algorithmic understanding** — implementing well-known image forensics algorithms from scratch
2. **System design** — building a multi-technique ensemble with weighted scoring
3. **Practical engineering** — delivering a complete, deployable web application

The system analyzes uploaded images through 5 complementary detection techniques, each targeting a different type of forgery artifact, and produces an interpretable risk assessment with detailed findings.

---

## Features

- **5 Detection Techniques**: Error Level Analysis, Metadata Inspection, Noise Pattern Analysis, Edge Detection, Copy-Move Detection
- **Weighted Scoring**: Each technique contributes a configurable weighted score to an overall risk assessment (LOW through CRITICAL)
- **Visual Reports**: ELA heatmap generation showing compression artifact regions, per-technique score bars, detailed findings list
- **Drag & Drop Upload**: Modern web interface with file preview and format validation
- **JSON Reports**: Machine-readable reports saved to `output/` for programmatic access
- **Responsive Design**: Works on desktop, tablet, and mobile
- **No ML Dependency**: Purely algorithmic using Pillow and NumPy — fast, transparent, and interpretable
- **Sample Generator**: Built-in script to create genuine and tampered test images

---

## Live Demo

The application is deployed on Render and accessible at:

**[https://forgery-detector-pt2k.onrender.com](https://forgery-detector-pt2k.onrender.com)**

You can upload the sample images included in this repository (`samples/genuine/` and `samples/tampered/`) to see the detection in action.

---

## Quick Start (Local)

### Prerequisites

- Python 3.8+

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/merinm488/forgery-detector.git
cd LucidPlus

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Generate sample test images (optional)
python create_samples.py

# 5. Run the application
python app.py
```

---

## How It Works

### Data Flow

```
User uploads image
        |
        v
  File validation (format, size)
        |
        v
  Save to static/uploads/
        |
        v
  Run all 5 detection techniques in sequence:
    1. Error Level Analysis (ELA)
    2. Metadata / EXIF Analysis
    3. Noise Pattern Analysis
    4. Edge Density Analysis
    5. Copy-Move Detection
        |
        v
  Each technique returns: score [0-1], findings list, details dict
        |
        v
  Weighted scoring in report/generator.py
        |
        v
  Risk level determination (LOW / LOW-MODERATE / MODERATE / HIGH / CRITICAL)
        |
        v
  Save JSON report to output/
  Generate ELA visualization to static/visualizations/
        |
        v
  Render report.html with full results
```

### Architecture

The application follows a clean modular architecture:

- **`app.py`** — Flask routes, file upload handling, validation
- **`config.py`** — All tunable thresholds, weights, and settings in one place
- **`analyzer/`** — Each detection technique is a self-contained module
- **`report/`** — Report generation with weighted scoring logic
- **`templates/`** — Jinja2 HTML templates with base template inheritance
- **`static/`** — CSS, JavaScript, uploaded files, and generated visualizations

---

## Detection Techniques

| Technique | Weight | Target | What It Detects |
|-----------|--------|--------|-----------------|
| **Error Level Analysis** | 0.30 | Re-compression artifacts | Localized edits: clone stamping, text overlay, copy-paste |
| **Metadata Analysis** | 0.20 | EXIF/metadata inconsistencies | Editing software signatures, date mismatches, stripped metadata |
| **Noise Pattern Analysis** | 0.20 | Sensor noise inconsistency | Splicing from different cameras/sources, noise level asymmetry |
| **Edge Analysis** | 0.15 | Unnatural edge patterns | Splice boundaries between composited image regions |
| **Copy-Move Detection** | 0.15 | Duplicated regions | Copied seals, stamps, text, or patterns within the same image |

### Technique Details

#### 1. Error Level Analysis (ELA) — Weight: 0.30

**Principle:** When an image is re-saved as JPEG, all pixels are recompressed uniformly. Previously edited regions that were saved at a different quality level will show different error magnitudes upon re-compression.

**Algorithm:**
1. Re-save the uploaded image at JPEG quality 85
2. Compute pixel-wise absolute difference between original and recompressed version
3. Amplify differences 15x for visibility
4. Divide into 32x32 grids, compute per-block mean error
5. Flag blocks whose error level deviates >1.5 standard deviations from the global mean
6. Generate a color heatmap visualization for the report

**Why highest weight:** ELA is one of the most reliable techniques for detecting localized edits. It effectively catches clone-stamp usage, text overlay, and copy-paste operations — the most common forgery techniques on ID documents.

#### 2. Metadata / EXIF Analysis — Weight: 0.20

**Principle:** Camera-captured images contain rich EXIF metadata (camera model, timestamps, GPS). Edited images often have stripped or modified metadata, or contain signatures of editing software.

**Checks performed:**
- Missing EXIF data (suspicious for camera-captured documents)
- Known editing software names in metadata (Photoshop, GIMP, Lightroom, etc.)
- DateTime vs DateTimeOriginal date inconsistencies
- MakerNote references to editing tools
- Format anomalies (PNG without EXIF, BMP format)
- Very low resolution (<200px) indicating digital creation

**Why moderate weight:** Metadata can be stripped intentionally without forgery, or forged metadata can be planted. It is a strong signal but not conclusive alone.

#### 3. Noise Pattern Analysis — Weight: 0.20

**Principle:** Every camera sensor produces a characteristic noise pattern (PRNU — Photo Response Non-Uniformity). When regions from different images are spliced together, the noise patterns do not match.

**Algorithm:**
1. Convert to grayscale and estimate noise by subtracting a median-filtered version
2. Divide noise residual into 64x64 blocks
3. Compute standard deviation of noise per block
4. **Signal 1 — Spatial asymmetry:** Compare left vs right and top vs bottom halves for noise level differences (normalized to 2.5 threshold)
5. **Signal 2 — Outlier detection:** Use Median Absolute Deviation (MAD) with 3.5x scaled threshold for robust outlier detection
6. Combined score: 60% asymmetry + 40% outlier

**Why moderate weight:** Effective for detecting splicing but can be affected by legitimate variations (e.g., text vs photograph regions on an ID).

#### 4. Edge Analysis — Weight: 0.15

**Principle:** Splice boundaries create unnatural edge patterns — sharp transitions that do not match the natural edges in the rest of the image.

**Algorithm:**
1. Compute gradient magnitude using horizontal and vertical finite differences
2. Divide into 32x32 blocks, compute per-block edge density
3. Flag blocks with edge density >2 standard deviations above the mean
4. Scoring: 60% outlier ratio + 40% variance of edge densities

**Why lower weight:** Edge analysis catches splice boundaries but can also trigger on legitimate text edges, stamps, and security features on ID documents.

#### 5. Copy-Move Detection — Weight: 0.15

**Principle:** A common forgery technique is copying a region (e.g., a stamp or seal) and pasting it elsewhere in the same image. This creates two identical but spatially distant regions.

**Algorithm:**
1. Resize large images to max 512px for performance
2. Divide into overlapping 16x16 blocks (step 8)
3. Skip low-variance (uniform) blocks to avoid false matches on backgrounds
4. Extract 18-dimensional feature vectors: row/col means, gradients (8+8+2)
5. Z-score normalize features across all blocks
6. Find block pairs with Euclidean distance < 0.8 that are spatially distant (>50px)
7. **Spatial coherence check:** Cluster match offsets into buckets — true copy-move produces many matches with the same translation vector
8. Score: 30% match ratio + 70% coherence score

**Why lowest weight:** Effective for copy-move forgeries specifically, but many forgeries use external content rather than duplicating existing regions.

---

## Scoring System

Each technique returns a score in [0.0, 1.0]. The overall score is the weighted average:

```
overall_score = sum(technique_score x technique_weight) / sum(weights)
```

### Risk Levels

| Score Range | Risk Level | Color | Interpretation |
|-------------|-----------|-------|----------------|
| 0.0 – 0.2 | **LOW** | Green | Document appears genuine |
| 0.2 – 0.4 | **LOW-MODERATE** | Yellow | Minor anomalies, acceptable range |
| 0.4 – 0.6 | **MODERATE** | Orange | Suspicious patterns, manual review recommended |
| 0.6 – 0.8 | **HIGH** | Red | Significant forgery indicators |
| 0.8 – 1.0 | **CRITICAL** | Dark Red | Strong manipulation evidence |

### Report Output

Each analysis generates:
- **Overall risk score** displayed as a percentage ring (0-100)
- **Per-technique breakdown** with individual scores and weighted contributions
- **ELA heatmap** visualization comparing original vs error amplified image
- **Sorted findings list** with the most suspicious patterns first
- **Raw JSON data** (collapsible) with complete analysis details
- **JSON file** saved to `output/report_<id>.json` for programmatic access

---

## Project Structure

```
LucidPlus/
├── app.py                      # Flask app: routes, upload, validation
├── config.py                   # All tunable thresholds, weights, settings
├── requirements.txt            # Python dependencies
├── create_samples.py           # Generate genuine/tampered test images
├── README.md                   # This file
├── APPROACH.md                 # Detailed approach and design decisions
│
├── analyzer/
│   ├── __init__.py
│   ├── engine.py               # Orchestrator: runs all analyzers in sequence
│   ├── ela_analyzer.py         # Error Level Analysis (weight: 0.30)
│   ├── metadata_analyzer.py    # EXIF/metadata analysis (weight: 0.20)
│   ├── noise_analyzer.py       # Noise pattern inconsistency (weight: 0.20)
│   ├── edge_analyzer.py        # Edge/splice detection (weight: 0.15)
│   ├── copy_move_analyzer.py   # Duplicated region detection (weight: 0.15)
│   └── utils.py                # Shared helpers (grid, normalization, visualization)
│
├── report/
│   ├── __init__.py
│   └── generator.py            # Weighted scoring and risk report assembly
│
├── templates/
│   ├── base.html               # Base template with nav and footer
│   ├── index.html              # Upload page with drag & drop
│   └── report.html             # Analysis results display
│
├── static/
│   ├── css/style.css           # Responsive styling with risk-based color coding
│   ├── js/main.js              # Drag & drop, preview, score bar coloring
│   ├── uploads/                # Uploaded document images (gitignored)
│   └── visualizations/         # Generated ELA heatmaps (gitignored)
│
├── samples/
│   ├── genuine/                # Test images: authentic-looking ID cards
│   │   ├── genuine_1.jpg       # UK ID card with subtle noise
│   │   └── genuine_2.jpg       # Spanish ID card with natural variation
│   └── tampered/               # Test images: forged ID cards
│       ├── tampered_copy_move.jpg       # Region copied and pasted
│       ├── tampered_noise_splice.jpg    # Different noise patterns spliced
│       └── tampered_double_compress.jpg # Double JPEG compression + text edit
│
├── output/                     # Generated JSON reports (gitignored)
│
└── venv/                       # Virtual environment (gitignored)
```

---

## Sample Test Images

The project includes a script to generate test images:

```bash
python create_samples.py
```

This creates:

| Image | Type | Forgery Technique |
|-------|------|-------------------|
| `genuine_1.jpg` | Genuine | UK ID card with subtle natural noise |
| `genuine_2.jpg` | Genuine | Spanish ID card with natural variation |
| `tampered_copy_move.jpg` | Tampered | Bottom bar region copied and pasted elsewhere |
| `tampered_noise_splice.jpg` | Tampered | Left half (noise std=2) spliced with right half (noise std=12) |
| `tampered_double_compress.jpg` | Tampered | Saved at quality 50, reopened, text overwritten, saved again at quality 92 |

**Expected results:** Genuine samples should score LOW to LOW-MODERATE. Tampered samples should score MODERATE to HIGH depending on the forgery type.

---

## Configuration

All thresholds and weights are centralized in `config.py` for easy tuning:

| Setting | Default | Description |
|---------|---------|-------------|
| `ELA_QUALITY` | 85 | JPEG re-compression quality for ELA |
| `ELA_SCALE` | 15 | Error amplification factor |
| `ELA_GRID_SIZE` | 32 | Block size for ELA grid analysis |
| `NOISE_BLOCK_SIZE` | 64 | Block size for noise analysis |
| `NOISE_MEDIAN_FILTER_SIZE` | 5 | Median filter kernel size |
| `EDGE_BLOCK_SIZE` | 32 | Block size for edge analysis |
| `COPY_MOVE_BLOCK_SIZE` | 16 | Block size for copy-move detection |
| `COPY_MOVE_STEP` | 8 | Step size for overlapping blocks |
| `COPY_MOVE_SIMILARITY_THRESHOLD` | 0.95 | Cosine similarity threshold |
| `COPY_MOVE_DISTANCE_THRESHOLD` | 50 | Minimum spatial distance (px) |
| `COPY_MOVE_MAX_DIMENSION` | 512 | Max image dimension for copy-move |
| `COPY_MOVE_MAX_SAMPLES` | 500 | Max blocks to compare |
| `TECHNIQUE_WEIGHTS` | varies | Weight per technique (must sum to 1.0) |
| `MAX_CONTENT_LENGTH` | 16 MB | Maximum upload file size |

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | 3.1.0 | Web framework |
| Pillow | 11.1.0 | Image processing and EXIF extraction |
| NumPy | 2.2.4 | Numerical operations, array processing |
| Werkzeug | 3.1.3 | WSGI utilities, secure file handling |

No machine learning frameworks, no pre-trained models, no GPU required.

---

## Technical Design Decisions

1. **No ML dependency**: All detection relies on well-understood image forensics algorithms. This demonstrates algorithmic understanding and keeps installation simple with only 4 dependencies.

2. **Multi-technique ensemble**: No single technique catches all forgeries. Using 5 complementary approaches reduces false positives and increases detection coverage.

3. **Weighted scoring**: Techniques that detect more reliable indicators (ELA, metadata) receive higher weights. The weighted average produces a single interpretable score.

4. **Block-based spatial analysis**: Dividing images into grids enables localized detection — the system identifies *where* anomalies occur, not just *that* they occur.

5. **Modular architecture**: Each analyzer is a self-contained module with a consistent interface (`run_*` function returning score/findings/details). New techniques can be added without modifying existing code.

6. **Centralized configuration**: All thresholds and weights live in `config.py`, making the system tunable without touching analysis code.

---

## Limitations & Future Improvements

- **No PRNU analysis**: True camera fingerprint matching would require a reference image from the same camera for comparison
- **No ML classifiers**: A trained SVM or random forest on the extracted features could improve accuracy and calibration
- **Limited copy-move**: Block-based approach may miss rotations or scalings of copied regions
- **No OCR integration**: Text-level analysis (font consistency, character spacing) could detect text replacement forgeries
- **Single image only**: No comparison against known-good templates of the same document type
- **No batch processing**: Currently handles one image at a time; a queue-based system could handle bulk uploads
