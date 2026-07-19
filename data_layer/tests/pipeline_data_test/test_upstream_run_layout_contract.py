from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_layer.data_cleaning.src import data_cleaning
from data_layer.data_cleaning.src.cleaning_core import (
    UTC_TIMESTAMP_FORMAT,
    build_output_columns,
    build_quality_output_columns,
    load_config,
)
from data_layer.data_cleaning.src.quality_audit import run_quality_audit
from data_layer.operating_condition_statistics.src.operating_condition_analysis import (
    CONFIG_PATH,
    run_operating_condition_analysis,
)
from data_layer.pipeline_data.paths import RunLayout


def _fixture_enriched(config: dict, rows: int = 8) -> pd.DataFrame:
    timestamps = pd.date_range(
        "2026-01-01T00:00:00Z", periods=rows, freq="s"
    )
    signals = list(config["fields"])
    values = {
        "coolant_temp": 80.0,
        "map": 45.0,
        "rpm": 800.0,
        "speed": 0.0,
        "intake_temp": 30.0,
        "maf": 4.0,
        "tps": 15.0,
        "ambient_temp": 20.0,
        "accel_pedal_d": 10.0,
        "accel_pedal_e": 10.0,
    }
    data = {
        "timestamp": timestamps.strftime(UTC_TIMESTAMP_FORMAT),
        "trip_id": ["trip-1"] * rows,
        "segment_id": ["segment-1"] * rows,
        "row_in_segment": range(1, rows + 1),
        "source_file": ["fixture.csv"] * rows,
        "brand": ["fixture"] * rows,
        "model": ["fixture"] * rows,
        "origin": ["A"] * rows,
        "destination": ["B"] * rows,
        "route": ["A-B"] * rows,
        "condition": ["normal"] * rows,
        "route_sequence": [1] * rows,
        "source_extension": [".csv"] * rows,
        "source_timestamp_was_monotonic": [True] * rows,
        "source_sample_count": [rows] * rows,
        "observed_sensor_count": [len(signals)] * rows,
    }
    for field in signals:
        data[field] = [values[field]] * rows
        data[f"{field}_is_imputed"] = [False] * rows
        data[f"{field}_is_suspicious"] = [False] * rows
        data[f"{field}_had_hard_invalid_source"] = [False] * rows
    data["is_imputed_any"] = [False] * rows
    data["is_suspicious_any"] = [False] * rows
    data["had_hard_invalid_source_any"] = [False] * rows
    data["quality_flags"] = ["OK"] * rows
    return pd.DataFrame(data)


def _normalized_keys(frame: pd.DataFrame) -> pd.DataFrame:
    keys = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
    result = frame[keys].copy()
    result["timestamp"] = pd.to_datetime(
        result["timestamp"], utc=True, errors="raise"
    )
    return result


def test_upstream_stages_share_layout_and_emit_script_00_authorities(
    tmp_path: Path, monkeypatch
) -> None:
    config = load_config(CONFIG_PATH)
    enriched_fixture = _fixture_enriched(config)
    layout = RunLayout.for_run_id("upstream-contract", repo_root=tmp_path)

    def fake_clean_dataset_enriched(*args, **kwargs):
        return enriched_fixture.copy(), {
            "files_processed": 1,
            "input_rows": len(enriched_fixture),
            "trips": 1,
            "segments": 1,
        }

    monkeypatch.setattr(
        data_cleaning,
        "clean_dataset_enriched",
        fake_clean_dataset_enriched,
    )

    model_output, cleaning_summary = data_cleaning.run_cleaning(config, layout)
    quality_output, quality_report = run_quality_audit(config, layout)
    operating_output, operating_summary = run_operating_condition_analysis(
        layout, config_path=CONFIG_PATH
    )

    assert list(model_output.columns) == build_output_columns(config)
    assert list(quality_output.columns) == build_quality_output_columns(config)
    assert cleaning_summary["output_csv"] == "cleaning/cleaned_dataset.csv"
    assert operating_summary["dataset"] == "cleaning/cleaned_dataset.csv"
    assert quality_report["duplicate_composite_key_rows"] == 0

    quality_raw = pd.read_csv(layout.cleaning_quality)
    operating_raw = pd.read_csv(layout.operating_condition_enriched)
    assert quality_raw["timestamp"].equals(operating_raw["timestamp"])
    assert quality_raw["timestamp"].str.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
    ).all()

    quality_keys = _normalized_keys(quality_raw)
    operating_keys = _normalized_keys(operating_raw)
    assert not quality_keys.duplicated().any()
    assert not operating_keys.duplicated().any()
    pd.testing.assert_frame_equal(quality_keys, operating_keys)

    assert len(operating_output) == len(enriched_fixture)
    assert layout.cleaning_quality.is_file()
    assert layout.operating_condition_enriched.is_file()
    assert all(path.is_relative_to(layout.run_dir) for path in (
        layout.cleaned_dataset,
        layout.cleaning_enriched,
        layout.cleaning_quality,
        layout.cleaning_report,
        layout.operating_condition_enriched,
        layout.operating_condition_counts,
        layout.operating_condition_signal_summary,
        layout.operating_condition_rules,
    ))
