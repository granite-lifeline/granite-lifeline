"""Focused tests for the Stage 4 fault-injection campaign helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

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
