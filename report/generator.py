"""Report Generator — computes weighted scoring and assembles the final risk report."""

import json
import os
import time
import config


def generate_report(technique_results):
    """
    Compute weighted scores and generate a unified risk report.

    Args:
        technique_results: dict mapping technique name to its result dict

    Returns: complete report dict with overall score, risk level, per-technique breakdown
    """
    weighted_sum = 0.0
    weight_total = 0.0
    breakdown = {}

    for technique, weight in config.TECHNIQUE_WEIGHTS.items():
        result = technique_results.get(technique, {})
        score = result.get('score', 0.0)
        weighted_sum += score * weight
        weight_total += weight

        breakdown[technique] = {
            'score': score,
            'weight': weight,
            'weighted_score': round(score * weight, 4),
            'findings': result.get('findings', []),
            'details': result.get('details', {}),
        }

        # Include visualization path if available (ELA)
        if 'visualization_path' in result:
            breakdown[technique]['visualization_path'] = result['visualization_path']

    overall_score = weighted_sum / weight_total if weight_total > 0 else 0.0

    # Determine risk level
    risk_level = 'LOW'
    risk_description = ''
    for low, high, level, desc in config.RISK_THRESHOLDS:
        if low <= overall_score < high:
            risk_level = level
            risk_description = desc
            break

    # Collect all findings
    all_findings = []
    for technique, data in breakdown.items():
        for finding in data['findings']:
            all_findings.append({
                'technique': technique.replace('_', ' ').title(),
                'finding': finding,
                'score': data['score'],
            })

    # Sort findings by score (most suspicious first)
    all_findings.sort(key=lambda f: f['score'], reverse=True)

    report = {
        'overall_score': round(overall_score, 4),
        'risk_level': risk_level,
        'risk_description': risk_description,
        'breakdown': breakdown,
        'findings': all_findings,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    # Save report to JSON
    _save_report_json(report)

    return report


def _save_report_json(report):
    """Save report as JSON to output directory."""
    os.makedirs(config.OUTPUT_FOLDER, exist_ok=True)
    analysis_id = report.get('analysis_id', str(int(time.time())))
    filepath = os.path.join(config.OUTPUT_FOLDER, f'report_{analysis_id}.json')
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2)
