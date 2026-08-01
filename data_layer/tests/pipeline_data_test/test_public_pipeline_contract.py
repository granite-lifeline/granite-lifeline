from __future__ import annotations

import shutil
from pathlib import Path

import pandas as pd

from data_layer import run_pipeline
from data_layer.data_cleaning.src import data_cleaning
from data_layer.data_cleaning.src.cleaning_core import load_config
from data_layer.pipeline_data.manifests import load_json_object, sha256_file
from data_layer.pipeline_data.paths import RunLayout
from data_layer.tests.pipeline_data_test import (
    test_upstream_run_layout_contract as fixture_upstream,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _copy_pipeline_contracts(tmp_path: Path) -> Path:
    relative_files = [
        "data_layer/contracts/feature_manifest.v1.json",
        "data_layer/calibration/calibration_registry.v1.json",
        "data_layer/calibration/calibration_registry.v1.manifest.json",
        "data_layer/data_cleaning/src/cleaning_config.yaml",
    ]
    for relative in relative_files:
        source = REPO_ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return tmp_path / "data_layer/data_cleaning/src/cleaning_config.yaml"


def _patch_cleaning(monkeypatch, enriched) -> None:
    def fake_clean_dataset_enriched(*args, **kwargs):
        return enriched.copy(), {
            "files_processed": 1,
            "input_rows": len(enriched),
            "trips": 1,
            "segments": 1,
        }

    monkeypatch.setattr(
        data_cleaning, "clean_dataset_enriched", fake_clean_dataset_enriched
    )


def test_public_pipeline_stops_at_stage_41_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    """The batch path must stay feature-only unless proxy is requested."""

    config_path = _copy_pipeline_contracts(tmp_path)
    config = load_config(config_path)
    enriched = fixture_upstream._fixture_enriched(config, rows=12)
    enriched["trip_id"] = "trip_0001"
    enriched["segment_id"] = "trip_0001_seg_001"
    layout = RunLayout.for_run_id("proxy-off-e2e", repo_root=tmp_path)
    _patch_cleaning(monkeypatch, enriched)

    summary = run_pipeline.run_data_pipeline(
        layout,
        config_path=config_path,
        creation_time_utc="2026-07-27T00:00:00Z",
    )

    assert "proxy_stage_ids" not in summary
    assert "proxy_decisions_path" not in summary
    assert not layout.proxy_decisions.exists()
    assert not layout.rule_state.exists()


def test_public_pipeline_runs_proxy_stages_when_requested(
    tmp_path: Path, monkeypatch
) -> None:
    """With include_proxy the run also yields decision-level output."""

    config_path = _copy_pipeline_contracts(tmp_path)
    config = load_config(config_path)
    enriched = fixture_upstream._fixture_enriched(config, rows=12)
    enriched["trip_id"] = "trip_0001"
    enriched["segment_id"] = "trip_0001_seg_001"
    layout = RunLayout.for_run_id("proxy-on-e2e", repo_root=tmp_path)
    _patch_cleaning(monkeypatch, enriched)

    summary = run_pipeline.run_data_pipeline(
        layout,
        config_path=config_path,
        creation_time_utc="2026-07-27T00:00:00Z",
        include_proxy=True,
    )

    assert summary["proxy_stage_ids"] == ["50", "60", "61", "70"]
    assert len(summary["stage_manifests"]) == 12
    assert Path(summary["proxy_decisions_path"]).is_file()
    assert summary["proxy_decisions"] == (
        "proxy/70_decisions/proxy_decisions.csv"
    )
    for path in (
        layout.rule_state,
        layout.engine_start_rule_state,
        layout.pedal_step_events,
        layout.duration_episodes,
        layout.proxy_decisions,
    ):
        assert path.is_file()
    # Even with no observed engine start, the episode artifact keeps a
    # header so stage 70 can parse it.
    episode_state = pd.read_csv(layout.engine_start_rule_state)
    assert len(episode_state.columns) > 0


def test_public_pipeline_runs_all_online_stages_with_one_layout(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = _copy_pipeline_contracts(tmp_path)
    config = load_config(config_path)
    enriched = fixture_upstream._fixture_enriched(config, rows=12)
    enriched["trip_id"] = "trip_0001"
    enriched["segment_id"] = "trip_0001_seg_001"
    layout = RunLayout.for_run_id("public-pipeline-e2e", repo_root=tmp_path)

    def fake_clean_dataset_enriched(*args, **kwargs):
        return enriched.copy(), {
            "files_processed": 1,
            "input_rows": len(enriched),
            "trips": 1,
            "segments": 1,
        }

    monkeypatch.setattr(
        data_cleaning, "clean_dataset_enriched", fake_clean_dataset_enriched
    )
    fixed_time = "2026-07-19T22:00:00Z"
    first = run_pipeline.run_data_pipeline(
        layout, config_path=config_path, creation_time_utc=fixed_time
    )
    first_hash = sha256_file(layout.production_features)
    second = run_pipeline.run_data_pipeline(
        layout, config_path=config_path, creation_time_utc=fixed_time
    )

    assert first == second
    assert sha256_file(layout.production_features) == first_hash
    assert first["feature_stage_ids"] == ["00", "10", "20", "30", "40", "41"]
    assert len(first["stage_manifests"]) == 8
    assert all(
        "90" not in item and "91" not in item
        for item in first["stage_manifests"]
    )

    expected_manifests = [
        (layout.cleaning_stage_manifest, "cleaning"),
        (layout.operating_conditions_manifest, "operating_conditions"),
        (layout.input_contract_manifest, "00"),
        (layout.atomic_features_manifest, "10"),
        (layout.engine_start_context_manifest, "20"),
        (layout.window_features_manifest, "30"),
        (layout.calibrated_features_manifest, "40"),
        (layout.production_feature_manifest, "41"),
    ]
    for path, stage_id in expected_manifests:
        assert path.is_file()
        assert load_json_object(path)["stage_id"] == stage_id

    production = pd.read_csv(layout.production_features, low_memory=False)
    keys = ["timestamp", "trip_id", "segment_id", "row_in_segment"]
    assert len(production.columns) == 46
    assert len(production) == len(enriched)
    assert production[keys].equals(
        production.sort_values(
            keys, kind="stable").reset_index(drop=True)[keys]
    )
    assert production["schema_version"].eq("feature_schema.v1").all()
    assert production["calibration_version"].eq("calibration.v1").all()
