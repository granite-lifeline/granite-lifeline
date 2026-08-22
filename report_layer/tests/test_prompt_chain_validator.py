"""Focused tests for cross-layer prompt-chain validation."""

from report_layer.pipeline.prompt_chain_validator import validate_layer2


def test_layer2_blocks_substantial_copy_from_layer1() -> None:
    layer1 = (
        "The coolant temperature stayed above its usual range while the "
        "vehicle was moving under similar engine load during this journey."
    )
    layer2 = (
        "The coolant temperature stayed above its usual range while the "
        "vehicle was moving under similar engine load during this journey. "
        "This could suggest restricted coolant flow or a thermostat issue, "
        "although the data cannot confirm a mechanical fault."
    )

    result = validate_layer2(layer2, layer1)

    assert result.score == 0.6
    assert any("Substantially repeats" in warning for warning in result.warnings)


def test_layer2_allows_shared_evidence_without_copying_description() -> None:
    layer1 = (
        "Coolant temperature remained higher than its usual range while "
        "engine load was broadly stable during the journey."
    )
    layer2 = (
        "This pattern could suggest reduced cooling efficiency, such as "
        "restricted coolant flow or a thermostat issue. The temperature and "
        "engine-load evidence alone cannot confirm which cause is present."
    )

    result = validate_layer2(layer2, layer1)

    assert not any(
        "Substantially repeats" in warning for warning in result.warnings
    )


def test_layer2_skips_repetition_check_when_layer1_is_empty() -> None:
    layer2 = (
        "This pattern could suggest reduced cooling efficiency, but the "
        "available signals cannot confirm a particular mechanical cause."
    )

    result = validate_layer2(layer2, "")

    assert not any(
        "Substantially repeats" in warning for warning in result.warnings
    )
