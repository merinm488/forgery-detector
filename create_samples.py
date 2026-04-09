"""Generate sample test images: genuine and tampered ID documents for testing."""

from PIL import Image, ImageDraw, ImageFont
import os
import random

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'samples')
GENUINE_DIR = os.path.join(SAMPLES_DIR, 'genuine')
TAMPERED_DIR = os.path.join(SAMPLES_DIR, 'tampered')


def _create_id_card(name, dob, id_number, nationality, extra_text=None):
    """Create a simple ID card image."""
    w, h = 600, 380
    img = Image.new('RGB', (w, h), '#ffffff')
    draw = ImageDraw.Draw(img)

    # Card border
    draw.rectangle([5, 5, w - 5, h - 5], outline='#1a237e', width=3)
    draw.rectangle([10, 10, w - 10, 50], fill='#1a237e')
    draw.text((20, 18), 'NATIONAL IDENTITY CARD', fill='white')
    draw.line([10, 55, w - 10, 55], fill='#1a237e', width=2)

    # Photo placeholder
    draw.rectangle([20, 70, 130, 180], outline='#cccccc', width=1)
    draw.text((40, 110), 'PHOTO', fill='#cccccc')

    # Details
    y = 75
    fields = [
        ('Name:', name),
        ('Date of Birth:', dob),
        ('ID Number:', id_number),
        ('Nationality:', nationality),
    ]
    for label, value in fields:
        draw.text((150, y), label, fill='#666666')
        draw.text((280, y), value, fill='#000000')
        y += 28

    if extra_text:
        draw.text((20, y + 10), extra_text, fill='#999999')

    # Bottom bar
    draw.rectangle([10, h - 40, w - 10, h - 10], fill='#e8eaf6')
    draw.text((20, h - 35), 'Sample document for forgery detection testing', fill='#666666')

    return img


def create_genuine_samples():
    """Create genuine-looking ID card samples."""
    os.makedirs(GENUINE_DIR, exist_ok=True)

    # Genuine sample 1
    img = _create_id_card(
        'John A. Smith',
        '15 March 1990',
        'ID-2024-001234',
        'United Kingdom',
    )
    # Add subtle noise (natural for scanned/photographed documents)
    import numpy as np
    arr = np.array(img, dtype=np.float64)
    noise = np.random.normal(0, 3, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    img.save(os.path.join(GENUINE_DIR, 'genuine_1.jpg'), quality=92)
    print('Created genuine_1.jpg')

    # Genuine sample 2
    img = _create_id_card(
        'Maria Garcia Lopez',
        '22 July 1985',
        'ID-2024-005678',
        'Spain',
    )
    arr = np.array(img, dtype=np.float64)
    noise = np.random.normal(0, 4, arr.shape)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    img.save(os.path.join(GENUINE_DIR, 'genuine_2.jpg'), quality=88)
    print('Created genuine_2.jpg')


def create_tampered_samples():
    """Create tampered ID card samples with various forgeries."""
    os.makedirs(TAMPERED_DIR, exist_ok=True)
    import numpy as np

    # Tampered sample 1: Name changed (text splicing)
    img = _create_id_card(
        'John B. Smith',  # Changed middle initial
        '15 March 1990',
        'ID-2024-001234',
        'United Kingdom',
    )
    # Copy a region and paste it elsewhere (copy-move forgery)
    arr = np.array(img)
    # Copy the bottom bar region to another location
    copied = arr[340:370, 10:590].copy()
    arr[60:90, 10:590] = copied
    img = Image.fromarray(arr)
    img.save(os.path.join(TAMPERED_DIR, 'tampered_copy_move.jpg'), quality=92)
    print('Created tampered_copy_move.jpg')

    # Tampered sample 2: Heavy noise manipulation (splicing from different source)
    img = _create_id_card(
        'Ahmed Hassan Al-Rashid',
        '01 January 1988',
        'ID-2024-009999',
        'Jordan',
    )
    arr = np.array(img, dtype=np.float64)
    # Add noise to only half the image (simulating splicing)
    noise_left = np.random.normal(0, 2, (arr.shape[0], arr.shape[1] // 2, 3))
    noise_right = np.random.normal(0, 12, (arr.shape[0], arr.shape[1] - arr.shape[1] // 2, 3))
    noise = np.hstack([noise_left, noise_right])
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    img.save(os.path.join(TAMPERED_DIR, 'tampered_noise_splice.jpg'), quality=92)
    print('Created tampered_noise_splice.jpg')

    # Tampered sample 3: Double-compressed (JPEG artifact)
    img = _create_id_card(
        'Sarah Johnson',
        '14 February 1995',
        'ID-2024-007777',
        'Canada',
    )
    # Save at low quality, reopen, edit, save again (double compression)
    import io
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=50)
    buf.seek(0)
    img = Image.open(buf)
    draw = ImageDraw.Draw(img)
    draw.text((280, 103), 'Williams', fill='#000000')  # Overwrite name
    img.save(os.path.join(TAMPERED_DIR, 'tampered_double_compress.jpg'), quality=92)
    print('Created tampered_double_compress.jpg')


if __name__ == '__main__':
    random.seed(42)
    create_genuine_samples()
    create_tampered_samples()
    print('\nSample images created in samples/genuine/ and samples/tampered/')
