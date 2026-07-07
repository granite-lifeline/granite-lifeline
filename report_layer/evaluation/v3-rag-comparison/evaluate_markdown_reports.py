#!/usr/bin/env python3
"""
Evaluate diagnostic reports from markdown comparison files.

This script extracts report sections from scenario comparison markdown files
and evaluates them using the report_quality_evaluator module.
"""

import re
import sys
from pathlib import Path

# Add parent directory to path to import evaluator
sys.path.insert(0, str(Path(__file__).parent.parent))

from report_quality_evaluator import (
    evaluate_report,
    ReportQualityScore,
    write_quality_report
)


def extract_reports_from_markdown(md_path: Path) -> list:
    """
    Extract report sections from a markdown file.
    
    Returns list of dicts with:
    - scenario_name
    - risk_level
    - context (input summary)
    - report (dict with anomaly_description, possible_cause, recommended_action)
    """
    with open(md_path, 'r') as f:
        content = f.read()
    
    reports = []
    
    # Find all scenario sections
    scenario_pattern = r'### (\w+)\s*\n\n\*\*Description:\*\*.*?\n\n\*\*Input Summary:\*\*\s*\n\n(.*?)\n\n#### Anomaly Description\s*\n\n(.*?)\n\n#### Possible Cause\s*\n\n(.*?)\n\n#### Recommended Action\s*\n\n(.*?)(?=\n---|\Z)'
    
    matches = re.finditer(scenario_pattern, content, re.DOTALL)
    
    for match in matches:
        scenario_name = match.group(1)
        input_summary = match.group(2)
        anomaly_desc = match.group(3).strip()
        possible_cause = match.group(4).strip()
        recommended_action = match.group(5).strip()
        
        # Extract risk level from input summary
        risk_match = re.search(r'Risk Level:\s*(\w+)', input_summary)
        risk_level = risk_match.group(1) if risk_match else "Unknown"
        
        # Parse recommended actions (handle both list and paragraph formats)
        actions = []
        
        # Try to find numbered items with format "- 1." or just "1."
        numbered_pattern = r'(?:^|\n)\s*-?\s*\d+\.?\s*\*?\*?(.+?)(?=\n\s*-?\s*\d+\.|\n\n|\Z)'
        action_items = re.findall(numbered_pattern, recommended_action, re.DOTALL)
        
        if action_items:
            # Clean up each action item
            actions = []
            for item in action_items:
                # Remove markdown bold markers and extra whitespace
                cleaned = re.sub(r'\*\*(.+?)\*\*:?', r'\1:', item)
                cleaned = ' '.join(cleaned.split())
                actions.append(cleaned.strip())
        else:
            # Fall back to bullet points format
            lines = [line.strip() for line in recommended_action.split('\n') if line.strip()]
            actions = [line.lstrip('- ').strip() for line in lines if line.startswith('-')]
        
        # If still no actions, treat whole text as single action
        if not actions:
            actions = [recommended_action]
        
        report = {
            "scenario_name": scenario_name,
            "risk_level": risk_level,
            "context": input_summary,
            "report": {
                "anomaly_description": anomaly_desc,
                "possible_cause": possible_cause,
                "recommended_action": actions
            }
        }
        
        reports.append(report)
    
    return reports


def main():
    """Main evaluation function."""
    eval_dir = Path(__file__).parent
    
    # Files to evaluate
    baseline_path = eval_dir / "scenario_comparison_baseline.md"
    rag_path = eval_dir / "scenario_comparison_rag.md"
    
    print("=" * 70)
    print("Report Quality Evaluation - V3 RAG Comparison")
    print("=" * 70)
    print()
    
    # Evaluate baseline reports
    print("Evaluating BASELINE reports...")
    baseline_reports = extract_reports_from_markdown(baseline_path)
    baseline_scores = []
    
    for report_data in baseline_reports:
        score = evaluate_report(
            report=report_data["report"],
            context=report_data["context"],
            anomaly_type=report_data["scenario_name"],
            risk_level=report_data["risk_level"]
        )
        baseline_scores.append(score)
        print(f"  ✓ {report_data['scenario_name']}: {score.overall_score:.2f}")
    
    print()
    
    # Evaluate RAG reports
    print("Evaluating RAG-ENHANCED reports...")
    rag_reports = extract_reports_from_markdown(rag_path)
    rag_scores = []
    
    for report_data in rag_reports:
        score = evaluate_report(
            report=report_data["report"],
            context=report_data["context"],
            anomaly_type=report_data["scenario_name"],
            risk_level=report_data["risk_level"]
        )
        rag_scores.append(score)
        print(f"  ✓ {report_data['scenario_name']}: {score.overall_score:.2f}")
    
    print()
    print("=" * 70)
    
    # Write detailed reports
    baseline_output = eval_dir / "quality_scores_baseline.md"
    rag_output = eval_dir / "quality_scores_rag.md"
    
    write_quality_report(baseline_scores, baseline_output)
    write_quality_report(rag_scores, rag_output)
    
    print(f"\n✓ Baseline quality report: {baseline_output}")
    print(f"✓ RAG quality report: {rag_output}")
    
    # Print comparison summary
    print("\n" + "=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Scenario':<30} {'Baseline':<12} {'RAG':<12} {'Improvement':<12}")
    print("-" * 70)
    
    for baseline, rag in zip(baseline_scores, rag_scores):
        improvement = rag.overall_score - baseline.overall_score
        improvement_str = f"{improvement:+.2f}"
        print(f"{baseline.anomaly_type:<30} {baseline.overall_score:<12.2f} {rag.overall_score:<12.2f} {improvement_str:<12}")
    
    # Calculate averages
    baseline_avg = sum(s.overall_score for s in baseline_scores) / len(baseline_scores)
    rag_avg = sum(s.overall_score for s in rag_scores) / len(rag_scores)
    avg_improvement = rag_avg - baseline_avg
    
    print("-" * 70)
    print(f"{'AVERAGE':<30} {baseline_avg:<12.2f} {rag_avg:<12.2f} {avg_improvement:+.2f}")
    print()


if __name__ == "__main__":
    main()
