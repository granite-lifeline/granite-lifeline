"""
Unit tests for report_layer/pipeline/report_generator.py [GL-246].

Uses unittest.mock to mock the Ollama API so the tests run without a
live Ollama instance.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

import requests

from report_layer.pipeline.report_generator import generate_report


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

VALID_MODEL_OUTPUT = {
    "timestamp": "2026-06-20T14:32:15Z",
    "anomaly_type": "cooling_degradation",
    "risk_score": 0.82,
    "risk_level": "High",
    "component": "cooling_degradation",
    "prediction_confidence": 0.87,
    "key_signals": [
        {
            "feature": "coolant_temp",
            "value": 102.0,
            "unit": "°C",
            "reference_range": [90.0, 95.0],
        }
    ],
    "estimated_cycles_to_failure": 15,
    "estimated_failure_probability": 0.72,
    "notes": [],
}

LAYER1_RESPONSE = json.dumps(
    {"anomaly_description": "Engine coolant temperature is elevated."}
)
LAYER2_RESPONSE = json.dumps(
    {"possible_cause": "Possible thermostat or coolant system issue."}
)
LAYER3_RESPONSE = json.dumps(
    {"recommended_action": ["Visit a mechanic", "Monitor temperature"]}
)

PASS_THROUGH_FIELDS = [
    "timestamp",
    "risk_score",
    "risk_level",
    "component",
    "prediction_confidence",
    "key_signals",
    "estimated_cycles_to_failure",
    "estimated_failure_probability",
    "notes",
]


def _make_mock_response(text: str) -> MagicMock:
    """Return a mock requests.Response whose .json() yields the text."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"response": text}
    return mock_resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGenerateReportSuccess(unittest.TestCase):
    """test_generate_report_success — full pipeline succeeds."""

    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_generate_report_success(self, mock_post):
        mock_post.side_effect = [
            _make_mock_response(LAYER1_RESPONSE),
            _make_mock_response(LAYER2_RESPONSE),
            _make_mock_response(LAYER3_RESPONSE),
        ]

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertIsInstance(result, dict)
        self.assertNotIn("report_generation_success", result)
        self.assertTrue(len(result["anomaly_description"]) > 0)
        self.assertTrue(len(result["possible_cause"]) > 0)
        self.assertIsInstance(result["recommended_action"], list)
        self.assertGreater(len(result["recommended_action"]), 0)


class TestGenerateReportOllamaTimeout(unittest.TestCase):
    """test_generate_report_ollama_timeout — Timeout activates fallback."""

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_generate_report_ollama_timeout(
        self, mock_post, mock_sleep
    ):
        mock_post.side_effect = requests.Timeout("timed out")

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertIsInstance(result, dict)
        self.assertNotIn("report_generation_success", result)
        self.assertEqual(result["anomaly_description"], "")
        self.assertEqual(result["possible_cause"], "")
        self.assertEqual(result["recommended_action"], [])


class TestGenerateReportJsonParseFailure(unittest.TestCase):
    """test_generate_report_json_parse_failure — bad JSON → fallback."""

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_generate_report_json_parse_failure(
        self, mock_post, mock_sleep
    ):
        # Return unparseable text for every call
        mock_post.side_effect = [
            _make_mock_response("this is not json"),
            _make_mock_response("this is not json"),
            _make_mock_response("this is not json"),
        ]

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertIsInstance(result, dict)
        self.assertNotIn("report_generation_success", result)
        self.assertEqual(result["anomaly_description"], "")
        self.assertEqual(result["possible_cause"], "")
        self.assertEqual(result["recommended_action"], [])


class TestGenerateReportInvalidInput(unittest.TestCase):
    """test_generate_report_invalid_input — missing fields → fallback."""

    def test_generate_report_invalid_input(self):
        # Dict with completely missing required fields
        bad_input = {"notes": []}

        result = generate_report(bad_input)

        self.assertIsInstance(result, dict)
        self.assertNotIn("report_generation_success", result)


class TestGenerateReportPassthroughFields(unittest.TestCase):
    """test_generate_report_passthrough_fields — fields present always."""

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_passthrough_fields_on_success(
        self, mock_post, mock_sleep
    ):
        mock_post.side_effect = [
            _make_mock_response(LAYER1_RESPONSE),
            _make_mock_response(LAYER2_RESPONSE),
            _make_mock_response(LAYER3_RESPONSE),
        ]
        result = generate_report(VALID_MODEL_OUTPUT)

        for field in PASS_THROUGH_FIELDS:
            self.assertIn(
                field, result,
                msg=f"Missing pass-through field on success: {field}",
            )

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_passthrough_fields_on_fallback(
        self, mock_post, mock_sleep
    ):
        mock_post.side_effect = requests.Timeout("timed out")
        result = generate_report(VALID_MODEL_OUTPUT)

        for field in PASS_THROUGH_FIELDS:
            self.assertIn(
                field, result,
                msg=(
                    f"Missing pass-through field on fallback: {field}"
                ),
            )

        # Verify actual values are preserved on fallback
        self.assertEqual(
            result["timestamp"], VALID_MODEL_OUTPUT["timestamp"]
        )
        self.assertEqual(
            result["risk_score"], VALID_MODEL_OUTPUT["risk_score"]
        )
        self.assertEqual(
            result["component"], VALID_MODEL_OUTPUT["component"]
        )
        self.assertEqual(
            result["estimated_cycles_to_failure"],
            VALID_MODEL_OUTPUT["estimated_cycles_to_failure"],
        )
        self.assertEqual(
            result["estimated_failure_probability"],
            VALID_MODEL_OUTPUT["estimated_failure_probability"],
        )


if __name__ == "__main__":
    unittest.main()
