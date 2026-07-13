"""
Story 6 data preparation: healthy-trip length verification and
seeded train/validation split (Lucca subtasks).

The healthy KIT data is one combined CSV whose `source_file` column
identifies the original per-trip files. This module counts rows per
trip, excludes trips below a minimum length (default 700 rows, above
the TTM 512-context + 96-prediction window), splits eligible trips
80/20 by trip with a fixed seed, and writes a JSON manifest that
Ray's fine-tuning script consumes by filtering the combined CSV on
`source_file`. See docs: notes/user_stories.md Story 6.
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
    from model.input_validation import validate_required_columns
except ImportError:  # direct script run: src/ not on sys.path
    from input_validation import validate_required_columns

DEFAULT_MIN_ROWS = 700
DEFAULT_TRAIN_FRACTION = 0.8
DEFAULT_SEED = 42
TRIP_COLUMN = "source_file"

_TTM_RELATED_DIR = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    _TTM_RELATED_DIR
    / "data"
    / "data_cleaned_normal_free"
    / "obd2_normal_frei_cleaned_1s.csv"
)
DEFAULT_OUTPUT = (
    _TTM_RELATED_DIR / "outputs" / "finetune_split_manifest.json"
)


def trip_row_counts(df: pd.DataFrame) -> dict[str, int]:
    """Count rows per trip, keyed by original trip filename."""
    validate_required_columns(
        df.columns, [TRIP_COLUMN], "combined healthy CSV"
    )
    counts = df.groupby(TRIP_COLUMN).size()
    return {str(trip): int(count) for trip, count in counts.items()}


def partition_trips(
    counts: dict[str, int], min_rows: int = DEFAULT_MIN_ROWS
) -> tuple[list[str], list[dict]]:
    """Partition trips into eligible (>= min_rows) and excluded.

    Excluded entries carry the row count and a human-readable reason
    so the manifest records why each trip was dropped.
    """
    eligible = sorted(
        trip for trip, rows in counts.items() if rows >= min_rows
    )
    excluded = [
        {
            "source_file": trip,
            "rows": counts[trip],
            "reason": f"below minimum length {min_rows}",
        }
        for trip in sorted(counts)
        if counts[trip] < min_rows
    ]
    return eligible, excluded


def split_trips(
    trip_names: Sequence[str],
    train_fraction: float = DEFAULT_TRAIN_FRACTION,
    seed: int = DEFAULT_SEED,
) -> tuple[list[str], list[str]]:
    """Seeded 80/20 split by trip; deterministic for a given seed.

    Input is sorted before shuffling so the outcome does not depend
    on CSV row order. Train side gets floor(n * train_fraction)
    trips; both sides must end up non-empty.
    """
    trips = sorted(trip_names)
    if not trips:
        raise ValueError(
            "No eligible trips to split; check the minimum-length "
            "filter and the input CSV"
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
    df: pd.DataFrame,
    input_file: str | Path,
    min_rows: int = DEFAULT_MIN_ROWS,
    train_fraction: float = DEFAULT_TRAIN_FRACTION,
    seed: int = DEFAULT_SEED,
) -> dict:
    """Build the train/validation split record for Ray's trainer."""
    counts = trip_row_counts(df)
    eligible, excluded = partition_trips(counts, min_rows)
    train, validation = split_trips(eligible, train_fraction, seed)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": str(input_file),
        "min_rows": min_rows,
        "train_fraction": train_fraction,
        "seed": seed,
        "n_trips_total": len(counts),
        "n_trips_eligible": len(eligible),
        "trip_row_counts": counts,
        "train_trips": train,
        "validation_trips": validation,
        "excluded_trips": excluded,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify healthy trip lengths and write the Story 6 "
            "train/validation split manifest."
        )
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT,
        help="Combined healthy CSV with a source_file trip column",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help="Where to write the split manifest JSON",
    )
    parser.add_argument(
        "--min-rows", type=int, default=DEFAULT_MIN_ROWS,
        help="Minimum rows for a trip to be used (default: 700)",
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
    df = pd.read_csv(args.input)
    manifest = build_manifest(
        df, args.input, args.min_rows, args.train_fraction, args.seed
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    print(
        f"{manifest['n_trips_total']} trips: "
        f"{len(manifest['train_trips'])} train / "
        f"{len(manifest['validation_trips'])} validation / "
        f"{len(manifest['excluded_trips'])} excluded "
        f"-> {args.output}"
    )


if __name__ == "__main__":
    main()
