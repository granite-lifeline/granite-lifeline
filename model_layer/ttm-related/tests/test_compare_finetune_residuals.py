from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from model.compare_finetune_residuals import build_comparison  # noqa: E402
from model.kit_residual_detector import MODEL_SIGNALS  # noqa: E402


def metrics(overall: float, values: list[float]):
    return {
        "overall_mae": overall,
        "per_signal_mae": dict(zip(MODEL_SIGNALS, values)),
    }


def test_comparison_marks_clear_improvement_when_overall_and_signals_pass():
    zero = metrics(100.0, [10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    tuned = metrics(90.0, [9.0, 20.0, 25.0, 38.0, 55.0, 54.0])

    result = build_comparison(zero, tuned)

    assert result["overall"]["improvement_pct"] == 10.0
    assert result["decision_rule"]["non_worse_signals"] == 5
    assert result["decision_rule"]["clear_improvement"] is True


def test_comparison_rejects_small_overall_improvement():
    zero = metrics(100.0, [10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
    tuned = metrics(96.0, [9.0, 19.0, 29.0, 39.0, 49.0, 59.0])

    result = build_comparison(zero, tuned)

    assert result["overall"]["improvement_pct"] == 4.0
    assert result["decision_rule"]["non_worse_signals"] == 6
    assert result["decision_rule"]["clear_improvement"] is False
