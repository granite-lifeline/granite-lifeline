"""Contract tests for the single-file upload intake path.

Covers ``data_layer.pipeline_data.upload_contract`` and
``run_pipeline.run_data_pipeline_for_upload``: fail-fast rejection
codes, no run artifacts on rejection, staging-directory cleanup, and
the absolute-path fields consumed by the Model Layer / Dashboard.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from data_layer import run_pipeline
from data_layer.data_cleaning.src import data_cleaning
from data_layer.data_cleaning.src.cleaning_core import load_config
from data_layer.pipeline_data.paths import RunLayout
from data_layer.pipeline_data.upload_contract import (
    MIN_UPLOAD_ROWS,
    UploadRejected,
    longest_segment_rows,
    validate_upload_csv,
    validate_usable_segment,
)
from data_layer.tests.pipeline_data_test import (
    test_public_pipeline_contract as public_contract,
)
from data_layer.tests.pipeline_data_test import (
    test_upstream_run_layout_contract as fixture_upstream,
)


VALID_KIT_NAME = "2019-05-06_Seat_Leon_Karlsruhe_Stuttgart_Normal.csv"

KIT_HEADER = [
    "Time",
    "Engine Coolant Temperature [°C]",
    "Intake Manifold Absolute Pressure [kPa]",
    "Engine RPM [RPM]",
    "Vehicle Speed Sensor [km/h]",
    "Intake Air Temperature [°C]",
    "Air Flow Rate from Mass Flow Sensor [g/s]",
    "Absolute Throttle Position [%]",
    "Ambient Air Temperature [°C]",
    "Accelerator Pedal Position D [%]",
    "Accelerator Pedal Position E [%]",
]


#: One 1 Hz row per second, so a valid fixture must clear both the row
#: floor and the duration floor: N rows span N-1 seconds.
VALID_ROWS = MIN_UPLOAD_ROWS + 1


def _write_kit_csv(
    directory: Path,
    *,
    name: str = VALID_KIT_NAME,
    header: list[str] | None = None,
    rows: int = VALID_ROWS,
) -> Path:
    columns = KIT_HEADER if header is None else header
    lines = [",".join(columns)]
    for index in range(rows):
        hour, remainder = divmod(index, 3600)
        minute, second = divmod(remainder, 60)
        time_value = f"{hour + 10:02d}:{minute:02d}:{second:02d}.0"
        lines.append(
            ",".join([time_value] + ["1.0"] * (len(columns) - 1))
        )
    path = directory / name
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_production_stub(
    directory: Path, *, rows: int = VALID_ROWS
) -> Path:
    """Minimal production_features.csv with one usable segment."""

    path = directory / "production_features.csv"
    lines = ["timestamp,trip_id,segment_id"]
    lines += [
        f"2019-05-06T10:00:{index % 60:02d}Z,trip_0001,"
        "trip_0001_seg_001"
        for index in range(rows)
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture(name="config")
def config_fixture() -> dict:
    return load_config(run_pipeline.DEFAULT_CONFIG)


def test_renamed_file_is_rejected_with_bad_filename(
    tmp_path: Path, config: dict
) -> None:
    path = _write_kit_csv(tmp_path, name="my_car_data.csv")
    with pytest.raises(UploadRejected) as excinfo:
        validate_upload_csv(path, config)
    assert excinfo.value.code == "bad_filename"
    assert "KIT" in str(excinfo.value)


def test_missing_kit_columns_are_rejected_and_named(
    tmp_path: Path, config: dict
) -> None:
    header = [
        column
        for column in KIT_HEADER
        if "Coolant" not in column and "Mass Flow" not in column
    ]
    path = _write_kit_csv(tmp_path, header=header)
    with pytest.raises(UploadRejected) as excinfo:
        validate_upload_csv(path, config)
    assert excinfo.value.code == "missing_columns"
    message = str(excinfo.value)
    assert "Engine Coolant Temperature [°C]" in message
    assert "Air Flow Rate from Mass Flow Sensor [g/s]" in message


def test_short_upload_is_rejected_with_too_few_rows(
    tmp_path: Path, config: dict
) -> None:
    path = _write_kit_csv(tmp_path, rows=MIN_UPLOAD_ROWS - 1)
    with pytest.raises(UploadRejected) as excinfo:
        validate_upload_csv(path, config)
    assert excinfo.value.code == "too_few_rows"
    assert str(MIN_UPLOAD_ROWS - 1) in str(excinfo.value)


def test_short_duration_is_rejected_even_with_enough_rows(
    tmp_path: Path, config: dict
) -> None:
    """Row count alone cannot express a duration requirement.

    KIT files are sampled at 6-12 Hz, so a file can carry thousands of
    raw rows and still cover under a minute of driving.
    """

    columns = KIT_HEADER
    lines = [",".join(columns)]
    for index in range(4000):          # well past MIN_UPLOAD_ROWS
        second, fraction = divmod(index, 10)
        time_value = f"10:00:{second % 60:02d}.{fraction}"
        lines.append(",".join([time_value] + ["1.0"] * (len(columns) - 1)))
    path = tmp_path / VALID_KIT_NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(UploadRejected) as excinfo:
        validate_upload_csv(path, config)
    assert excinfo.value.code == "too_few_rows"
    assert "seconds" in str(excinfo.value)


def test_unparsable_time_does_not_reject_at_intake(
    tmp_path: Path, config: dict
) -> None:
    """Timestamp validation belongs to cleaning, which has context."""

    columns = KIT_HEADER
    lines = [",".join(columns)]
    for _ in range(VALID_ROWS):
        lines.append(",".join(["not-a-time"] + ["1.0"] * (len(columns) - 1)))
    path = tmp_path / VALID_KIT_NAME
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert validate_upload_csv(path, config) is None


def test_fragmented_run_is_rejected_as_no_usable_segment(
    tmp_path: Path
) -> None:
    """A recording split into short pieces has no usable window."""

    path = tmp_path / "production_features.csv"
    lines = ["timestamp,trip_id,segment_id"]
    for segment in range(4):           # 4 x 200 rows: none reaches 700
        for index in range(200):
            lines.append(
                f"2019-05-06T10:00:{index % 60:02d}Z,trip_0001,"
                f"trip_0001_seg_{segment:03d}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    assert longest_segment_rows(path) == 200
    with pytest.raises(UploadRejected) as excinfo:
        validate_usable_segment(path, run_id="frag-run")
    assert excinfo.value.code == "no_usable_segment"
    assert "200" in str(excinfo.value)
    assert "frag-run" in str(excinfo.value)


def test_single_long_segment_passes_usable_segment_check(
    tmp_path: Path
) -> None:
    stub = _write_production_stub(tmp_path)
    assert longest_segment_rows(stub) == VALID_ROWS
    assert validate_usable_segment(stub) is None


def test_stage_failure_is_wrapped_as_data_pipeline_error(
    tmp_path: Path, monkeypatch
) -> None:
    """Callers are documented to receive DataPipelineError."""

    path = _write_kit_csv(tmp_path)

    class StageSpecificError(RuntimeError):
        pass

    def exploding_pipeline(layout, *, config_path, input_dir,
                           include_proxy):
        raise StageSpecificError("simulated stage contract failure")

    monkeypatch.setattr(
        run_pipeline, "run_data_pipeline", exploding_pipeline
    )
    with pytest.raises(run_pipeline.DataPipelineError) as excinfo:
        run_pipeline.run_data_pipeline_for_upload(
            path, run_id="wrap-test", repo_root=tmp_path
        )
    assert "wrap-test" in str(excinfo.value)
    assert isinstance(excinfo.value.__cause__, StageSpecificError)


def test_empty_or_missing_file_is_rejected_as_unreadable(
    tmp_path: Path, config: dict
) -> None:
    empty = tmp_path / VALID_KIT_NAME
    empty.write_text("", encoding="utf-8")
    with pytest.raises(UploadRejected) as excinfo:
        validate_upload_csv(empty, config)
    assert excinfo.value.code == "unreadable_csv"

    with pytest.raises(UploadRejected) as excinfo:
        validate_upload_csv(tmp_path / "absent" / VALID_KIT_NAME, config)
    assert excinfo.value.code == "unreadable_csv"


def test_valid_header_passes_with_encoding_variant(
    tmp_path: Path, config: dict
) -> None:
    header = [
        column.replace("°C", "Â°C") for column in KIT_HEADER
    ]
    path = _write_kit_csv(tmp_path, header=header)
    assert validate_upload_csv(path, config) is None


def test_rejected_upload_creates_no_run_directory(
    tmp_path: Path, monkeypatch
) -> None:
    path = _write_kit_csv(tmp_path, name="renamed.csv")

    def unexpected_pipeline_call(*args, **kwargs):
        raise AssertionError(
            "run_data_pipeline must not run for a rejected upload"
        )

    monkeypatch.setattr(
        run_pipeline, "run_data_pipeline", unexpected_pipeline_call
    )
    with pytest.raises(UploadRejected):
        run_pipeline.run_data_pipeline_for_upload(
            path, repo_root=tmp_path
        )
    assert not (tmp_path / "data" / "processed" / "runs").exists()


def test_upload_adapter_stages_file_and_cleans_up(
    tmp_path: Path, monkeypatch
) -> None:
    path = _write_kit_csv(tmp_path)
    observed: dict = {}

    stub = _write_production_stub(tmp_path)

    def fake_pipeline(layout, *, config_path, input_dir, include_proxy):
        staged = sorted(p.name for p in Path(input_dir).iterdir())
        observed["layout"] = layout
        observed["input_dir"] = Path(input_dir)
        observed["staged_names"] = staged
        observed["include_proxy"] = include_proxy
        return {"sentinel": True, "production_features_path": str(stub)}

    monkeypatch.setattr(run_pipeline, "run_data_pipeline", fake_pipeline)
    result = run_pipeline.run_data_pipeline_for_upload(
        path, run_id="upload-test-01", repo_root=tmp_path
    )

    assert result["sentinel"] is True
    assert observed["staged_names"] == [VALID_KIT_NAME]
    assert observed["layout"].run_id == "upload-test-01"
    assert observed["layout"].repo_root == tmp_path.resolve()
    assert not observed["input_dir"].exists()
    # The upload path enables proxy stages by default so that
    # proxy_decisions.csv is reachable from a live single-CSV run.
    assert observed["include_proxy"] is True


def test_default_upload_run_id_uses_upload_prefix(
    tmp_path: Path, monkeypatch
) -> None:
    path = _write_kit_csv(tmp_path)

    stub = _write_production_stub(tmp_path)

    def fake_pipeline(layout, *, config_path, input_dir, include_proxy):
        return {
            "run_id": layout.run_id,
            "production_features_path": str(stub),
        }

    monkeypatch.setattr(run_pipeline, "run_data_pipeline", fake_pipeline)
    result = run_pipeline.run_data_pipeline_for_upload(
        path, repo_root=tmp_path
    )
    assert result["run_id"].startswith("upload_")


def test_pipeline_summary_exposes_absolute_paths(
    tmp_path: Path, monkeypatch
) -> None:
    config_path = public_contract._copy_pipeline_contracts(tmp_path)
    config = load_config(config_path)
    enriched = fixture_upstream._fixture_enriched(config, rows=12)
    enriched["trip_id"] = "trip_0001"
    enriched["segment_id"] = "trip_0001_seg_001"
    layout = RunLayout.for_run_id("upload-abspath-e2e", repo_root=tmp_path)

    def fake_clean_dataset_enriched(*args, **kwargs):
        return enriched.copy(), {
            "files_processed": 1,
            "input_rows": len(enriched),
            "trips": 1,
            "segments": 1,
        }

    monkeypatch.setattr(
        data_cleaning,
        "clean_dataset_enriched",
        fake_clean_dataset_enriched,
    )
    summary = run_pipeline.run_data_pipeline(
        layout,
        config_path=config_path,
        creation_time_utc="2026-07-27T00:00:00Z",
    )

    features_path = Path(summary["production_features_path"])
    run_dir_path = Path(summary["run_dir_path"])
    assert features_path.is_absolute()
    assert run_dir_path.is_absolute()
    assert features_path.is_file()
    assert run_dir_path.is_dir()
    assert features_path == layout.production_features
    assert run_dir_path == layout.run_dir
    # Run-relative legacy fields are unchanged alongside the new ones.
    assert summary["production_features"] == (
        "features/41_production/production_features.csv"
    )
