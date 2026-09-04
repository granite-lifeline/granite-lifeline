"""Focused tests for the Stage 4 fault-injection campaign helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pandas as pd
import numpy as np
import pytest


SCRIPT = (
    Path(__file__).parents[2]
    / "fault_injection"
    / "src"
    / "run_fault_injection.py"
)
SPEC = importlib.util.spec_from_file_location(
    "fault_injection_campaign", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_expand_cases_preserves_identity_and_expands_grid() -> None:
    case = {
        "case_id": "example",
        "proxy_id": "proxy",
        "expected_sub_check_id": "1-S2",
        "target_signal": "coolant_temp",
        "selector": "post_warmup",
        "strategy": "set_constant",
        "replicates": 2,
        "severity_grid": [
            {"severity_id": "mild", "parameters": {"value": 104}},
            {"severity_id": "strong", "parameters": {"value": 110}},
        ],
    }

    expanded = MODULE.expand_cases([case])

    assert len(expanded) == 2
    assert [item["_replicates"] for item in expanded] == [2, 2]
    assert [item["_severity_rank"] for item in expanded] == [0, 1]
    assert {item["case_id"] for item in expanded} == {"example"}


def test_expand_cases_rejects_identity_override() -> None:
    case = {
        "case_id": "example",
        "proxy_id": "proxy",
        "expected_sub_check_id": "1-S2",
        "target_signal": "coolant_temp",
        "selector": "post_warmup",
        "strategy": "set_constant",
        "severity_grid": [{
            "severity_id": "bad",
            "parameters": {"target_signal": "maf"},
        }],
    }

    with pytest.raises(MODULE.FaultInjectionError):
        MODULE.expand_cases([case])


def test_consecutive_window_does_not_bridge_false_rows() -> None:
    mask = pd.Series([True, True, False, True, True, True])

    assert MODULE.consecutive_window(mask, 3) == [3, 4, 5]
    assert MODULE.consecutive_window(mask, 4) is None


def test_wilson_interval_is_bounded_for_zero_events() -> None:
    low, high = MODULE.wilson_interval(0, 75)

    assert 0 <= low <= high <= 1
    assert high < 0.05


def test_json_default_converts_numpy_scalars() -> None:
    assert MODULE.json_default(np.bool_(True)) is True
    assert MODULE.json_default(np.int64(3)) == 3
    assert MODULE.json_default(np.float64(1.5)) == 1.5


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, True), (False, False), (1, True), (0, False),
     ("True", True), ("False", False)],
)
def test_parse_bool_is_strict(value: object, expected: bool) -> None:
    assert MODULE.parse_bool(value, field="flag") is expected


def test_parse_bool_rejects_ambiguous_text() -> None:
    with pytest.raises(MODULE.FaultInjectionError, match="flag"):
        MODULE.parse_bool("yes", field="flag")


def _decision_layout(tmp_path: Path, name: str, rows: list[dict]) -> object:
    path = tmp_path / f"{name}.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return SimpleNamespace(proxy_decisions=path)


def _window() -> object:
    return MODULE.Window(
        indices=[0], trip_id="trip-1", segment_id="segment-1",
        start_timestamp="2026-01-01T00:00:00Z",
        end_timestamp="2026-01-01T00:00:00Z",
    )


def _case(**overrides: object) -> dict:
    case = {
        "expected_sub_check_id": "2-S2",
        "expected_result_state": "triggered",
        "expected_dtc_candidate_label": "P0101",
        "expected_dtc_emitted": True,
        "expected_routed_dtc": "P0101",
    }
    case.update(overrides)
    return case


def _decision(**overrides: object) -> dict:
    row = {
        "sub_check_id": "2-S2",
        "trip_id": "trip-1",
        "segment_id": "segment-1",
        "result_state": "triggered",
        "decision_reason": "residual_low",
        "decision_margin": 1.0,
        "dtc_candidate_label": "P0101",
        "dtc_emitted": True,
        "routed_dtc": "P0101",
        "confidence": "high",
    }
    row.update(overrides)
    return row


def test_evaluate_case_checks_complete_decision_contract(
    tmp_path: Path,
) -> None:
    layout = _decision_layout(tmp_path, "injected", [_decision()])
    baseline = _decision_layout(
        tmp_path, "baseline", [_decision(result_state="pass")]
    )

    result = MODULE.evaluate_case(
        layout, _case(), _window(), baseline_layout=baseline
    )

    assert result["passed"] is True
    assert result["dtc_matches_expected"] is True
    assert result["emission_matches_expected"] is True
    assert result["routed_dtc_matches_expected"] is True


@pytest.mark.parametrize(
    "decision_override",
    [
        {"result_state": "pass"},
        {"dtc_candidate_label": "P0102"},
        {"dtc_emitted": False},
        {"routed_dtc": "P0106"},
    ],
)
def test_evaluate_case_rejects_contract_mismatch(
    tmp_path: Path, decision_override: dict
) -> None:
    layout = _decision_layout(
        tmp_path, "injected", [_decision(**decision_override)]
    )

    result = MODULE.evaluate_case(layout, _case(), _window())

    assert result["passed"] is False


def test_evaluate_case_rejects_baseline_false_positive(
    tmp_path: Path,
) -> None:
    layout = _decision_layout(tmp_path, "injected", [_decision()])
    baseline = _decision_layout(tmp_path, "baseline", [_decision()])

    result = MODULE.evaluate_case(
        layout, _case(), _window(), baseline_layout=baseline
    )

    assert result["baseline_already_positive"] is True
    assert result["passed"] is False


def test_evaluate_case_does_not_treat_false_text_as_true(
    tmp_path: Path,
) -> None:
    layout = _decision_layout(
        tmp_path, "injected", [_decision(dtc_emitted="False")]
    )

    result = MODULE.evaluate_case(
        layout,
        _case(expected_dtc_emitted=False, expected_routed_dtc=None),
        _window(),
    )

    assert result["dtc_emitted"] is False


def test_evaluate_case_scopes_decision_to_trip_and_segment(
    tmp_path: Path,
) -> None:
    wrong = _decision(
        trip_id="trip-2", segment_id="segment-2", result_state="pass"
    )
    layout = _decision_layout(tmp_path, "injected", [wrong, _decision()])

    result = MODULE.evaluate_case(layout, _case(), _window())

    assert result["passed"] is True


def test_recompute_rejects_absolute_zero_temperature() -> None:
    frame = pd.DataFrame({
        "coolant_temp": [20.0],
        "ambient_temp": [20.0],
        "intake_temp": [-273.15],
        "accel_pedal_d": [0.0],
        "accel_pedal_e": [0.0],
        "rpm": [500.0],
        "map": [50.0],
    })

    with pytest.raises(MODULE.FaultInjectionError, match="absolute zero"):
        MODULE.recompute_dependent_features(
            frame, MODULE.load_calibration_registry()
        )


def test_selector_uses_frozen_registry_threshold() -> None:
    registry = MODULE.load_calibration_registry()
    registry["proxy_rules"]["2-S3b"]["rpm"]["value"] = 700.0
    frame = pd.DataFrame({
        "trip_id": ["trip-1", "trip-2"],
        "segment_id": ["segment-1", "segment-2"],
        "timestamp": ["t1", "t2"],
        "rpm": [600.0, 800.0],
    })
    case = {
        "case_id": "registry-threshold",
        "selector": "engine_firing",
        "duration_seconds": 1,
        "_severity_id": "single",
    }

    windows = MODULE.select_windows(frame, case, 1, registry)

    assert windows[0].trip_id == "trip-2"


def test_run_proxy_stages_executes_50_60_61_70_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def load_stage(filename: str) -> object:
        functions = {
            function_name: (
                lambda _layout, creation_time_utc, stage=stage_id:
                calls.append((stage, creation_time_utc))
            )
            for stage_id, _filename, function_name
            in MODULE.PROXY_STAGE_FILES
            if _filename == filename
        }
        return SimpleNamespace(**functions)

    monkeypatch.setattr(MODULE, "load_stage_module", load_stage)

    MODULE.run_proxy_stages(object(), "created-at")

    assert calls == [
        ("50", "created-at"),
        ("60", "created-at"),
        ("61", "created-at"),
        ("70", "created-at"),
    ]


def test_run_batch_case_executes_injection_and_stage_oracle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base_features = tmp_path / "base.csv"
    target_features = tmp_path / "target.csv"
    decisions = tmp_path / "decisions.csv"
    pd.DataFrame({
        "trip_id": ["trip-1"],
        "segment_id": ["segment-1"],
        "timestamp": ["2026-01-01T00:00:00Z"],
        "rpm": [600.0],
        "maf": [5.0],
    }).to_csv(base_features, index=False)
    base = SimpleNamespace(
        production_features=base_features,
        proxy_decisions=tmp_path / "baseline.csv",
    )
    pd.DataFrame([_decision(result_state="pass")]).to_csv(
        base.proxy_decisions, index=False
    )
    target = SimpleNamespace(
        run_id="target-run",
        production_features=target_features,
        proxy_decisions=decisions,
        run_relative_posix=lambda path: path.name,
    )
    calls: list[str] = []

    monkeypatch.setattr(
        MODULE.RunLayout, "for_run_id", lambda *_args, **_kwargs: target
    )

    def copy_run(_base: object, _target: object) -> None:
        calls.append("copy")
        shutil.copy2(base_features, target_features)

    def recompute(frame: pd.DataFrame, _registry: dict) -> None:
        calls.append("recompute")
        assert frame.loc[0, "maf"] == 0.0

    def run_stages(_layout: object, _creation_time: str) -> None:
        calls.append("stages")
        pd.DataFrame([_decision()]).to_csv(decisions, index=False)

    monkeypatch.setattr(MODULE, "copy_minimal_run", copy_run)
    monkeypatch.setattr(MODULE, "recompute_dependent_features", recompute)
    monkeypatch.setattr(MODULE, "update_production_manifest", lambda *_: None)
    monkeypatch.setattr(MODULE, "run_proxy_stages", run_stages)

    results = MODULE.run_batch_case(
        base_layout=base,
        case={
            **_case(),
            "case_id": "campaign-test",
            "proxy_id": "air_intake_maf_anomaly",
            "target_signal": "maf",
            "selector": "engine_firing",
            "strategy": "set_constant",
            "value": 0.0,
            "_replicates": 1,
        },
        run_id="target-run",
        creation_time_utc="2026-01-01T00:00:00Z",
    )

    assert calls == ["copy", "recompute", "stages"]
    assert results[0]["passed"] is True


def test_default_config_covers_every_runtime_sub_check() -> None:
    config = (
        SCRIPT.parents[1] / "configs" / "fault_injection_cases.v1.json"
    )
    cases = MODULE.load_cases(config)

    assert {case["expected_sub_check_id"] for case in cases} == {
        "1-S1", "1-S2", "1-S3", "1-S4",
        "2-S2", "2-S3b",
        "3-S1a", "3-S1b",
        "4-S1", "4-S2", "4-S3",
        "5-S1", "5-S2", "5-S3",
    }
    assert all(len(case["severity_grid"]) >= 3 for case in cases)
    assert all(case["replicates"] >= 3 for case in cases)
    expanded = MODULE.expand_cases(cases)
    contract_cases = [
        case for case in expanded if "expected_dtc_emitted" in case
    ]
    assert contract_cases
    assert all("expected_routed_dtc" in case for case in contract_cases)
