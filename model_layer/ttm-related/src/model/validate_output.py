"""
Validate Model Layer output JSON against INTERFACE.md v0.5.

This script checks the output contract only: required fields, JSON
types, enum values, and interface-level numeric ranges. It does not
judge whether a vehicle signal is healthy or anomalous.

Run from the repository root:
    ttm-related/venv/bin/python ttm-related/src/model/validate_output.py \
        ttm-related/outputs/kit_residual_sample.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = [
    "timestamp",
    "anomaly_type",
    "risk_score",
    "risk_level",
    "component",
    "prediction_confidence",
    "key_signals",
    "estimated_cycles_to_failure",
    "estimated_failure_probability",
    "notes",
]

ALLOWED_ANOMALY_TYPES = {
    "cooling_degradation",
    "air_intake_maf_anomaly",
    "accelerator_pedal_sensor",
    "intake_air_temperature_sensor_or_heat_soak_fault",
    "map_load_signal_plausibility_fault",
    "electronic_throttle_tracking_fault",
    "idle_speed_control_or_surge_degradation",
}

ALLOWED_RISK_LEVELS = {"Low", "Medium", "High"}


def is_number(value: Any) -> bool:
    """Return True for int/float values, excluding bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_non_negative_int(value: Any) -> bool:
    """Return True for non-negative integers, excluding bool."""
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    )


def validate_timestamp(value: Any) -> list[str]:
    if not isinstance(value, str):
        return ["timestamp must be a string"]
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return ["timestamp must be ISO 8601 parseable"]
    return []


def validate_key_signals(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return ["key_signals must be a list"]

    for index, item in enumerate(value):
        prefix = f"key_signals[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be an object")
            continue

        for field in ("feature", "value", "unit", "reference_range"):
            if field not in item:
                errors.append(f"{prefix} missing required field: {field}")

        if "feature" in item and not isinstance(item["feature"], str):
            errors.append(f"{prefix}.feature must be a string")
        if "value" in item and not is_number(item["value"]):
            errors.append(f"{prefix}.value must be a number")
        if "unit" in item and not isinstance(item["unit"], str):
            errors.append(f"{prefix}.unit must be a string")

        if "reference_range" in item:
            reference_range = item["reference_range"]
            if not isinstance(reference_range, list):
                errors.append(f"{prefix}.reference_range must be a list")
            elif len(reference_range) != 2:
                errors.append(
                    f"{prefix}.reference_range must contain exactly 2 values"
                )
            else:
                low, high = reference_range
                if not is_number(low) or not is_number(high):
                    errors.append(
                        f"{prefix}.reference_range values must be numbers"
                    )
                elif low > high:
                    errors.append(
                        f"{prefix}.reference_range lower bound "
                        "exceeds upper bound"
                    )

    return errors


def validate_notes(value: Any) -> list[str]:
    if not isinstance(value, list):
        return ["notes must be a list"]
    errors = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(f"notes[{index}] must be a string")
    return errors


def validate_output(data: Any) -> list[str]:
    """Return validation errors. Empty list means valid."""
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["top-level JSON value must be an object"]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"missing required field: {field}")

    # Continue only with present fields so one bad file can report all issues.
    if "timestamp" in data:
        errors.extend(validate_timestamp(data["timestamp"]))

    if "anomaly_type" in data:
        anomaly_type = data["anomaly_type"]
        if not isinstance(anomaly_type, str):
            errors.append("anomaly_type must be a string")
        elif anomaly_type not in ALLOWED_ANOMALY_TYPES:
            errors.append(f"anomaly_type is not allowed: {anomaly_type}")

    if "risk_score" in data:
        risk_score = data["risk_score"]
        if not is_number(risk_score):
            errors.append("risk_score must be a number")
        elif not 0.0 <= risk_score <= 1.0:
            errors.append("risk_score must be between 0 and 1")

    if "risk_level" in data:
        risk_level = data["risk_level"]
        if not isinstance(risk_level, str):
            errors.append("risk_level must be a string")
        elif risk_level not in ALLOWED_RISK_LEVELS:
            errors.append(f"risk_level is not allowed: {risk_level}")

    if "component" in data:
        component = data["component"]
        if not isinstance(component, str):
            errors.append("component must be a string")
        elif "anomaly_type" in data and component != data["anomaly_type"]:
            errors.append("component must equal anomaly_type")

    if "prediction_confidence" in data:
        confidence = data["prediction_confidence"]
        if not is_number(confidence):
            errors.append("prediction_confidence must be a number")
        elif not 0.0 <= confidence <= 1.0:
            errors.append("prediction_confidence must be between 0 and 1")

    if "key_signals" in data:
        errors.extend(validate_key_signals(data["key_signals"]))

    if "estimated_cycles_to_failure" in data:
        cycles = data["estimated_cycles_to_failure"]
        if cycles is not None and not is_non_negative_int(cycles):
            errors.append(
                "estimated_cycles_to_failure must be null "
                "or a non-negative integer"
            )

    if "estimated_failure_probability" in data:
        probability = data["estimated_failure_probability"]
        if probability is not None:
            if not is_number(probability):
                errors.append(
                    "estimated_failure_probability must be null or a number"
                )
            elif not 0.0 <= probability <= 1.0:
                errors.append(
                    "estimated_failure_probability must be null "
                    "or between 0 and 1"
                )

    if "notes" in data:
        errors.extend(validate_notes(data["notes"]))

    return errors


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    if not path.exists():
        return None, [f"file does not exist: {path}"]
    try:
        return json.loads(path.read_text()), []
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {exc.msg} at line {exc.lineno}"]


def validate_file(path: Path) -> list[str]:
    data, errors = load_json(path)
    if errors:
        return errors
    return validate_output(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate Model Layer output JSON against INTERFACE.md v0.5."
        )
    )
    parser.add_argument(
        "json_path", type=Path, help="Path to output JSON file"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    errors = validate_file(args.json_path)

    if errors:
        print("FAIL: output JSON does not match INTERFACE.md v0.5")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("PASS: output JSON matches INTERFACE.md v0.5")


if __name__ == "__main__":
    main()
