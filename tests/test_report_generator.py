"""
Unit tests for report_layer/pipeline/report_generator.py [GL-246].

Uses unittest.mock to mock the Ollama API so the tests run without a
live Ollama instance.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

import requests

from report_layer.pipeline.report_generator import (
    _apply_signal_direction_check,
    call_ollama,
    generate_report,
)
from report_layer.pipeline.prompt_chain_validator import ValidationResult
from shared.interface_models import ModelLayerOutput


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


def test_signal_direction_check_blocks_reversed_coolant_comparison():
    payload = dict(VALID_MODEL_OUTPUT)
    payload["key_signals"] = [{
        "feature": "coolant_temp",
        "value": 84.0,
        "unit": "°C",
        "reference_range": [90.0, 95.0],
    }]
    result = _apply_signal_direction_check(
        ValidationResult(layer=1, passed=True, warnings=[], score=1.0),
        "The coolant temperature is higher than expected, so this pattern "
        "requires professional verification soon.",
        ModelLayerOutput(**payload),
    )

    assert result.score < 0.8
    assert any("below, not above" in item for item in result.warnings)

# Realistic enough to pass prompt_chain_validator.validate_chain() at
# VALIDATOR_SCORE_THRESHOLD — word-count minimums, hedging language,
# High-risk urgency wording. Placeholder-length text (e.g. "Visit a
# mechanic") now correctly gets blocked by the live validation gate,
# which is exactly the behavior the gate exists to test elsewhere; this
# fixture instead represents a realistic passing generation.
LAYER1_RESPONSE = json.dumps(
    {
        "anomaly_description": (
            "Your engine's coolant temperature is running higher than "
            "normal. The current reading is 102 degrees Celsius, while "
            "the expected range is 90 to 95 degrees. Because the risk "
            "level is High, this may need prompt attention soon to "
            "avoid further strain on the cooling system."
        )
    }
)
LAYER2_RESPONSE = json.dumps(
    {
        "possible_cause": (
            "This pattern may indicate a partially blocked radiator or "
            "a thermostat that is not fully opening, which could "
            "reduce how effectively the engine sheds heat."
        )
    }
)
LAYER3_RESPONSE = json.dumps(
    {
        "recommended_action": [
            "Now: Watch the temperature gauge and avoid unusual vehicle "
            "load while arranging an inspection.",
            "Service timing: Arrange a prompt professional inspection.",
            "Stop driving and seek help if: A red temperature warning "
            "appears, the engine overheats, or power drops.",
            "Tell the mechanic: Ask them to inspect the radiator, "
            "thermostat and coolant flow with suitable equipment.",
        ]
    }
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


class TestOllamaRequestOptions(unittest.TestCase):
    """test_call_ollama_requests_json — request deterministic JSON."""

    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_call_ollama_requests_json_mode(self, mock_post):
        mock_post.return_value = _make_mock_response("{}")

        response = call_ollama("Return JSON")

        self.assertEqual(response, "{}")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["format"], "json")
        self.assertEqual(kwargs["json"]["options"]["temperature"], 0)
        self.assertFalse(kwargs["json"]["stream"])


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


class TestGenerateReportValidationGate(unittest.TestCase):
    """Live validation corrects bad layers or falls back safely."""

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_low_quality_layer_is_corrected_before_next_layer(
        self, mock_post, mock_sleep
    ):
        low_quality_layer1 = json.dumps(
            {
                "anomaly_description": (
                    "coolant_temp is high and the cooling fan has failed."
                )
            }
        )
        corrected_layer1 = json.dumps(
            {
                "anomaly_description": (
                    "The engine coolant reading is higher than its expected "
                    "range during this driving period. This is evidence of "
                    "unusual cooling-system behaviour, but it does not "
                    "confirm that a specific component has failed. The High "
                    "risk level means the pattern needs prompt attention."
                )
            }
        )
        mock_post.side_effect = [
            _make_mock_response(low_quality_layer1),
            _make_mock_response(corrected_layer1),
            _make_mock_response(LAYER2_RESPONSE),
            _make_mock_response(LAYER3_RESPONSE),
        ]

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertIn(
            "does not confirm",
            result["anomaly_description"],
        )
        self.assertEqual(mock_post.call_count, 4)
        correction_prompt = mock_post.call_args_list[1].kwargs["json"][
            "prompt"
        ]
        self.assertIn("VALIDATOR FEEDBACK", correction_prompt)
        self.assertIn("unexplained raw field name", correction_prompt)
        self.assertNotIn(
            "coolant_temp",
            mock_post.call_args_list[2].kwargs["json"]["prompt"],
        )

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_layer2_correction_is_used_by_layer3(
        self, mock_post, mock_sleep
    ):
        unsafe_layer2 = json.dumps(
            {"possible_cause": "The thermostat is broken."}
        )
        corrected_layer2 = json.dumps(
            {
                "possible_cause": (
                    "This pattern could suggest restricted coolant flow or "
                    "a thermostat that is not opening fully. These remain "
                    "possible explanations rather than a confirmed fault."
                )
            }
        )
        mock_post.side_effect = [
            _make_mock_response(LAYER1_RESPONSE),
            _make_mock_response(unsafe_layer2),
            _make_mock_response(corrected_layer2),
            _make_mock_response(LAYER3_RESPONSE),
        ]

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertIn("could suggest", result["possible_cause"])
        layer3_prompt = mock_post.call_args_list[3].kwargs["json"]["prompt"]
        self.assertIn("could suggest", layer3_prompt)
        self.assertNotIn("The thermostat is broken", layer3_prompt)
        self.assertEqual(mock_post.call_count, 4)

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_layer3_actions_are_corrected_before_delivery(
        self, mock_post, mock_sleep
    ):
        unsafe_layer3 = json.dumps(
            {"recommended_action": ["Check it", "Keep driving"]}
        )
        corrected_layer3 = json.dumps(
            {
                "recommended_action": [
                    "Now: Watch the temperature gauge and avoid unusual "
                    "vehicle load while arranging an inspection.",
                    "Service timing: Arrange a prompt cooling-system "
                    "inspection.",
                    "Stop driving and seek help if: A red temperature "
                    "warning appears, the engine overheats, or power drops.",
                    "Tell the mechanic: Ask them to inspect the radiator, "
                    "thermostat and coolant flow with suitable equipment.",
                ]
            }
        )
        mock_post.side_effect = [
            _make_mock_response(LAYER1_RESPONSE),
            _make_mock_response(LAYER2_RESPONSE),
            _make_mock_response(unsafe_layer3),
            _make_mock_response(corrected_layer3),
        ]

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertEqual(len(result["recommended_action"]), 4)
        self.assertTrue(result["recommended_action"][0].startswith("Now:"))
        self.assertEqual(mock_post.call_count, 4)

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_low_quality_output_falls_back(
        self, mock_post, mock_sleep
    ):
        # A semantic correction is attempted once. If the corrected value
        # still scores below the threshold, the report must fall back before
        # any downstream layer is generated.
        low_quality_layer1 = json.dumps(
            {
                "anomaly_description": (
                    "coolant_temp is high and the cooling fan has failed."
                )
            }
        )
        mock_post.side_effect = [
            _make_mock_response(low_quality_layer1),
            _make_mock_response(low_quality_layer1),
        ]

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertIsInstance(result, dict)
        self.assertNotIn("report_generation_success", result)
        self.assertEqual(result["anomaly_description"], "")
        self.assertEqual(result["possible_cause"], "")
        self.assertEqual(result["recommended_action"], [])
        self.assertEqual(mock_post.call_count, 2)

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_score_exactly_at_threshold_is_not_blocked(
        self, mock_post, mock_sleep
    ):
        # A score of exactly VALIDATOR_SCORE_THRESHOLD (0.8) is the
        # single most common real case — 20-40% of real generated
        # reports land here (one flagged issue on one layer). The gate
        # must use a strict "<" comparison, not "<=": this is the
        # boundary an off-by-one change would silently break, blocking
        # a large share of otherwise-normal reports.
        at_threshold_layer1 = json.dumps(
            {
                "anomaly_description": (
                    "Your engine coolant_temp reading is running higher "
                    "than normal. The current reading is 102 degrees "
                    "Celsius, while the expected range is 90 to 95 "
                    "degrees. Because the risk level is High, this may "
                    "need prompt attention soon to avoid further strain "
                    "on the cooling system."
                )
            }
        )
        mock_post.side_effect = [
            _make_mock_response(at_threshold_layer1),
            _make_mock_response(LAYER2_RESPONSE),
            _make_mock_response(LAYER3_RESPONSE),
        ]

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertTrue(len(result["anomaly_description"]) > 0)
        self.assertTrue(len(result["possible_cause"]) > 0)
        self.assertGreater(len(result["recommended_action"]), 0)
        self.assertEqual(mock_post.call_count, 3)

    @patch(
        "report_layer.pipeline.report_generator.time.sleep"
    )
    @patch(
        "report_layer.pipeline.report_generator.requests.post"
    )
    def test_passing_quality_output_is_not_blocked(
        self, mock_post, mock_sleep
    ):
        # Sanity check in the other direction: realistic text at or
        # above the threshold must reach the owner, not be discarded.
        mock_post.side_effect = [
            _make_mock_response(LAYER1_RESPONSE),
            _make_mock_response(LAYER2_RESPONSE),
            _make_mock_response(LAYER3_RESPONSE),
        ]

        result = generate_report(VALID_MODEL_OUTPUT)

        self.assertTrue(len(result["anomaly_description"]) > 0)
        self.assertTrue(len(result["possible_cause"]) > 0)
        self.assertGreater(len(result["recommended_action"]), 0)


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
