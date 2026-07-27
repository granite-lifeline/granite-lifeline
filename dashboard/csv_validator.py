"""GL-257: Validation helpers for uploaded OBD-II CSV files.

Validates that a DataFrame parsed from an uploaded CSV file contains
the required raw OBD-II column headers and sufficient rows before the
file is handed to the data pipeline.
"""

from __future__ import annotations

import pandas as pd

# Canonical column names required by the cleaning pipeline.
# The encoding variant [Â°C] is accepted as an alias for [°C].
REQUIRED_COLUMNS: list[str] = [
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

# Map encoding-corrupt variants to their canonical names so that files
# saved with a mis-detected BOM still pass validation.
_ENCODING_ALIASES: dict[str, str] = {
    col.replace("°", "\u00c2\u00b0"): col
    for col in REQUIRED_COLUMNS
    if "°" in col
}


def _normalise_column(name: str) -> str:
    """Return the canonical column name, resolving encoding aliases."""
    return _ENCODING_ALIASES.get(name, name)


def validate_csv_columns(
    df: pd.DataFrame,
) -> tuple[bool, list[str]]:
    """Check that *df* contains all required raw OBD-II columns.

    Encoding variants such as ``[Â°C]`` are accepted as aliases for
    the canonical ``[°C]`` spelling.

    Parameters
    ----------
    df:
        DataFrame parsed from the uploaded CSV.

    Returns
    -------
    tuple[bool, list[str]]
        ``(True, [])`` when all required columns are present.
        ``(False, missing)`` where *missing* lists the canonical names
        of any absent columns.
    """
    normalised = {_normalise_column(c) for c in df.columns}
    missing = [col for col in REQUIRED_COLUMNS if col not in normalised]
    return (len(missing) == 0, missing)


def validate_csv_min_rows(
    df: pd.DataFrame,
    min_rows: int = 700,
) -> bool:
    """Return ``True`` if *df* has at least *min_rows* data rows.

    Parameters
    ----------
    df:
        DataFrame parsed from the uploaded CSV.
    min_rows:
        Minimum acceptable row count (default 700).

    Returns
    -------
    bool
        ``True`` when ``len(df) >= min_rows``, ``False`` otherwise.
    """
    return len(df) >= min_rows
