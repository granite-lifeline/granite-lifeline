"""
Story 8 (Lucca): batch-mode and window-enumeration tests.

TTM is never loaded: `run_ttm_forecast` is monkeypatched to
return the healthy fixture values so residuals are zero and the
tests exercise windowing, envelope assembly, history wiring, and
CLI error handling only.

Run from ttm-related/:  ../.venv/bin/python -m pytest tests -v
"""

import json
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
from model.validate_output import validate_output  # noqa: E402
from proxy_decision_fixtures import (  # noqa: E402
    IAT_PROXY,
    MAP_PROXY,
    make_decision_frame,
    make_decision_row,
    make_triggered_row,
    write_decisions_csv,
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
        assert (
            result["secondary_risk"]["risk_score"]
            <= result["risk_score"]
        )
        assert (
            result["secondary_risk"]["component"]
            != result["component"]
        )
        assert validate_output(result) == []
        assert result["estimated_cycles_to_failure"] is None
        assert result["estimated_failure_probability"] is None

    def test_emits_both_components_when_two_risks_are_high(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        window = make_group1_frame(rows=608)
        future_rows = window.index >= 512
        window.loc[future_rows, "coolant_temp"] = 110.0
        window.loc[
            future_rows, "speed_density_maf_residual"
        ] = 35.0

        result = analyze_window(window, 512, 96, None, [])

        assert result["anomaly_type"] == "cooling_degradation"
        assert result["risk_level"] == "High"
        assert (
            result["secondary_risk"]["anomaly_type"]
            == "air_intake_maf_anomaly"
        )
        assert result["secondary_risk"]["risk_level"] == "High"
        assert validate_output(result) == []


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
        # summary keeps the primary single-window schema and adds the
        # second-ranked component without changing primary fields.
        assert "window_id" not in envelope["summary"]
        assert "secondary_risk" in envelope["summary"]
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

    def test_failure_projection_is_calculated_per_component(
        self, monkeypatch
    ):
        """Different component histories must not share one projection."""
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        envelope, _ = detector.run_batch(
            self._frame(), 512, 96, model=None
        )
        calls = []

        class Estimate:
            notes = []
            estimated_failure_probability = 0.0

            def __init__(self, marker):
                self.marker = marker

            def interface_fields(self):
                return {
                    "estimated_cycles_to_failure": self.marker,
                    "estimated_failure_probability": self.marker / 100,
                }

        def fake_estimate(history):
            calls.append(history.copy())
            marker = 11 if len(calls) == 1 else 22
            return Estimate(marker)

        monkeypatch.setattr(detector, "estimate_from_history", fake_estimate)
        result = detector.add_component_estimates_to_batch(envelope)

        primary = result["windows"][0]
        secondary = primary["secondary_risk"]
        assert primary["estimated_cycles_to_failure"] != (
            secondary["estimated_cycles_to_failure"]
        )
        assert len(calls) == 2

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


class TestProxyDecisionForwarding:
    """GL-368: relayed Data Layer verdicts reach the interface JSON."""

    def _frame(self):
        return make_multi_segment_frame([
            ("trip_0001", "trip_0001_seg_001", 700),
        ])

    def test_without_decisions_the_pending_types_stay_zero(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        envelope, _ = detector.run_batch(
            self._frame(), 512, 96, model=None
        )
        summary = envelope["summary"]
        assert summary["anomaly_type"] not in {
            IAT_PROXY, MAP_PROXY
        }

    def test_emitted_dtc_wins_argmax_and_validates(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        decisions = make_decision_frame([make_triggered_row()])
        envelope, _ = detector.run_batch(
            self._frame(), 512, 96, model=None, decisions=decisions
        )
        summary = envelope["summary"]
        assert summary["anomaly_type"] == IAT_PROXY
        assert summary["component"] == IAT_PROXY
        assert summary["risk_score"] == 0.9
        assert summary["risk_level"] == "High"
        assert validate_output(summary) == []

    def test_forwarded_confidence_replaces_the_residual_value(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        decisions = make_decision_frame([
            make_triggered_row(confidence="provisional")
        ])
        envelope, _ = detector.run_batch(
            self._frame(), 512, 96, model=None, decisions=decisions
        )
        assert envelope["summary"]["prediction_confidence"] == 0.6

    def test_note_records_the_forwarded_provenance(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        decisions = make_decision_frame([make_triggered_row()])
        envelope, _ = detector.run_batch(
            self._frame(), 512, 96, model=None, decisions=decisions
        )
        notes = envelope["summary"]["notes"]
        assert any("proxy_decisions.csv" in note for note in notes)
        assert any("P0111" in note for note in notes)

    def test_key_signals_follow_the_interface_mapping(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        decisions = make_decision_frame([
            make_triggered_row(
                proxy_id=MAP_PROXY,
                sub_check_id="5-S1",
                dtc_candidate_label="P0106",
                routed_dtc="P0106",
            )
        ])
        envelope, _ = detector.run_batch(
            self._frame(), 512, 96, model=None, decisions=decisions
        )
        summary = envelope["summary"]
        assert summary["anomaly_type"] == MAP_PROXY
        # pedal_slope was missing from FEATURE_UNITS/REFERENCE_RANGES
        # until GL-368; a MAP verdict used to KeyError here.
        features = [s["feature"] for s in summary["key_signals"]]
        assert "map" in features
        assert validate_output(summary) == []

    def test_healthy_decisions_leave_the_output_unchanged(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        baseline, _ = detector.run_batch(
            self._frame(), 512, 96, model=None
        )
        forwarded, _ = detector.run_batch(
            self._frame(), 512, 96, model=None,
            decisions=make_decision_frame([make_decision_row()]),
        )
        assert forwarded["summary"] == baseline["summary"]

    def test_cli_flag_accepts_a_decisions_csv(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        monkeypatch.setattr(
            detector, "load_model", lambda *a, **k: None
        )
        csv_path = tmp_path / "features.csv"
        self._frame().to_csv(csv_path, index=False)
        decisions_path = write_decisions_csv(
            tmp_path / "decisions.csv", [make_triggered_row()]
        )
        output_path = tmp_path / "out.json"
        monkeypatch.setattr(sys, "argv", [
            "kit_residual_detector.py", str(csv_path),
            "--batch",
            "--proxy-decisions", str(decisions_path),
            "--history-file", str(tmp_path / "history.csv"),
            "--output", str(output_path),
        ])

        assert detector.main() == 0

        saved = json.loads(output_path.read_text())
        assert saved["summary"]["anomaly_type"] == IAT_PROXY

    def test_cli_reports_a_bad_decisions_file_clearly(
        self, monkeypatch, capsys, tmp_path
    ):
        csv_path = tmp_path / "features.csv"
        self._frame().to_csv(csv_path, index=False)
        monkeypatch.setattr(sys, "argv", [
            "kit_residual_detector.py", str(csv_path),
            "--batch",
            "--proxy-decisions", str(tmp_path / "absent.csv"),
        ])

        assert detector.main() == 1

        err = capsys.readouterr().err
        assert err.startswith("ERROR:")
        assert "Traceback" not in err


class TestCliErrors:
    def test_cli_does_not_expose_a_runtime_model_override(
        self, monkeypatch
    ):
        monkeypatch.setattr(sys, "argv", ["kit_residual_detector.py"])
        args = detector.parse_args()
        assert not hasattr(args, "model_path")

    def test_runtime_loads_the_evaluated_fine_tuned_model(
        self, monkeypatch
    ):
        captured = {}

        class FakeModel:
            def eval(self):
                return self

        def fake_get_model(model_path, **kwargs):
            captured["model_path"] = model_path
            captured.update(kwargs)
            return FakeModel()

        monkeypatch.setattr(detector, "get_model", fake_get_model)

        detector.load_model(512, 96)

        assert captured == {
            "model_path": str(detector.OFFICIAL_DETECTOR_MODEL_PATH),
            "context_length": 512,
            "prediction_length": 96,
        }

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
        load_calls = []

        def fake_load_model(context_length, prediction_length):
            load_calls.append((context_length, prediction_length))
            return None

        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        monkeypatch.setattr(
            detector, "load_model", fake_load_model
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
        assert load_calls == [(512, 96)]
        assert (tmp_path / "history.csv").exists()


class TestSingleRunFailureProjection:
    """Non-batch mode has one global history, but still emits a
    ``secondary_risk`` object (GL-445): it must get the same real
    projection as the primary risk, not the ``None`` placeholders."""

    def test_secondary_risk_shares_the_primary_projection(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(
            detector, "run_ttm_forecast", fake_forecast
        )
        monkeypatch.setattr(
            detector, "load_model", lambda *a, **k: None
        )

        class Estimate:
            notes = []
            estimated_failure_probability = 0.42

            def interface_fields(self):
                return {
                    "estimated_cycles_to_failure": 7,
                    "estimated_failure_probability": 0.42,
                }

        monkeypatch.setattr(
            detector, "estimate_from_history", lambda history: Estimate()
        )

        csv_path = tmp_path / "ok.csv"
        make_multi_segment_frame(
            [("trip_0001", "trip_0001_seg_001", 700)]
        ).to_csv(csv_path, index=False)
        output_path = tmp_path / "result.json"
        monkeypatch.setattr(sys, "argv", [
            "kit_residual_detector.py", str(csv_path),
            "--history-file", str(tmp_path / "history.csv"),
            "--output", str(output_path),
        ])

        assert detector.main() == 0
        result = json.loads(output_path.read_text())

        assert result["estimated_cycles_to_failure"] == 7
        assert result["estimated_failure_probability"] == 0.42
        assert result["secondary_risk"]["estimated_cycles_to_failure"] == 7
        assert (
            result["secondary_risk"]["estimated_failure_probability"]
            == 0.42
        )
