import importlib.util
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "report_layer/evaluation/v5-rag-final-ablation"
    / "run_final_rag_ablation.py"
)
SPEC = importlib.util.spec_from_file_location(
    "final_rag_ablation", SCRIPT_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def _context() -> dict:
    return {
        "context": "Risk Level: Medium",
        "fault_knowledge": "",
        "actions_knowledge": "",
    }


def test_audit_does_not_flag_negated_disassembly_statement():
    report = {
        "anomaly_description": "An unusual pedal pattern was detected.",
        "possible_cause": "The cause remains uncertain.",
        "recommended_action": [
            "Now: Observe whether the pedal feels normal. No tools or "
            "disassembly are needed.",
            "Service timing: Arrange a professional inspection soon.",
            "Stop driving and seek help if: Acceleration becomes unsafe.",
            "Tell the mechanic: Inspect the sensor wiring and connectors.",
        ],
    }

    audit = MODULE._automatic_audit(
        report, _context(), "accelerator_pedal_sensor"
    )

    assert audit["unsafe_owner_actions"] == []


def test_audit_flags_owner_disassembly_instruction():
    report = {
        "anomaly_description": "An unusual pedal pattern was detected.",
        "possible_cause": "The cause remains uncertain.",
        "recommended_action": [
            "Now: Disassemble the pedal sensor and inspect the connector.",
            "Service timing: Arrange a professional inspection soon.",
            "Stop driving and seek help if: Acceleration becomes unsafe.",
            "Tell the mechanic: Verify the reported pedal evidence.",
        ],
    }

    audit = MODULE._automatic_audit(
        report, _context(), "accelerator_pedal_sensor"
    )

    assert len(audit["unsafe_owner_actions"]) == 1
