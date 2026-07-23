"""Cross-check raw-filename traffic labels against derived child_state.

Research/validation script, not a production contract. It matches each
raw KIT source file (whose filename encodes a human-assigned trip-level
traffic label: Normal / Frei / Stau) to its assigned `trip_id` in a
completed run's `operating_condition_enriched.csv`, then compares the
coarse filename label against the fine-grained, per-sample `child_state`
distribution the Data Layer derives independently from telemetry.

This does not feed the production pipeline and must never be imported
by scripts 00-91. It exists purely to support the Background chapter's
Dataset Selection write-up with a reproducible sanity check.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT))
from data_layer.pipeline_data.manifests import write_json_atomic  # noqa: E402
from data_layer.pipeline_data.paths import RunLayout  # noqa: E402

DEFAULT_RAW_DIR = REPO_ROOT / "data" / "raw" / "OBD-II-Dataset"
SOURCE_TIMEZONE = ZoneInfo("Europe/Berlin")
MATCH_TOLERANCE = pd.Timedelta("120s")
CONDITION_LABELS = ("Normal", "Frei", "Stau")
FILENAME_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2})_(.+)\.csv$")

OUTPUT_TRIPS_CSV = HERE / "trip_condition_labels.csv"
OUTPUT_SUMMARY_JSON = HERE / "condition_label_crosscheck_summary.json"


def _raw_file_start_utc(path: Path, file_date: str) -> datetime:
    """Read a raw file's first data row and convert its local time to UTC."""
    with open(path, "r", encoding="latin-1") as handle:
        handle.readline()  # header
        first_row = handle.readline().strip()
    time_str = first_row.split(",")[0]  # "HH:MM:SS.mmm"
    hh, mm, ss = time_str.split(":")
    year, month, day = (int(part) for part in file_date.split("-"))
    local_dt = datetime(
        year, month, day, int(hh), int(mm), int(float(ss)),
        tzinfo=SOURCE_TIMEZONE,
    )
    return local_dt.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def extract_condition_label(filename_body: str) -> str:
    """Extract Normal/Frei/Stau from a raw filename's non-date remainder."""
    tokens = filename_body.split("_")
    for label in CONDITION_LABELS:
        if label in tokens:
            return label
    return "Other"


def build_raw_index(raw_dir: Path) -> pd.DataFrame:
    """One row per raw source file: filename, condition label, start_utc."""
    rows = []
    for path_str in sorted(glob.glob(str(raw_dir / "*.csv"))):
        path = Path(path_str)
        match = FILENAME_PATTERN.match(path.name)
        if match is None:
            raise ValueError(f"Unexpected raw filename: {path.name}")
        file_date, remainder = match.groups()
        rows.append({
            "filename": path.name,
            "condition_label": extract_condition_label(remainder),
            "start_utc": _raw_file_start_utc(path, file_date),
        })
    if not rows:
        raise ValueError(f"No raw source files found under {raw_dir}.")
    return pd.DataFrame(rows)


def match_trip_ids(
    raw_index: pd.DataFrame, operating_condition_enriched: Path
) -> pd.DataFrame:
    """Match each raw file to the trip_id whose first sample starts nearest."""
    oce = pd.read_csv(
        operating_condition_enriched,
        usecols=["timestamp", "trip_id", "child_state"],
    )
    oce["timestamp"] = pd.to_datetime(oce["timestamp"]).dt.tz_localize(None)
    trip_start = (
        oce.groupby("trip_id")["timestamp"].min()
        .reset_index().sort_values("timestamp")
    )
    matched = pd.merge_asof(
        raw_index.sort_values("start_utc").reset_index(drop=True),
        trip_start.reset_index(drop=True),
        left_on="start_utc", right_on="timestamp",
        direction="nearest", tolerance=MATCH_TOLERANCE,
    )
    unmatched = matched["trip_id"].isna().sum()
    if unmatched:
        raise ValueError(
            f"{unmatched} raw file(s) did not match any trip_id within "
            f"{MATCH_TOLERANCE}; increase tolerance or re-check timezone."
        )
    return matched.drop(columns=["timestamp"]), oce


def build_summary(
    matched: pd.DataFrame, oce: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per-trip child_state shares, then averaged per condition_label."""
    child_dist = (
        oce.groupby("trip_id")["child_state"]
        .value_counts(normalize=True).unstack(fill_value=0.0)
    )
    per_trip = matched[["filename", "trip_id", "condition_label"]].merge(
        child_dist, on="trip_id", how="left", validate="one_to_one"
    )
    state_columns = child_dist.columns.tolist()
    grouped = per_trip.groupby("condition_label")[state_columns].mean()
    counts = per_trip["condition_label"].value_counts()
    grouped.insert(0, "n_trips", counts)
    return per_trip, grouped.round(4)


def run_crosscheck(
    layout: RunLayout,
    *,
    raw_dir: Path = DEFAULT_RAW_DIR,
    output_trips_csv: Path = OUTPUT_TRIPS_CSV,
    output_summary_json: Path = OUTPUT_SUMMARY_JSON,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw_index = build_raw_index(raw_dir)
    matched, oce = match_trip_ids(
        raw_index, layout.operating_condition_enriched
    )
    per_trip, summary = build_summary(matched, oce)

    output_trips_csv.parent.mkdir(parents=True, exist_ok=True)
    per_trip.sort_values("trip_id").to_csv(
        output_trips_csv, index=False, float_format="%.6g",
        lineterminator="\n",
    )
    manifest = {
        "manifest_type": "condition_label_crosscheck_summary",
        "run_id": layout.run_id,
        "raw_file_count": len(raw_index),
        "matched_trip_count": int(matched["trip_id"].nunique()),
        "condition_label_counts": (
            per_trip["condition_label"].value_counts().to_dict()
        ),
        "child_state_share_by_condition_label": (
            summary.reset_index().to_dict(orient="records")
        ),
    }
    write_json_atomic(output_summary_json, manifest)
    return per_trip, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument(
        "--raw-dir", type=Path, default=DEFAULT_RAW_DIR,
        help="Directory of raw KIT source CSV files.",
    )
    parser.add_argument(
        "--output-trips-csv", type=Path, default=OUTPUT_TRIPS_CSV
    )
    parser.add_argument(
        "--output-summary-json", type=Path, default=OUTPUT_SUMMARY_JSON
    )
    args = parser.parse_args()
    layout = RunLayout.from_run_dir(args.run_dir, repo_root=REPO_ROOT)
    _, summary = run_crosscheck(
        layout,
        raw_dir=args.raw_dir.resolve(),
        output_trips_csv=args.output_trips_csv.resolve(),
        output_summary_json=args.output_summary_json.resolve(),
    )
    print(json.dumps(
        json.loads(summary.reset_index().to_json(orient="records")),
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
