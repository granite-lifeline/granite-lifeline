"""
Story 6 data preparation: segment eligibility check and seeded
train/validation split on Group 1's data (Lucca subtasks).

Input is Group 1's `feature_dataset.csv`, keyed by `trip_id` /
`segment_id` / `row_in_segment`. A segment is eligible when it has
at least 700 contiguous rows (above the TTM 512-context +
96-prediction window, windows must not cross segment boundaries)
AND every row is healthy per the `final_label_*` columns in Group
1's `proxy_training_labels.csv`. A segment containing any unhealthy
row is excluded whole — individual rows are never dropped, because
that would break the row contiguity the TTM windows require.

Labels are joined to the feature rows on `timestamp`, which is
globally unique (one vehicle, chronological trips at 1 Hz) — NOT on
trip/segment ids, because Group 1's trip numbering drifted between
the two deliveries (21 trips renumbered in the 2026-07-12 drop, seen
2026-07-14). `feature_dataset.csv`'s trip_id/segment_id values are
authoritative; the ids inside the labels CSV are ignored.

The 80/20 split is grouped by trip: all eligible segments of a trip
land on the same side, so correlated segments of one drive cannot
leak between train and validation. The split fraction therefore
holds on trips, not segments or rows. Ray's fine-tuning script
consumes the JSON manifest by filtering `feature_dataset.csv` on
the listed segment ids. The manifest's `input_file`/`labels_file`
are recorded relative to the repo root (posix separators) so the
manifest is portable across machines — resolve them from your own
repo root. See docs: notes/user_stories.md Story 6.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from math import floor
from pathlib import Path
from typing import Sequence

import pandas as pd

try:
    from model.input_validation import (
        GROUP1_REQUIRED_COLUMNS,
        validate_required_columns,
    )
except ImportError:  # direct script run: src/ not on sys.path
    from input_validation import (
        GROUP1_REQUIRED_COLUMNS,
        validate_required_columns,
    )

DEFAULT_MIN_ROWS = 700
DEFAULT_TRAIN_FRACTION = 0.8
DEFAULT_SEED = 42
TRIP_COLUMN = "trip_id"
SEGMENT_COLUMN = "segment_id"
ROW_COLUMN = "row_in_segment"
KEY_COLUMNS = [TRIP_COLUMN, SEGMENT_COLUMN, ROW_COLUMN]
TIMESTAMP_COLUMN = "timestamp"
LABEL_PREFIX = "final_label_"

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TTM_RELATED_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    _REPO_ROOT / "data_layer" / "feature_engineering"
    / "feature_dataset.csv"
)
DEFAULT_LABELS = (
    _REPO_ROOT / "data_layer" / "proxy_design"
    / "proxy_training_labels.csv"
)
DEFAULT_OUTPUT = (
    _TTM_RELATED_DIR / "outputs" / "finetune_split_manifest.json"
)


def repo_relative(path: str | Path) -> str:
    """Path as repo-root-relative posix string; as-given if outside.

    The manifest is handed to Ray, whose checkout lives at a
    different absolute path, so recorded paths must not embed this
    machine's directory layout.
    """
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def load_key_columns(csv_path: Path) -> pd.DataFrame:
    """Load only the trip/segment/row key columns of the feature CSV.

    The header is validated against the full Group 1 interface first
    (catches a wrong or stale file cheaply), but only the key and
    timestamp columns are read into memory — the split never needs
    the ~40 signal and feature columns of the ~96 MB file.
    """
    header = pd.read_csv(csv_path, nrows=0)
    validate_required_columns(
        header.columns, GROUP1_REQUIRED_COLUMNS, str(csv_path)
    )
    return pd.read_csv(
        csv_path, usecols=KEY_COLUMNS + [TIMESTAMP_COLUMN]
    )


def find_label_columns(columns: Sequence[str]) -> list[str]:
    """Discover `final_label_*` columns by prefix, sorted.

    Never hardcode the anomaly-type list: the Data Layer adds and
    removes proxy types between deliveries (e.g. the electronic
    throttle type was dropped on 2026-07-13).
    """
    labels = sorted(
        column for column in columns
        if str(column).startswith(LABEL_PREFIX)
    )
    if not labels:
        raise ValueError(
            f"No columns with prefix '{LABEL_PREFIX}' found; is this "
            "really Group 1's proxy_training_labels.csv?"
        )
    return labels


def load_segment_labels(csv_path: Path) -> pd.DataFrame:
    """Load timestamps plus `final_label_*` columns only.

    The labels CSV's own trip/segment ids are deliberately NOT read:
    Group 1's trip numbering is not stable across deliveries, so the
    row identity is the timestamp and the segment ids come from the
    feature frame after the join.
    """
    header = pd.read_csv(csv_path, nrows=0)
    validate_required_columns(
        header.columns, [TIMESTAMP_COLUMN], str(csv_path)
    )
    label_columns = find_label_columns(header.columns)
    return pd.read_csv(
        csv_path,
        usecols=[TIMESTAMP_COLUMN] + label_columns,
    )


def validate_label_alignment(
    features: pd.DataFrame, labels: pd.DataFrame
) -> None:
    """Fail loudly unless the two frames cover identical rows.

    The labels CSV must mirror the feature CSV row-for-row on the
    timestamp key; a silent mismatch would let unhealthy rows slip
    into training unlabelled.
    """
    feature_keys = pd.Index(features[TIMESTAMP_COLUMN])
    label_keys = pd.Index(labels[TIMESTAMP_COLUMN])
    for name, keys in (
        ("feature", feature_keys), ("labels", label_keys)
    ):
        if keys.duplicated().any():
            sample = keys[keys.duplicated()][:5].tolist()
            raise ValueError(
                f"Duplicate timestamp keys in the {name} frame, "
                f"e.g. {sample}"
            )
    if len(feature_keys) != len(label_keys):
        raise ValueError(
            f"Row count mismatch: {len(feature_keys)} feature rows "
            f"vs {len(label_keys)} label rows"
        )
    difference = feature_keys.symmetric_difference(label_keys)
    if len(difference):
        raise ValueError(
            f"Feature and label timestamps differ on "
            f"{len(difference)} rows, e.g. {difference[:5].tolist()}"
        )


def segment_summary(features: pd.DataFrame) -> pd.DataFrame:
    """One row per segment: [trip_id, segment_id, rows]."""
    validate_required_columns(
        features.columns, KEY_COLUMNS, "Group 1 feature frame"
    )
    trips_per_segment = features.groupby(SEGMENT_COLUMN)[
        TRIP_COLUMN
    ].nunique()
    conflicted = trips_per_segment[trips_per_segment > 1]
    if not conflicted.empty:
        raise ValueError(
            "segment_id values mapped to more than one trip_id: "
            f"{sorted(conflicted.index)[:5]}"
        )
    summary = (
        features.groupby([TRIP_COLUMN, SEGMENT_COLUMN])
        .size()
        .reset_index(name="rows")
    )
    return summary


def unhealthy_segments(labels: pd.DataFrame) -> dict[str, int]:
    """Count unhealthy rows per segment from `final_label_*`.

    Expects a frame carrying the authoritative `segment_id` (i.e.
    the feature frame merged with the label columns on timestamp).
    A row is unhealthy when any label differs from 0; NaN labels
    count as unhealthy (fail-safe: unlabelled rows must not be
    trained on as healthy). Only flagged segments are returned.
    """
    label_columns = find_label_columns(labels.columns)
    flagged = labels[label_columns].ne(0).any(axis=1)
    counts = (
        labels.loc[flagged].groupby(SEGMENT_COLUMN).size()
    )
    return {
        str(segment): int(count)
        for segment, count in counts.items()
    }


def partition_segments(
    summary: pd.DataFrame,
    unhealthy: dict[str, int],
    min_rows: int = DEFAULT_MIN_ROWS,
) -> tuple[dict[str, list[str]], list[dict]]:
    """Partition segments into eligible-by-trip and excluded.

    A segment is eligible when it has >= min_rows rows AND no
    unhealthy rows. Eligible segments are grouped by trip (sorted);
    trips whose segments all fail are absent from the eligible dict.
    Excluded entries carry the row count and a human-readable reason
    so the manifest records why each segment was dropped.
    """
    eligible: dict[str, list[str]] = {}
    excluded: list[dict] = []
    ordered = summary.sort_values(SEGMENT_COLUMN)
    for record in ordered.itertuples(index=False):
        trip = str(getattr(record, TRIP_COLUMN))
        segment = str(getattr(record, SEGMENT_COLUMN))
        rows = int(record.rows)
        reasons = []
        if rows < min_rows:
            reasons.append(f"below minimum length {min_rows}")
        if segment in unhealthy:
            reasons.append(
                f"{unhealthy[segment]} rows flagged unhealthy by "
                "final_label_*"
            )
        if reasons:
            excluded.append(
                {
                    "trip_id": trip,
                    "segment_id": segment,
                    "rows": rows,
                    "reason": "; ".join(reasons),
                }
            )
        else:
            eligible.setdefault(trip, []).append(segment)
    eligible = {
        trip: sorted(segments)
        for trip, segments in sorted(eligible.items())
    }
    return eligible, excluded


def split_trips(
    trip_names: Sequence[str],
    train_fraction: float = DEFAULT_TRAIN_FRACTION,
    seed: int = DEFAULT_SEED,
) -> tuple[list[str], list[str]]:
    """Seeded 80/20 split of trip_id values; deterministic per seed.

    Input is sorted before shuffling so the outcome does not depend
    on CSV row order. Train side gets floor(n * train_fraction)
    trips; both sides must end up non-empty.
    """
    trips = sorted(trip_names)
    if not trips:
        raise ValueError(
            "No eligible trips to split; check the minimum-length "
            "filter, the final_label_* filter and the input CSV"
        )
    random.Random(seed).shuffle(trips)
    n_train = floor(len(trips) * train_fraction)
    train, validation = trips[:n_train], trips[n_train:]
    if not train or not validation:
        raise ValueError(
            f"Split leaves an empty side ({len(train)} train / "
            f"{len(validation)} validation from {len(trips)} trips); "
            "adjust train_fraction or provide more trips"
        )
    return train, validation


def build_manifest(
    features: pd.DataFrame,
    labels: pd.DataFrame,
    input_file: str | Path,
    labels_file: str | Path,
    min_rows: int = DEFAULT_MIN_ROWS,
    train_fraction: float = DEFAULT_TRAIN_FRACTION,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Build the train/validation split record for Ray's trainer."""
    validate_label_alignment(features, labels)
    summary = segment_summary(features)
    joined = features.merge(labels, on=TIMESTAMP_COLUMN)
    unhealthy = unhealthy_segments(joined)
    eligible, excluded = partition_segments(
        summary, unhealthy, min_rows
    )
    train, validation = split_trips(
        sorted(eligible), train_fraction, seed
    )
    segment_rows = {
        str(getattr(record, SEGMENT_COLUMN)): int(record.rows)
        for record in summary.sort_values(SEGMENT_COLUMN).itertuples(
            index=False
        )
    }
    n_eligible_segments = sum(
        len(segments) for segments in eligible.values()
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_file),
        "labels_file": str(labels_file),
        "min_rows": min_rows,
        "train_fraction": train_fraction,
        "seed": seed,
        "label_columns": find_label_columns(labels.columns),
        "n_trips_total": int(features[TRIP_COLUMN].nunique()),
        "n_trips_eligible": len(eligible),
        "n_segments_total": len(summary),
        "n_segments_eligible": n_eligible_segments,
        "segment_row_counts": segment_rows,
        "train_trips": {trip: eligible[trip] for trip in train},
        "validation_trips": {
            trip: eligible[trip] for trip in validation
        },
        "excluded_segments": excluded,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check segment eligibility on Group 1's feature dataset "
            "and write the Story 6 train/validation split manifest."
        )
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help="Group 1 feature_dataset.csv keyed by trip/segment id",
    )
    parser.add_argument(
        "--labels", type=Path, default=DEFAULT_LABELS,
        help=(
            "Group 1 proxy_training_labels.csv with final_label_* "
            "columns"
        ),
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help="Where to write the split manifest JSON",
    )
    parser.add_argument(
        "--min-rows", type=int, default=DEFAULT_MIN_ROWS,
        help="Minimum rows for a segment to be used (default: 700)",
    )
    parser.add_argument(
        "--train-fraction", type=float, default=DEFAULT_TRAIN_FRACTION,
        help="Fraction of eligible trips used for training",
    )
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED,
        help="Shuffle seed for the reproducible split",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    features = load_key_columns(args.input)
    labels = load_segment_labels(args.labels)
    manifest = build_manifest(
        features, labels,
        repo_relative(args.input), repo_relative(args.labels),
        args.min_rows, args.train_fraction, args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    n_train_segments = sum(
        len(segments) for segments in manifest["train_trips"].values()
    )
    n_validation_segments = sum(
        len(segments)
        for segments in manifest["validation_trips"].values()
    )
    print(
        f"{manifest['n_segments_total']} segments in "
        f"{manifest['n_trips_total']} trips: "
        f"{manifest['n_segments_eligible']} eligible -> "
        f"{n_train_segments} train / "
        f"{n_validation_segments} validation / "
        f"{len(manifest['excluded_segments'])} excluded "
        f"-> {args.output}"
    )


if __name__ == "__main__":
    main()
