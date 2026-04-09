"""Engine — orchestrates all analyzers and builds the final report."""

import time
from .ela_analyzer import run_ela
from .metadata_analyzer import run_metadata_analysis
from .noise_analyzer import run_noise_analysis
from .edge_analyzer import run_edge_analysis
from .copy_move_analyzer import run_copy_move_analysis
from report.generator import generate_report


def run_analysis(image_path, analysis_id=''):
    """
    Run all forgery detection techniques and return a unified report.

    Returns: complete report dict with scores, findings, risk level.
    """
    start_time = time.time()

    # Run all analyzers
    ela_result = run_ela(image_path, analysis_id)
    metadata_result = run_metadata_analysis(image_path)
    noise_result = run_noise_analysis(image_path)
    edge_result = run_edge_analysis(image_path)
    copy_move_result = run_copy_move_analysis(image_path)

    # Collect technique results
    technique_results = {
        'ela': ela_result,
        'metadata': metadata_result,
        'noise': noise_result,
        'edge': edge_result,
        'copy_move': copy_move_result,
    }

    # Generate weighted report
    report = generate_report(technique_results)
    report['analysis_id'] = analysis_id
    report['image_path'] = image_path
    report['processing_time'] = round(time.time() - start_time, 2)

    return report
