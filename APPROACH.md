# Approach — ID Document Forgery Detection

## Problem Statement

The task is to build a system that detects digital manipulation in ID document images (passports, national ID cards, driver's licenses) and produces an interpretable risk assessment. The system must analyze uploaded images and determine whether they show signs of having been digitally forged or tampered with.

### Key Constraints

- **Purely algorithmic**: No pre-trained machine learning models — all detection must be implemented from scratch using image processing algorithms
- **Interpretable results**: The system must explain *why* an image is flagged, not just produce a binary score
- **Practical deployment**: Must be a working web application that a reviewer can interact with

---

## My Approach

### Design Philosophy

I approached this as a **multi-technique ensemble** problem. No single algorithm can reliably detect all types of digital forgery. Each forgery technique leaves different artifacts in an image, and different detection methods are needed to find each type of artifact. By combining multiple techniques with weighted scoring, the system achieves broader detection coverage and more reliable results than any single method alone.

The core design decisions:

1. **No ML dependency** — All detection uses well-understood image forensics algorithms implemented with Pillow and NumPy. This demonstrates algorithmic understanding and keeps the project lightweight with only 4 dependencies.

2. **5 complementary techniques** — Each targets a different type of forgery artifact. Together they cover the most common manipulation methods.

3. **Weighted scoring** — Techniques that detect more reliable indicators receive higher weights. ELA (most reliable for localized edits) gets 0.30, while copy-move (narrower scope) gets 0.15.

4. **Block-based spatial analysis** — Dividing images into grids enables localized anomaly detection. The system identifies *where* in the image anomalies occur, not just *that* they exist.

5. **Modular architecture** — Each detection technique is a self-contained module with a consistent interface, making the system extensible.

---

## Technique Selection Rationale

### Why These 5 Techniques?

I selected these techniques because they each target a fundamentally different type of forgery artifact, providing complementary coverage:

| Forgery Artifact | Detection Technique | Example Forgery |
|-----------------|---------------------|-----------------|
| Inconsistent JPEG compression | Error Level Analysis (ELA) | Clone stamping, text overlay |
| Metadata manipulation/stripping | Metadata Analysis | Editing software use, screenshot |
| Mixed sensor noise patterns | Noise Pattern Analysis | Splicing regions from different sources |
| Unnatural edge transitions | Edge Analysis | Splice boundaries between composited regions |
| Duplicated image regions | Copy-Move Detection | Copying seals, stamps, or text |

### What I Considered But Did Not Implement

- **PRNU camera fingerprint matching**: Requires a reference image from the same camera — not practical for document analysis where we have no reference.
- **DCT coefficient analysis**: More specialized version of ELA; ELA provides sufficient coverage for JPEG artifacts.
- **Deep learning (CNN-based)**: Would require training data and GPU resources, contradicting the "no ML" constraint.
- **JPEG ghost detection**: Only applicable to JPEG images with specific quality differences; too narrow.

---

## Detailed Technique Implementation

### 1. Error Level Analysis (ELA) — Weight: 0.30

**The Science:**
JPEG compression works by dividing an image into 8x8 blocks and applying a Discrete Cosine Transform (DCT) to each block. When an image is re-saved as JPEG, every block undergoes the same quantization process. If a region was previously edited (and saved at a different quality level or format), it will produce a different error magnitude when re-compressed. Edited regions "stand out" because their compression error differs from the surrounding untouched areas.

**My Implementation:**
```
Original Image → Re-save at JPEG quality 85 → Compute pixel-wise |diff| × 15
     → Divide into 32×32 grid → Per-block mean error → Flag blocks > mean + 1.5σ
```

- **Re-compression at quality 85**: High enough to preserve subtle differences, low enough to create measurable error
- **15x amplification**: Makes differences visible in the heatmap
- **32x32 grid blocks**: Larger than JPEG's 8x8 DCT blocks, averaging out block-boundary noise
- **1.5σ threshold**: Statistically significant deviation (roughly 87th percentile for normal distributions)

**Scoring:**
- `variance_score` (50%): How much error levels vary across blocks (normalized to max 40)
- `anomaly_score` (50%): What fraction of blocks exceed the threshold (normalized to max 0.3)

**Why highest weight (0.30):** ELA is one of the most widely validated techniques in image forensics. It directly detects the most common types of localized editing — clone stamping, healing brush, text overlay, and copy-paste operations. It produces both a numeric score and a visual heatmap that a human can interpret.

**Limitations:** Only works well on JPEG images. PNG-to-PNG re-compression shows no loss. Very high quality JPEGs (>95) may show minimal differences. An attacker who re-compresses the entire image at the same quality can reduce ELA effectiveness.

---

### 2. Metadata / EXIF Analysis — Weight: 0.20

**The Science:**
Digital cameras embed rich metadata in image files — EXIF tags that record camera model, lens, exposure settings, timestamps, GPS coordinates, and more. When an image is edited in software like Photoshop, this metadata is often modified or stripped. Key indicators include:

- **Software tag**: Directly records the editing application used
- **Date mismatches**: DateTime (file save time) vs DateTimeOriginal (capture time) should be consistent
- **Missing metadata**: Camera-captured images almost always contain EXIF; its absence is suspicious for a "photographed document"
- **Format anomalies**: PNG files without EXIF suggest screenshots or exports from editing tools

**My Implementation:**
```python
# Scoring breakdown:
# +0.35  Editing software detected in EXIF (Photoshop, GIMP, etc.)
# +0.25  No EXIF data at all (suspicious for camera-captured documents)
# +0.20  DateTime != DateTimeOriginal (re-saved after original capture)
# +0.15  MakerNote references editing software
# +0.10  Original != Digitized dates
# +0.10  PNG without EXIF (screenshot or edited export)
# +0.10  BMP format (unusual for documents)
# +0.10  Resolution < 200px (likely digitally created)
```

**Why moderate weight (0.20):** Metadata is a strong signal but has important caveats:
- Legitimate users may strip metadata for privacy
- Forged metadata can be planted
- Social media platforms strip EXIF automatically
- Screenshots of genuine documents have no EXIF

The score is additive (capped at 1.0), meaning multiple independent signals compound the suspicion.

---

### 3. Noise Pattern Analysis — Weight: 0.20

**The Science:**
Every camera sensor produces a unique noise pattern called Photo Response Non-Uniformity (PRNU). This noise acts like a fingerprint — images from the same camera share consistent noise characteristics. When regions from different images are spliced together, the noise patterns don't match, creating detectable inconsistencies.

Even without a reference camera fingerprint, we can detect splicing by checking whether noise levels are consistent across the image. A genuine photograph has uniform noise; a spliced image has regions with different noise characteristics.

**My Implementation:**
```
Image → Grayscale → Median filter (5×5) → Noise residual = original − denoised
     → 64×64 blocks → Per-block noise std → Two signals:
       1. Spatial asymmetry (left vs right, top vs bottom)
       2. Outlier blocks (MAD-based robust detection)
```

**Signal 1 — Spatial Asymmetry (60% of noise score):**
- Compare mean noise std between left/right halves and top/bottom halves
- Genuine images may have some asymmetry (text regions vs photo regions on IDs)
- Threshold set generously (2.5) to avoid false positives from document layout
- Normalized ratio: `max(LR_diff, TB_diff) / overall_mean`

**Signal 2 — Outlier Detection (40% of noise score):**
- Uses Median Absolute Deviation (MAD) — more robust than mean/std for outlier detection
- Threshold: `median + 3.5 × (MAD × 1.4826)` — the 1.4826 factor makes MAD comparable to standard deviation for normal distributions
- Outlier ratio normalized to max 0.3

**Why moderate weight (0.20):** Effective for detecting splicing from different sources, but document images naturally have varying noise levels (printed text vs photograph vs background), which can create false positives. The generous thresholds mitigate this.

---

### 4. Edge Analysis — Weight: 0.15

**The Science:**
When two image regions from different sources are composited together (splicing), the boundary between them often has unnatural edge characteristics. Even if the splice is blended, the transition region typically shows:
- Abnormally high edge density (sharp transition)
- Edges that don't align with natural image structure
- Clusters of edge outliers forming lines (splice boundaries) rather than random points

**My Implementation:**
```
Image → Grayscale → Horizontal gradient (|pixel[x] − pixel[x−1]|)
                  → Vertical gradient (|pixel[y] − pixel[y−1]|)
                  → Edge magnitude = √(grad_x² + grad_y²)
     → 32×32 blocks → Per-block edge density → Flag blocks > mean + 2σ
```

**Scoring:**
- `outlier_score` (60%): Fraction of blocks with edge density > 2σ above mean
- `variance_score` (40%): Standard deviation of edge densities across all blocks

**Why lower weight (0.15):** ID documents are text-heavy with many natural edges (text, borders, photos, holograms). This makes edge analysis prone to false positives on legitimate documents. The lower weight reflects this reduced discriminative power for the specific domain of ID documents.

---

### 5. Copy-Move Detection — Weight: 0.15

**The Science:**
Copy-move forgery involves copying a region of an image and pasting it elsewhere — for example, copying an official stamp or seal to cover an altered area, or duplicating a pattern to hide something. The copied region has identical content to the source but is spatially displaced.

**My Implementation:**
```
Image → Grayscale → Resize if >512px → 16×16 overlapping blocks (step 8)
     → Skip uniform blocks (std < 5) → Extract 18-D feature vector per block:
       - 8 row mean samples (interpolated to fixed length)
       - 8 column mean samples
       - 2 gradient values (horizontal + vertical)
     → Z-score normalize features → Pairwise Euclidean distance
     → Match if distance < 0.8 AND spatial distance > 50px
     → Spatial coherence check: cluster match offsets into buckets
     → Score = 30% match_ratio + 70% coherence
```

**Key design choices:**

1. **Uniform block skipping**: Background regions (std < 5) produce identical features and create false matches. Skipping them dramatically improves precision.

2. **Feature vector design**: Row/column mean profiles capture the internal structure of each block. Interpolation to 8 features ensures fixed-length vectors regardless of block content. Gradient features add directional information.

3. **Z-score normalization**: Normalizes features across all blocks so that a single high-magnitude feature doesn't dominate the distance calculation.

4. **Spatial coherence**: The most important innovation. Genuine images can produce incidental block matches (repeating textures, text). True copy-move forgeries produce many matches with the *same translation vector* (offset). By clustering match offsets into buckets (rounded to 2× block_size multiples), we can distinguish coherent copy-move from random texture similarity.

5. **Performance safeguards**: Max 500 blocks sampled, max 100 matches tracked, images resized to 512px. This keeps runtime reasonable for web requests.

**Why lowest weight (0.15):** Copy-move is a specific forgery technique. Many forgeries use content from *external* sources (different images) rather than copying within the same image. The technique is valuable but has narrower scope.

---

## Scoring System Design

### Weighted Average

```
overall_score = Σ(technique_score × technique_weight) / Σ(weights)
             = (0.30 × ela + 0.20 × metadata + 0.20 × noise + 0.15 × edge + 0.15 × copy_move) / 1.0
```

The weights were chosen based on:
- **Reliability**: How often the technique correctly identifies manipulation
- **False positive rate**: How often it flags genuine images
- **Scope**: How many different forgery types it can detect
- **Domain suitability**: How well it works on ID documents specifically

### Risk Level Thresholds

| Range | Level | Rationale |
|-------|-------|-----------|
| 0.0–0.2 | LOW | All techniques report low suspicion — image appears genuine |
| 0.2–0.4 | LOW-MODERATE | Minor anomalies detected — common for real-world scans/photos |
| 0.4–0.6 | MODERATE | Enough signals to warrant manual review by a human |
| 0.6–0.8 | HIGH | Multiple techniques flag significant issues — likely manipulated |
| 0.8–1.0 | CRITICAL | Strong consensus across techniques — high confidence of forgery |

The 0.2 increments provide fine-grained assessment while keeping the levels interpretable.

### Why Not a Binary Classifier

A binary genuine/forgery classifier would lose important nuance:
- Some anomalies are innocuous (metadata stripped by social media)
- Some forgeries are subtle (sophisticated splicing)
- The risk level gives reviewers a prioritization framework
- The detailed findings explain *what* was detected, enabling informed decisions

---

## Architecture Decisions

### Why Flask

- Lightweight, minimal boilerplate
- Perfect for a single-purpose tool
- Built-in development server sufficient for demonstration
- Easy deployment to Render, Heroku, PythonAnywhere

### Why No Database

The analysis is stateless — each upload is processed independently. Results are saved as JSON files for simplicity. A production system would use a database (PostgreSQL with the analysis results), but for this assignment, JSON files are appropriate and keep the dependency count at 4.

### Why No Async Processing

Image analysis completes in 1-5 seconds for typical ID document sizes (<16MB). This is fast enough for synchronous processing. A production system handling bulk uploads would use a task queue (Celery + Redis), but that's unnecessary overhead for this scope.

### Template Inheritance

Jinja2's template inheritance (`base.html` → `index.html` / `report.html`) keeps the UI consistent and avoids code duplication. The base template provides navigation and footer; child templates fill in the content.

---

## Testing Strategy

### Sample Image Generator

The `create_samples.py` script generates controlled test cases:

| Test Image | Expected Outcome | Why |
|-----------|-----------------|-----|
| `genuine_1.jpg` | LOW | Uniform noise (std=3), consistent JPEG quality (92) |
| `genuine_2.jpg` | LOW to LOW-MODERATE | Uniform noise (std=4), slightly lower quality (88) |
| `tampered_copy_move.jpg` | MODERATE to HIGH | Region duplicated — should trigger copy-move detection |
| `tampered_noise_splice.jpg` | MODERATE to HIGH | Left (noise=2) spliced with right (noise=12) — should trigger noise analysis |
| `tampered_double_compress.jpg` | MODERATE to HIGH | Quality 50 → edit → quality 92 — should trigger ELA |

### Validation Approach

1. **Unit validation**: Each analyzer tested independently with known-manipulated images
2. **Boundary testing**: Very small images, very large images, non-JPEG formats
3. **False positive testing**: Genuine images should consistently score LOW
4. **End-to-end testing**: Full upload → analysis → report flow verified

---

## Performance Considerations

- **ELA**: O(n) where n = pixel count. Very fast (<1s for typical images).
- **Metadata**: O(1) — reads EXIF tags, constant time regardless of image size.
- **Noise Analysis**: O(n) for median filter + O(blocks) for analysis.
- **Edge Analysis**: O(n) for gradient computation + O(blocks) for analysis.
- **Copy-Move**: O(blocks²) worst case, but limited to 500 blocks and 100 matches. Resizing to 512px keeps blocks manageable.

For a typical 1000×600 ID document image, total analysis time is 1-5 seconds.

---

## Limitations & Honest Assessment

### What This System Does Well
- Detects obvious forgeries (copy-paste, double compression, inconsistent noise)
- Provides interpretable, evidence-based results
- Works with zero training data
- Runs efficiently on any hardware

### What It Does NOT Do
- **Cannot detect perfect forgeries**: A skilled forger who re-compresses at matching quality, adds consistent noise, and avoids metadata issues may evade detection
- **Cannot identify *what* was changed**: It detects manipulation artifacts but cannot tell you "the name was changed from X to Y"
- **Not calibrated on real data**: The thresholds are based on forensic literature and empirical tuning with test images, not a large labeled dataset
- **No document-type awareness**: Doesn't know the difference between a passport and a driver's license — doesn't check for expected fields, hologram placement, etc.

### What I Would Add With More Time

1. **DCT coefficient analysis**: Statistical analysis of JPEG DCT coefficients for more precise ELA
2. **CFA interpolation detection**: Check Color Filter Array patterns for splicing artifacts
3. **ML ensemble classifier**: Train a logistic regression or SVM on the 5 technique scores + feature details to learn optimal combination weights
4. **OCR + text analysis**: Use Tesseract to extract text and check for font inconsistencies
5. **Template matching**: Compare against known-good document templates
6. **Batch processing API**: REST API endpoint for programmatic bulk analysis

---

## File-by-File Walkthrough

### Core Application
- **`app.py`** (53 lines): Two routes — `index()` handles GET (upload form) and POST (file upload + redirect to report), `report()` runs analysis and renders results. File validation, UUID naming, and secure filename handling.
- **`config.py`** (47 lines): All tunable parameters in one place. ELA quality/scale, block sizes, weights, risk thresholds.

### Analysis Pipeline
- **`analyzer/engine.py`** (43 lines): Orchestrator. Runs all 5 analyzers sequentially, collects results, delegates to report generator, adds timing metadata.
- **`analyzer/ela_analyzer.py`** (96 lines): ELA implementation. Re-compresses, computes diff, grid analysis, heatmap generation.
- **`analyzer/metadata_analyzer.py`** (122 lines): EXIF extraction, 6 distinct checks with additive scoring.
- **`analyzer/noise_analyzer.py`** (115 lines): Median filter denoising, spatial asymmetry, MAD-based outlier detection.
- **`analyzer/edge_analyzer.py`** (88 lines): Gradient computation, edge density analysis, outlier detection.
- **`analyzer/copy_move_analyzer.py`** (193 lines): Block feature extraction, pairwise matching, spatial coherence scoring.
- **`analyzer/utils.py`** (35 lines): Shared helpers — grid splitting, score normalization, visualization saving.

### Report Generation
- **`report/generator.py`** (86 lines): Computes weighted scores, determines risk level, collects and sorts findings, saves JSON.

### User Interface
- **`templates/base.html`** (25 lines): Base layout with nav bar, footer, and CSS/JS includes.
- **`templates/index.html`** (54 lines): Upload form with drag & drop zone, file preview, and info cards.
- **`templates/report.html`** (81 lines): Risk summary ring, technique breakdown bars, image comparison, findings list, raw JSON.
- **`static/css/style.css`** (409 lines): Responsive design with mobile/tablet breakpoints, risk-based color coding.
- **`static/js/main.js`** (84 lines): Drag & drop handling, file preview, score bar and risk ring coloring.

### Utilities
- **`create_samples.py`** (147 lines): Generates 5 test images (2 genuine, 3 tampered) with controlled forgery techniques.

---

## Conclusion

This project demonstrates that effective document forgery detection can be achieved with well-understood algorithmic techniques, without relying on machine learning. The multi-technique ensemble approach provides broad coverage of common forgery methods, while the weighted scoring system produces interpretable results that help human reviewers make informed decisions.

The modular architecture makes it straightforward to extend — adding a new detection technique requires only implementing a `run_*` function that returns a score/findings/details dict and registering it in `engine.py` and `config.py`.
