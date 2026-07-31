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
from datetime import datetime
from pathlib import Path
from typing import Any

from data_layer.data_cleaning.src.cleaning_core import (
    CleaningError,
    normalize_column_name,
    parse_filename,
)


#: Minimum raw data rows for one upload (cheap sanity floor).
MIN_UPLOAD_ROWS = 700

#: Minimum recording duration in seconds.  This carries the actual
#: "about 15 minutes of driving" semantics: KIT raw files are sampled
#: at 6-12 Hz (non-uniform across the corpus), so a raw row count
#: cannot express a duration requirement.  700 s mirrors the >= 700
#: cleaned 1 Hz rows the Model Layer needs (INTERFACE.md section 1.5).
MIN_UPLOAD_DURATION_S = 700.0

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
        "no_usable_segment",
    }
)


class UploadRejected(RuntimeError):
    """A user upload failed intake validation.

    ``code`` is a stable machine-readable identifier so the Dashboard
    can branch on the failure kind:

    - ``bad_filename``: file name does not follow the KIT naming rule.
    - ``missing_columns``: required KIT source columns are absent.
    - ``too_few_rows``: fewer than :data:`MIN_UPLOAD_ROWS` data rows,
      or a recording shorter than :data:`MIN_UPLOAD_DURATION_S`.
    - ``unreadable_csv``: the file could not be parsed as CSV at all.
    - ``no_usable_segment``: raised after the pipeline has run, when
      no contiguous cleaned segment reaches
      :data:`MIN_UPLOAD_ROWS` rows (e.g. a fragmented recording).
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


def _read_header_only(csv_path: Path) -> list[str]:
    """Return just the header row, so the time column can be located."""

    header, _, _, _ = _read_header_and_count(csv_path, header_only=True)
    return header


def _read_header_and_count(
    csv_path: Path,
    *,
    time_index: int | None = None,
    header_only: bool = False,
) -> tuple[list[str], int, str | None, str | None]:
    """Return (header, data-row count, first time, last time).

    ``time_index`` selects the column read for the first/last time
    values; both are ``None`` when it is omitted or the column is
    absent from a row.
    """

    first_time: str | None = None
    last_time: str | None = None
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
            row_count = 0
            for row in [] if header_only else reader:
                if not row:
                    continue
                row_count += 1
                if time_index is not None and len(row) > time_index:
                    value = row[time_index].strip()
                    if value:
                        if first_time is None:
                            first_time = value
                        last_time = value
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
    return header, row_count, first_time, last_time


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


def _time_column_index(
    header: list[str], config: dict[str, Any]
) -> int | None:
    """Locate the raw time column in a validated KIT header."""

    wanted = normalize_column_name(config["time"]["source_field"])
    for index, column in enumerate(header):
        if normalize_column_name(column) == wanted:
            return index
    return None


def validate_duration(
    first_time: str | None,
    last_time: str | None,
    config: dict[str, Any],
    *,
    minimum_seconds: float = MIN_UPLOAD_DURATION_S,
) -> None:
    """Reject recordings shorter than ``minimum_seconds``.

    Unparsable or missing time values are not treated as a rejection:
    the cleaning stage owns timestamp validation and reports it with
    full context.  This check only screens out recordings that are
    clearly too short to yield a usable segment.
    """

    if not first_time or not last_time:
        return
    time_format = config["time"]["source_format"]
    try:
        start = datetime.strptime(first_time, time_format)
        end = datetime.strptime(last_time, time_format)
    except (ValueError, TypeError):
        return
    duration = (end - start).total_seconds()
    if duration < 0.0:            # recording crossed midnight
        duration += 86400.0
    if duration < minimum_seconds:
        raise UploadRejected(
            "too_few_rows",
            (
                f"The uploaded recording covers {duration:.0f} seconds "
                f"of driving, but at least {minimum_seconds:.0f} "
                "seconds (about 15 minutes) of continuous driving are "
                "required for a diagnosis. Please upload a longer "
                "recording."
            ),
        )


def longest_segment_rows(production_features_path: str | Path) -> int:
    """Return the row count of the longest cleaned ``segment_id``.

    Read with the standard-library CSV reader so this module keeps its
    lightweight dependencies; ``segment_id`` already encodes
    contiguity, so counting rows per segment is sufficient.
    """

    path = Path(production_features_path)
    counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            segment = row.get("segment_id")
            if segment:
                counts[segment] = counts.get(segment, 0) + 1
    return max(counts.values(), default=0)


def validate_usable_segment(
    production_features_path: str | Path,
    *,
    minimum: int = MIN_UPLOAD_ROWS,
    run_id: str | None = None,
) -> None:
    """Reject a completed run with no long enough contiguous segment.

    The Model Layer needs at least ``minimum`` contiguous cleaned 1 Hz
    rows within one ``segment_id``, because forecast windows never
    cross a recording break.  A recording can satisfy every intake
    check and still fail here when it is fragmented into short pieces,
    so this is the authoritative check and it can only run after
    cleaning.
    """

    longest = longest_segment_rows(production_features_path)
    if longest < minimum:
        location = f" (run '{run_id}')" if run_id else ""
        raise UploadRejected(
            "no_usable_segment",
            (
                "The uploaded recording was processed, but its longest "
                f"uninterrupted stretch is only {longest} seconds long, "
                f"while at least {minimum} seconds are required for a "
                "diagnosis. This usually means the recording was "
                f"repeatedly interrupted{location}. Please upload a "
                "recording with a longer continuous drive."
            ),
        )


def validate_upload_csv(
    csv_path: str | Path, config: dict[str, Any]
) -> None:
    """Run all pre-run intake checks for one uploaded CSV, fail fast.

    Order: file existence -> KIT file name -> readable CSV header ->
    required KIT columns -> minimum row count -> minimum duration.
    Raises :class:`UploadRejected` on the first failure; returns
    ``None`` when the upload passes intake.  The segment-level
    requirement is enforced separately by
    :func:`validate_usable_segment` once cleaning has run.
    """

    path = Path(csv_path)
    if not path.is_file():
        raise UploadRejected(
            "unreadable_csv",
            f"The uploaded file was not found: {path}.",
        )
    validate_kit_filename(path.name)
    header = _read_header_only(path)
    validate_kit_columns(header, config)
    _, row_count, first_time, last_time = _read_header_and_count(
        path, time_index=_time_column_index(header, config)
    )
    validate_row_count(row_count)
    validate_duration(first_time, last_time, config)
