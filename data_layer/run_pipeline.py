"""Single public entry point for the online Data Layer pipeline."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any

from data_layer.data_cleaning.src import data_cleaning
from data_layer.data_cleaning.src.cleaning_core import load_config
from data_layer.data_cleaning.src.quality_audit import run_quality_audit
from data_layer.operating_condition_statistics.src import (
    operating_condition_analysis,
)
from data_layer.pipeline_data.manifests import (
    ArtifactDescriptor,
    build_stage_manifest,
    compute_source_dataset_identity,
    validate_stage_manifest,
    verify_manifest_artifacts,
    write_json_atomic,
)
from data_layer.pipeline_data.paths import RunLayout, repo_relative_posix
from data_layer.pipeline_data.upload_contract import (
    UploadRejected,
    validate_upload_csv,
    validate_usable_segment,
)


__all__ = [
    "DataPipelineError",
    "UploadRejected",
    "run_data_pipeline",
    "run_data_pipeline_for_upload",
    "run_data_pipeline_for_uploads",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = (
    REPO_ROOT / "data_layer/data_cleaning/src/cleaning_config.yaml"
)
FEATURE_STAGE_FILES = (
    ("00", "00_input_contract_validator.py", "run_input_contract_validation"),
    ("10", "10_atomic_feature_builder.py", "run_atomic_feature_builder"),
    ("20", "20_engine_start_context_builder.py",
     "run_engine_start_context_builder"),
    ("30", "30_window_feature_builder.py", "run_window_feature_builder"),
    ("40", "40_calibrated_feature_builder.py",
     "run_calibrated_feature_builder"),
    ("41", "41_production_feature_assembler.py",
     "run_production_feature_assembler"),
)
# Proxy evidence and decision stages.  These run only when the caller
# opts in: the batch/CLI path stays feature-only, while the Dashboard
# upload path enables them so `proxy_decisions.csv` is reachable from a
# live single-CSV run.  `run_fault_injection.py` keeps its own copy of
# this list because it reruns these stages on injected copies.
PROXY_STAGE_FILES = (
    ("50", "50_rule_state_builder.py", "run_rule_state_builder"),
    ("60", "60_event_evidence_builder.py", "run_event_evidence_builder"),
    ("61", "61_duration_evidence_builder.py",
     "run_duration_evidence_builder"),
    ("70", "70_proxy_decision_builder.py", "run_proxy_decision_builder"),
)


class DataPipelineError(RuntimeError):
    """Raised when the public online pipeline cannot complete its contract."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _load_stage_module(
    filename: str,
    *,
    source_dir: str = "data_layer/feature_engineering/src",
) -> ModuleType:
    path = REPO_ROOT / source_dir / filename
    name = f"data_layer_public_{filename.removesuffix('.py')}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DataPipelineError(f"Cannot load pipeline stage: {path}.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _run_descriptor(
    path: Path, *, artifact_id: str, layout: RunLayout
) -> ArtifactDescriptor:
    return ArtifactDescriptor.from_file(
        path,
        artifact_id=artifact_id,
        manifest_path=layout.run_relative_posix(path),
        path_base="run_dir",
    )


def _repo_descriptor(
    path: Path, *, artifact_id: str, layout: RunLayout
) -> ArtifactDescriptor:
    return ArtifactDescriptor.from_file(
        path,
        artifact_id=artifact_id,
        manifest_path=repo_relative_posix(path, repo_root=layout.repo_root),
        path_base="repo_root",
    )


def _write_upstream_manifests(
    layout: RunLayout,
    *,
    config_path: Path,
    cleaning_summary: dict[str, Any],
    operating_summary: dict[str, Any],
    creation_time_utc: str,
) -> None:
    cleaning_outputs = [
        _run_descriptor(layout.cleaned_dataset,
                        artifact_id="cleaned_dataset", layout=layout),
        _run_descriptor(layout.cleaning_enriched,
                        artifact_id="cleaning_enriched", layout=layout),
        _run_descriptor(layout.cleaning_quality,
                        artifact_id="cleaning_quality", layout=layout),
        _run_descriptor(layout.cleaning_report,
                        artifact_id="cleaning_report", layout=layout),
    ]
    source_identity = compute_source_dataset_identity(cleaning_outputs)
    cleaning_manifest = build_stage_manifest(
        stage_id="cleaning",
        schema_version="feature_schema.v1",
        script_version="1.0.0",
        source_dataset_identity=source_identity,
        input_artifacts=[
            _repo_descriptor(
                config_path, artifact_id="cleaning_config", layout=layout)
        ],
        output_artifacts=cleaning_outputs,
        calibration_version=None,
        creation_time_utc=creation_time_utc,
    )
    cleaning_manifest["run_summary"] = cleaning_summary
    validate_stage_manifest(cleaning_manifest)
    write_json_atomic(layout.cleaning_stage_manifest, cleaning_manifest)

    operating_outputs = [
        _run_descriptor(
            layout.operating_condition_enriched,
            artifact_id="operating_condition_enriched",
            layout=layout,
        ),
        _run_descriptor(
            layout.operating_condition_counts,
            artifact_id="operating_condition_counts_overall",
            layout=layout,
        ),
        _run_descriptor(
            layout.operating_condition_signal_summary,
            artifact_id="operating_condition_signal_summary",
            layout=layout,
        ),
        _run_descriptor(
            layout.operating_condition_rules,
            artifact_id="operating_condition_rules",
            layout=layout,
        ),
    ]
    operating_manifest = build_stage_manifest(
        stage_id="operating_conditions",
        schema_version="feature_schema.v1",
        script_version="1.0.0",
        source_dataset_identity=source_identity,
        input_artifacts=[
            _run_descriptor(
                layout.cleaning_stage_manifest,
                artifact_id="cleaning_stage_manifest",
                layout=layout,
            ),
            _run_descriptor(
                layout.cleaned_dataset,
                artifact_id="cleaned_dataset",
                layout=layout,
            ),
        ],
        output_artifacts=operating_outputs,
        calibration_version=None,
        creation_time_utc=creation_time_utc,
    )
    operating_manifest["run_summary"] = operating_summary
    validate_stage_manifest(operating_manifest)
    write_json_atomic(layout.operating_conditions_manifest, operating_manifest)


def _run_stage(
    stage_id: str,
    function: Any,
    layout: RunLayout,
    timestamp: str,
) -> Any:
    """Execute one stage, normalising failures to DataPipelineError.

    Stage modules raise their own contract errors (for example
    ``RuleStateContractError``).  Callers are documented to receive
    :class:`DataPipelineError`, so the original exception is wrapped
    and chained rather than allowed to escape unrecognised.
    """

    try:
        return function(layout, creation_time_utc=timestamp)
    except DataPipelineError:
        raise
    except Exception as exc:
        raise DataPipelineError(
            f"Stage {stage_id} failed for run '{layout.run_id}': {exc}"
        ) from exc


def run_data_pipeline(
    layout: RunLayout,
    *,
    config_path: str | Path = DEFAULT_CONFIG,
    input_dir: str | Path | None = None,
    creation_time_utc: str | None = None,
    include_proxy: bool = False,
) -> dict[str, Any]:
    """Run cleaning -> operating conditions -> 00/10/20/30/40/41.

    With ``include_proxy`` the proxy evidence and decision stages
    50/60/61/70 run afterwards in the same run directory, adding
    ``proxy_decisions_path`` and ``proxy_stage_ids`` to the summary and
    the four proxy manifests to ``stage_manifests``.  It defaults to
    ``False`` so the batch and CLI paths stay feature-only.
    """

    timestamp = creation_time_utc or _utc_now()
    config_target = Path(config_path).expanduser().resolve()
    config = copy.deepcopy(load_config(config_target))
    if input_dir is not None:
        config["input"]["directory"] = str(
            Path(input_dir).expanduser().resolve())
    layout.create_directories()
    _, cleaning_summary = data_cleaning.run_cleaning(config, layout)
    _, quality_summary = run_quality_audit(config, layout)
    cleaning_summary = {**cleaning_summary, "quality_audit": quality_summary}
    _, operating_summary = (
        operating_condition_analysis.run_operating_condition_analysis(
            layout, config_path=config_target
        )
    )
    _write_upstream_manifests(
        layout,
        config_path=config_target,
        cleaning_summary=cleaning_summary,
        operating_summary=operating_summary,
        creation_time_utc=timestamp,
    )

    stage_results: dict[str, Any] = {}
    for stage, filename, function_name in FEATURE_STAGE_FILES:
        module = _load_stage_module(filename)
        function = getattr(module, function_name)
        stage_results[stage] = _run_stage(
            stage, function, layout, timestamp
        )

    proxy_results: dict[str, Any] = {}
    if include_proxy:
        for stage, filename, function_name in PROXY_STAGE_FILES:
            module = _load_stage_module(
                filename, source_dir="data_layer/proxy_failure/src"
            )
            function = getattr(module, function_name)
            proxy_results[stage] = _run_stage(
                stage, function, layout, timestamp
            )

    manifest_paths = [
        layout.cleaning_stage_manifest,
        layout.operating_conditions_manifest,
        layout.input_contract_manifest,
        layout.atomic_features_manifest,
        layout.engine_start_context_manifest,
        layout.window_features_manifest,
        layout.calibrated_features_manifest,
        layout.production_feature_manifest,
    ]
    if include_proxy:
        manifest_paths += [
            layout.rule_state_manifest,
            layout.event_evidence_manifest,
            layout.duration_evidence_manifest,
            layout.proxy_decision_manifest,
        ]
    for path in manifest_paths:
        if not path.is_file():
            raise DataPipelineError(
                f"Required stage manifest was not produced: {path}.")
        verify_manifest_artifacts(
            json.loads(path.read_text(encoding="utf-8")),
            run_dir=layout.run_dir,
            repo_root=layout.repo_root,
        )
    return {
        "run_id": layout.run_id,
        "run_dir": layout.run_relative_posix(layout.run_dir / ".") or ".",
        "production_features": layout.run_relative_posix(
            layout.production_features
        ),
        "production_manifest": layout.run_relative_posix(
            layout.production_feature_manifest
        ),
        "stage_manifests": [
            layout.run_relative_posix(path) for path in manifest_paths
        ],
        "feature_stage_ids": list(stage_results),
        # Absolute paths for downstream consumers (Model Layer /
        # Dashboard) that read artifacts without a RunLayout.  The
        # run-relative fields above are unchanged for compatibility.
        "run_dir_path": str(layout.run_dir),
        "production_features_path": str(layout.production_features),
        **(
            {
                "proxy_stage_ids": list(proxy_results),
                "proxy_decisions": layout.run_relative_posix(
                    layout.proxy_decisions
                ),
                "proxy_decisions_path": str(layout.proxy_decisions),
            }
            if include_proxy
            else {}
        ),
    }


def run_data_pipeline_for_upload(
    csv_path: str | Path,
    *,
    run_id: str | None = None,
    repo_root: str | Path = REPO_ROOT,
    config_path: str | Path = DEFAULT_CONFIG,
    include_proxy: bool = True,
) -> dict[str, Any]:
    """Run the online pipeline for one uploaded KIT OBD-II CSV file.

    Thin single-file adapter over :func:`run_data_pipeline` for the
    Dashboard upload flow.  ``csv_path`` must point to a CSV saved on
    disk (the Dashboard is responsible for persisting its uploaded
    file object to a path first).  The file must keep its original
    KIT file name, because the recording date is parsed from the
    name.

    Intake validation (KIT file name, required KIT columns, minimum
    row count) runs before any run directory is created, so a
    rejected upload leaves no run artifacts behind.  Raises
    :class:`UploadRejected` with a machine-readable ``code`` on
    intake failure and :class:`DataPipelineError` on pipeline
    failure.  On success, returns the :func:`run_data_pipeline`
    summary, whose ``production_features_path`` field is the absolute
    path handed to the Model Layer.

    After the pipeline completes, the cleaned output must contain at
    least one contiguous segment of >= 700 rows (INTERFACE.md §1.5);
    otherwise :class:`UploadRejected` is raised with code
    ``no_usable_segment``.  The run directory is kept in that case so
    the result can be inspected.

    ``include_proxy`` defaults to ``True`` here, unlike the batch
    entry point: an uploaded run also produces
    ``proxy_decisions.csv``, whose absolute path is returned as
    ``proxy_decisions_path``.  Pass ``False`` to stop at stage 41.
    """

    source = Path(csv_path).expanduser().resolve(strict=False)
    config = load_config(Path(config_path).expanduser().resolve())
    validate_upload_csv(source, config)

    resolved_run_id = run_id or datetime.now(timezone.utc).strftime(
        "upload_%Y%m%dT%H%M%SZ"
    )
    layout = RunLayout.for_run_id(resolved_run_id, repo_root=repo_root)

    staging_dir = Path(tempfile.mkdtemp(prefix="gl_upload_"))
    try:
        shutil.copyfile(source, staging_dir / source.name)
        try:
            summary = run_data_pipeline(
                layout,
                config_path=config_path,
                input_dir=staging_dir,
                include_proxy=include_proxy,
            )
        except DataPipelineError:
            raise
        except Exception as exc:
            # Honour the documented contract: pipeline failures reach
            # the caller as DataPipelineError, whatever stage raised.
            raise DataPipelineError(
                f"Pipeline stage failed for run '{layout.run_id}': "
                f"{exc}"
            ) from exc
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    # Post-run acceptance: the Model Layer needs one contiguous
    # segment of >= 700 cleaned 1 Hz rows; a fragmented recording can
    # pass every intake heuristic and still fail this.  The run
    # directory is kept for inspection and named in the message.
    validate_usable_segment(
        Path(summary["production_features_path"]),
        run_id=layout.run_id,
    )
    return summary


def run_data_pipeline_for_uploads(
    csv_paths: list[str | Path],
    *,
    run_id: str | None = None,
    repo_root: str | Path = REPO_ROOT,
    config_path: str | Path = DEFAULT_CONFIG,
    include_proxy: bool = True,
) -> dict[str, Any]:
    """Run one joint pipeline over an ordered uploaded trip history.

    Each source file is validated independently, then all files are copied
    into one staging directory. The normal Data Layer discovers that directory
    once, assigns chronological trip identifiers, preserves trip boundaries,
    and produces one combined production feature artifact for the Model Layer.
    """
    if not csv_paths:
        raise DataPipelineError("No upload files were supplied.")

    sources = [Path(path).expanduser().resolve(strict=False)
               for path in csv_paths]
    config = load_config(Path(config_path).expanduser().resolve())
    for source in sources:
        validate_upload_csv(source, config)

    resolved_run_id = run_id or datetime.now(timezone.utc).strftime(
        "upload_history_%Y%m%dT%H%M%SZ"
    )
    layout = RunLayout.for_run_id(resolved_run_id, repo_root=repo_root)
    staging_dir = Path(tempfile.mkdtemp(prefix="gl_upload_history_"))
    try:
        for source in sources:
            shutil.copyfile(source, staging_dir / source.name)
        summary = run_data_pipeline(
            layout,
            config_path=config_path,
            input_dir=staging_dir,
            include_proxy=include_proxy,
        )
    except DataPipelineError:
        raise
    except Exception as exc:
        raise DataPipelineError(
            f"Pipeline stage failed for run '{layout.run_id}': {exc}"
        ) from exc
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    validate_usable_segment(
        Path(summary["production_features_path"]),
        run_id=layout.run_id,
    )
    return summary


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the complete online Data Layer pipeline for one "
            "explicit run ID."
        )
    )
    parser.add_argument(
        "--run-id", help="Explicit run identifier; never 'latest'.")
    parser.add_argument(
        "--input-dir", help="Optional raw KIT CSV input directory override.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument(
        "--include-proxy",
        action="store_true",
        help="Also run proxy stages 50/60/61/70 after stage 41.",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    run_id = args.run_id or datetime.now(
        timezone.utc).strftime("run_%Y%m%dT%H%M%SZ")
    try:
        layout = RunLayout.for_run_id(run_id, repo_root=REPO_ROOT)
        summary = run_data_pipeline(
            layout,
            config_path=args.config,
            input_dir=args.input_dir,
            include_proxy=args.include_proxy,
        )
    except (
        DataPipelineError, OSError, KeyError, TypeError, ValueError
    ) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
