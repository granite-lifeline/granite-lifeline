"""Upload intake contract for single-file Dashboard uploads.

Fail-fast validation for one user-uploaded KIT OBD-II CSV before any
run directory is created or any pipeline stage executes.  The rules
are derived from the cleaning configuration
(``data_layer/data_cleaning/src/cleaning_config.yaml``) instead of
being hard-coded, so the intake contract cannot drift from the
cleaning contract.

Decision record (Sprint 4 upload intake):

- Uploaded files must keep their original KIT file name
  (``<date>_<brand>_<model>_<origin>_<destination>_<condition>.csv``)
  because the recording date exists only in the file name and is
  required to build timestamps.  The cleaning rule itself lives in
  ``cleaning_core.parse_filename``; this module only pre-checks it to
  return a user-readable error before the pipeline starts.
- The minimum-row limit follows the Model Layer input requirement of
  >= 700 contiguous 1 Hz rows per segment (INTERFACE.md section 1.5:
  512 context + 96 forecast + margin).  A raw file with fewer than
  700 rows can never produce a usable segment, so it is rejected at
  intake.  The definitive check remains segment-level downstream.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from data_layer.data_cleaning.src.cleaning_core import (
    CleaningError,
    normalize_column_name,
    parse_filename,
)


#: Minimum raw data rows for one upload (INTERFACE.md section 1.5).
MIN_UPLOAD_ROWS = 700

#: Example file name shown to users in rejection messages.
KIT_FILENAME_EXAMPLE = (
    "2019-05-06_Seat_Leon_Karlsruhe_Stuttgart_Normal.csv"
)

_VALID_REJECT_CODES = frozenset(
    {
        "bad_filename",
        "missing_columns",
        "too_few_rows",
        "unreadable_csv",
    }
)


class UploadRejected(RuntimeError):
    """A user upload failed intake validation.

    ``code`` is a stable machine-readable identifier so the Dashboard
    can branch on the failure kind:

    - ``bad_filename``: file name does not follow the KIT naming rule.
    - ``missing_columns``: required KIT source columns are absent.
    - ``too_few_rows``: fewer than :data:`MIN_UPLOAD_ROWS` data rows.
    - ``unreadable_csv``: the file could not be parsed as CSV at all.
    """

    def __init__(self, code: str, message: str) -> None:
        if code not in _VALID_REJECT_CODES:
            raise ValueError(f"Unknown upload rejection code: {code!r}")
        super().__init__(message)
        self.code = code


def required_source_columns(config: dict[str, Any]) -> dict[str, str]:
    """Map canonical field -> normalized accepted source column names.

    Returns one entry per canonical cleaning field plus the time
    source field, with every accepted raw header variant normalized
    through :func:`normalize_column_name` and joined by ``" | "`` for
    display.  Derived from the cleaning configuration so the intake
    check always matches what the cleaning stage will demand.
    """

    mapping: dict[str, str] = {
        "time": normalize_column_name(config["time"]["source_field"]),
    }
    for canonical, spec in config["fields"].items():
        variants = [
            normalize_column_name(name) for name in spec["source_names"]
        ]
        deduplicated = sorted(set(variants))
        mapping[canonical] = " | ".join(deduplicated)
    return mapping


def validate_kit_filename(file_name: str) -> None:
    """Reject file names that break the KIT naming rule (fail fast).

    Delegates the structural check to
    ``cleaning_core.parse_filename`` (single source of truth) and
    wraps its error in a user-readable :class:`UploadRejected`.
    """

    try:
        parse_filename(file_name)
    except CleaningError as exc:
        raise UploadRejected(
            "bad_filename",
            (
                "The uploaded file must keep its original KIT file "
                "name, because the recording date is read from the "
                "name itself. Expected a name like "
                f"'{KIT_FILENAME_EXAMPLE}' but received "
                f"'{Path(file_name).name}'. Please re-upload the "
                "file without renaming it."
            ),
        ) from exc


def _read_header_and_count(csv_path: Path) -> tuple[list[str], int]:
    """Return (header row, number of data rows) for one CSV file."""

    try:
        with csv_path.open(
            "r", encoding="utf-8-sig", errors="strict", newline=""
        ) as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                raise UploadRejected(
                    "unreadable_csv",
                    f"The uploaded file '{csv_path.name}' is empty.",
                ) from None
            row_count = sum(1 for _ in reader)
    except UploadRejected:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise UploadRejected(
            "unreadable_csv",
            (
                f"The uploaded file '{csv_path.name}' could not be "
                "read as a CSV file. Please export the original KIT "
                "OBD-II recording and try again."
            ),
        ) from exc
    return header, row_count


def validate_kit_columns(
    header: list[str], config: dict[str, Any]
) -> None:
    """Reject headers missing any required KIT source column."""

    normalized_header = {
        normalize_column_name(column) for column in header
    }
    missing: list[str] = []

    time_source = normalize_column_name(config["time"]["source_field"])
    if time_source not in normalized_header:
        missing.append(time_source)

    for spec in config["fields"].values():
        variants = {
            normalize_column_name(name)
            for name in spec["source_names"]
        }
        if not variants & normalized_header:
            missing.append(sorted(variants)[0])

    if missing:
        listed = ", ".join(f"'{name}'" for name in missing)
        raise UploadRejected(
            "missing_columns",
            (
                "The uploaded CSV does not follow the KIT OBD-II "
                f"column naming rules. Missing columns: {listed}. "
                "Please upload an unmodified KIT-format recording."
            ),
        )


def validate_row_count(
    row_count: int, *, minimum: int = MIN_UPLOAD_ROWS
) -> None:
    """Reject uploads with fewer than ``minimum`` data rows."""

    if row_count < minimum:
        raise UploadRejected(
            "too_few_rows",
            (
                f"The uploaded recording has {row_count} data rows, "
                f"but at least {minimum} rows (about 15 minutes of "
                "continuous driving) are required for a diagnosis. "
                "Please upload a longer recording."
            ),
        )


def validate_upload_csv(
    csv_path: str | Path, config: dict[str, Any]
) -> None:
    """Run all intake checks for one uploaded CSV, fail fast.

    Order: file existence -> KIT file name -> readable CSV header ->
    required KIT columns -> minimum row count.  Raises
    :class:`UploadRejected` on the first failure; returns ``None``
    when the upload passes intake.
    """

    path = Path(csv_path)
    if not path.is_file():
        raise UploadRejected(
            "unreadable_csv",
            f"The uploaded file was not found: {path}.",
        )
    validate_kit_filename(path.name)
    header, row_count = _read_header_and_count(path)
    validate_kit_columns(header, config)
    validate_row_count(row_count)
