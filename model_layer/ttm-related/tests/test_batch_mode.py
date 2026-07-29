"""
Story 8 (Lucca): batch-mode and window-enumeration tests.

TTM is never loaded: `run_ttm_forecast` is monkeypatched to
return the healthy fixture values so residuals are zero and the
tests exercise windowing, envelope assembly, history wiring, and
CLI error handling only.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from group1_fixtures import (  # noqa: E402
    make_group1_frame,
    make_multi_segment_frame,
)
from model import kit_residual_detector as detector  # noqa: E402
from model.kit_residual_detector import (  # noqa: E402
    MODEL_SIGNALS,
    analyze_window,
    iter_windows,
)
from model.risk_history import (  # noqa: E402
    append_history,
    load_history,
)


def fake_forecast(context, context_length, prediction_length,
                  model=None):
    healthy = {
        signal: [float(context[signal].iloc[-1])]
        * prediction_length
        for signal in MODEL_SIGNALS
    }
    return pd.DataFrame(healthy)


class TestIterWindows:
    def test_non_overlapping_608_row_windows(self):
        segment = make_group1_frame(rows=1300)
        windows = list(iter_windows(segment, 512, 96))
        assert [index for index, _ in windows] == [0, 1]
        first, second = windows[0][1], windows[1][1]
        assert len(first) == 608 and len(second) == 608
        assert list(first["row_in_segment"])[-1] == 608
        assert list(second["row_in_segment"])[0] == 609

    def test_short_segment_yields_nothing(self):
        segment = make_group1_frame(rows=600)
        assert list(iter_windows(segment, 512, 96)) == []


class TestAnalyzeWindow:
    def test_returns_interface_json(self, monkeypatch):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        window = make_group1_frame(rows=608)
        result = analyze_window(window, 512, 96, None, [])
        assert 0.0 <= result["risk_score"] <= 1.0
        assert result["risk_level"] in {"Low", "Medium", "High"}
        assert result["estimated_cycles_to_failure"] is None
        assert result["estimated_failure_probability"] is None


class TestRunBatch:
    def _frame(self):
        return make_multi_segment_frame([
            ("trip_0001", "trip_0001_seg_001", 1300),
            ("trip_0001", "trip_0001_seg_002", 650),
            ("trip_0002", "trip_0002_seg_001", 700),
        ])

    def test_sweeps_eligible_segments_only(self, monkeypatch):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        envelope, records = detector.run_batch(
            self._frame(), 512, 96, model=None
        )
        window_ids = [r["window_id"] for r in records]
        # seg_001: 1300 rows -> 2 windows; seg_002 < 700 skipped;
        # trip_0002 seg_001: 700 rows -> 1 window.
        assert window_ids == [
            "trip_0001_seg_001__w000",
            "trip_0001_seg_001__w001",
            "trip_0002_seg_001__w000",
        ]
        assert len(envelope["windows"]) == 3

    def test_summary_is_worst_window_interface_json(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        envelope, records = detector.run_batch(
            self._frame(), 512, 96, model=None
        )
        worst = max(records, key=lambda r: r["risk_score"])
        assert (
            envelope["summary"]["risk_score"]
            == worst["risk_score"]
        )
        # summary keeps today's single-window schema exactly
        assert "window_id" not in envelope["summary"]
        for entry in envelope["windows"]:
            assert {"trip_id", "segment_id", "window_id"} <= set(
                entry
            )

    def test_history_records_match_window_outputs(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        envelope, records = detector.run_batch(
            self._frame(), 512, 96, model=None
        )
        path = tmp_path / "risk_history.csv"
        append_history(records, path)
        df = load_history(path)
        assert list(df["trip_id"]) == [
            "trip_0001", "trip_0001", "trip_0002"
        ]
        assert (df["risk_score"] >= 0).all()
        assert (df["risk_score"] <= 1).all()

    def test_trip_filter_restricts_sweep(self, monkeypatch):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        envelope, records = detector.run_batch(
            self._frame(), 512, 96, model=None,
            trip_id="trip_0002",
        )
        assert [r["trip_id"] for r in records] == ["trip_0002"]

    def test_no_eligible_segment_is_clear_error(
        self, monkeypatch
    ):
        frame = make_multi_segment_frame(
            [("trip_0001", "trip_0001_seg_001", 650)]
        )
        with pytest.raises(ValueError, match="700"):
            detector.run_batch(frame, 512, 96, model=None)


class TestCliErrors:
    def test_missing_csv_is_single_clear_error(
        self, monkeypatch, capsys, tmp_path
    ):
        monkeypatch.setattr(sys, "argv", [
            "kit_residual_detector.py",
            str(tmp_path / "missing.csv"),
        ])
        exit_code = detector.main()
        assert exit_code == 1
        err = capsys.readouterr().err
        assert err.startswith("ERROR:")
        assert len(err.strip().splitlines()) == 1
        assert "Traceback" not in err

    def test_missing_column_is_single_clear_error(
        self, monkeypatch, capsys, tmp_path
    ):
        from group1_fixtures import write_group1_csv
        path = write_group1_csv(
            tmp_path / "bad.csv", rows=10,
            drop_columns=["maf"],
        )
        monkeypatch.setattr(sys, "argv", [
            "kit_residual_detector.py", str(path),
        ])
        exit_code = detector.main()
        assert exit_code == 1
        err = capsys.readouterr().err
        assert err.startswith("ERROR:")
        assert "maf" in err

    def test_success_returns_zero(
        self, monkeypatch, capsys, tmp_path
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        monkeypatch.setattr(
            detector, "load_model", lambda *a, **k: None
        )
        csv_path = tmp_path / "ok.csv"
        make_multi_segment_frame(
            [("trip_0001", "trip_0001_seg_001", 700)]
        ).to_csv(csv_path, index=False)
        monkeypatch.setattr(sys, "argv", [
            "kit_residual_detector.py", str(csv_path),
            "--batch",
            "--history-file",
            str(tmp_path / "history.csv"),
        ])
        assert detector.main() == 0
        assert (tmp_path / "history.csv").exists()
