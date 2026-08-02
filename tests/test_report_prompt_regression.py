import json
from pathlib import Path


SELECTED_REPORT_DIR = Path(
    "report_layer/evaluation/prompt_refinement/"
    "fault_injection_candidates/selected_window_reports"
)
GOLDEN_SET_PATH = Path(
    "report_layer/evaluation/prompt_refinement/golden_report_set.json"
)

EXPECTED_ANOMALY_TYPES = {
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
    "intake_air_temperature_sensor_fault",
    "map_load_signal_plausibility_fault",
}

FORBIDDEN_OWNER_FACING_TERMS = [
    "proxy_decisions.csv",
    "P0113",
    "P0106",
    "DTC",
    "e.g.",
    "i.e.",
    "this window",
    "near future",
    "could fail soon",
    "likely to fail soon",
    "**",
]

NORMAL_CONTRADICTIONS = [
    "outside its normal range",
    "outside their normal ranges",
    "outside the normal range",
    "reading is abnormal",
    "readings are abnormal",
]

ABNORMAL_CONTRADICTIONS = [
    "current readings still look normal",
    "all current readings are normal",
    "all monitored signals are normal",
    "all related key signals are within their normal ranges",
]


def _load_selected_reports():
    manifest = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    reports = []
    for case in manifest["cases"]:
        report_path = Path(case["report_path"])
        report = json.loads(report_path.read_text(encoding="utf-8"))
        report["_golden_case"] = case
        reports.append(report)
    return reports


def _owner_facing_text(report):
    return "\n".join([
        "\n".join(str(note) for note in report.get("notes") or []),
        str(report.get("anomaly_description") or ""),
        str(report.get("possible_cause") or ""),
        "\n".join(report.get("recommended_action") or []),
    ])


def _has_abnormal_key_signal(report):
    for signal in report.get("key_signals") or []:
        lower, upper = signal["reference_range"]
        if signal["value"] < lower or signal["value"] > upper:
            return True
    return False


def test_selected_reports_cover_five_anomaly_types():
    reports = _load_selected_reports()

    assert {report["component"] for report in reports} == (
        EXPECTED_ANOMALY_TYPES
    )
    assert len(reports) == 5


def test_golden_report_manifest_points_to_existing_case_files():
    manifest = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))

    assert {case["anomaly_type"] for case in manifest["cases"]} == (
        EXPECTED_ANOMALY_TYPES
    )
    for case in manifest["cases"]:
        assert Path(case["model_input_path"]).exists()
        assert Path(case["report_path"]).exists()


def test_selected_reports_do_not_expose_owner_facing_artifacts():
    for report in _load_selected_reports():
        text = _owner_facing_text(report)

        for forbidden in FORBIDDEN_OWNER_FACING_TERMS:
            assert forbidden not in text, (
                f"{report['component']} exposes {forbidden!r}"
            )


def test_selected_reports_do_not_contradict_signal_status():
    for report in _load_selected_reports():
        text = _owner_facing_text(report).lower()

        if _has_abnormal_key_signal(report):
            for phrase in ABNORMAL_CONTRADICTIONS:
                assert phrase not in text, (
                    f"{report['component']} says readings are normal "
                    f"despite abnormal key signals"
                )
        else:
            for phrase in NORMAL_CONTRADICTIONS:
                assert phrase not in text, (
                    f"{report['component']} says readings are abnormal "
                    f"despite normal key signals"
                )


def test_low_projection_reports_do_not_claim_likely_immediate_failure():
    for report in _load_selected_reports():
        probability = report.get("estimated_failure_probability")
        if probability is None or probability >= 0.01:
            continue

        text = _owner_facing_text(report).lower()
        assert "immediate failure is likely" not in text
        assert "will fail soon" not in text
        assert "is likely to fail soon" not in text
