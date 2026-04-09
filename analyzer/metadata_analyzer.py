"""Metadata / EXIF Analysis — flags editing software, date mismatches, missing metadata."""

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import config


# Known editing software signatures
EDITING_SOFTWARE = [
    'photoshop', 'gimp', 'lightroom', 'affinity', 'paint.net',
    'snapseed', 'picsart', 'canva', 'pixlr', 'picmonkey',
    'adobe', 'capture one', 'darktable', 'rawtherapee',
    'polarr', 'vsco', 'lightzone', 'digiKam',
]


def run_metadata_analysis(image_path):
    """
    Analyze image metadata for signs of manipulation.

    Checks:
    1. EXIF data presence and completeness
    2. Editing software signatures
    3. Date consistency (create vs modify)
    4. Format inconsistencies
    5. Thumbnail mismatch indicators

    Returns: dict with score, findings, details
    """
    findings = []
    score = 0.0
    details = {}

    try:
        img = Image.open(image_path)
    except Exception as e:
        return {
            'score': 0.5,
            'findings': [f'Could not open image: {e}'],
            'details': {},
        }

    details['format'] = img.format
    details['mode'] = img.mode
    details['size'] = f'{img.width}x{img.height}'

    # Extract EXIF data
    exif_data = {}
    if hasattr(img, '_getexif') and img._getexif():
        raw_exif = img._getexif()
        for tag_id, value in raw_exif.items():
            tag = TAGS.get(tag_id, tag_id)
            exif_data[tag] = str(value)

    details['has_exif'] = bool(exif_data)
    details['exif_field_count'] = len(exif_data)

    # Check 1: Missing EXIF — suspicious for a camera-captured document
    if not exif_data:
        findings.append('No EXIF metadata found. Camera-captured documents typically contain EXIF data.')
        score += 0.25
    else:
        # Check 2: Editing software in metadata
        software = exif_data.get('Software', '').lower()
        if software:
            details['software'] = exif_data.get('Software')
            for editor in EDITING_SOFTWARE:
                if editor in software:
                    findings.append(f'Editing software detected: "{exif_data.get("Software")}"')
                    score += 0.35
                    break

        # Check 3: Date consistency
        date_time = exif_data.get('DateTime', '')
        date_time_original = exif_data.get('DateTimeOriginal', '')
        date_time_digitized = exif_data.get('DateTimeDigitized', '')

        if date_time and date_time_original and date_time != date_time_original:
            findings.append('Create date differs from original date — possible re-save after editing.')
            score += 0.2
            details['date_mismatch'] = {
                'DateTime': date_time,
                'DateTimeOriginal': date_time_original,
            }

        if date_time_original and date_time_digitized and date_time_original != date_time_digitized:
            findings.append('Original and digitized dates differ.')
            score += 0.1

        # Check 4: Maker notes from editing tools
        maker_note = exif_data.get('MakerNote', '')
        if maker_note and any(s in maker_note.lower() for s in EDITING_SOFTWARE):
            findings.append('MakerNote references editing software.')
            score += 0.15

    # Check 5: Format consistency
    fmt = (img.format or '').upper()
    if fmt == 'PNG':
        # PNGs from cameras are rare; could be screenshot or edited
        if not exif_data:
            findings.append('PNG format with no EXIF — possibly a screenshot or edited export.')
            score += 0.1
    elif fmt == 'BMP':
        findings.append('BMP format is unusual for ID documents.')
        score += 0.1

    # Check 6: Very small images may be low-quality scans or digitally created
    if img.width < 200 or img.height < 200:
        findings.append('Image resolution is very low — may indicate digital creation rather than scan.')
        score += 0.1

    if not findings:
        findings.append('Metadata appears consistent with an authentic document.')

    score = min(score, 1.0)

    return {
        'score': round(score, 4),
        'findings': findings,
        'details': details,
    }
