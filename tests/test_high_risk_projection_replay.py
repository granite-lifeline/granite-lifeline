"""Replay current High-risk reports through the consistency guard."""

import json
from pathlib import Path

from report_layer.pipeline.prompt_chain_validator import validate_chain


ABLATION_RESULTS = (
    Path(__file__).parents[1]
    / "report_layer"
    / "evaluation"
    / "v5-rag-final-ablation"
    / "final_rag_ablation_raw.json"
)


def test_current_high_risk_reports_avoid_projection_conflicts():
    """Regenerated High-risk fixtures must satisfy the semantic check.

    The saved ablation contains two High-risk anomaly types under four
    retrieval conditions. GL-447 removed future High-threshold projections
    from their prompt context and added the consistency guard.
    """
    records = json.loads(ABLATION_RESULTS.read_text(encoding="utf-8"))
    high_risk_records = [
        record for record in records if record["risk_level"] == "High"
    ]

    assert len(high_risk_records) == 8
    assert {
        record["anomaly_type"] for record in high_risk_records
    } == {
        "intake_air_temperature_sensor_fault",
        "map_load_signal_plausibility_fault",
    }

    for record in high_risk_records:
        report = record["report"]
        results = validate_chain(
            report["anomaly_description"],
            report["possible_cause"],
            report["recommended_action"],
            record["risk_level"],
        )

        assert not any(
            "already High risk" in warning
            for result in results
            for warning in result.warnings
        ), record["condition"]
        assert all(result.score >= 0.8 for result in results)
