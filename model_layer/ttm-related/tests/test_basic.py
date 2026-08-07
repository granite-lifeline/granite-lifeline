"""
Basic tests to verify setup is working
"""

import sys
from pathlib import Path

import pytest

# CWD-independent: append this file's own src/ directory, not a path
# relative to wherever the process happened to be launched from. The
# original `sys.path.append('src')` only resolved when pytest was
# invoked with model_layer/ttm-related/ as the working directory —
# running it as part of the repo-wide `pytest` from the root (as CI
# does) silently failed to find the `model` package, a second real
# bug the old return-based tests were also masking.
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))


def test_imports():
    """Test that all required libraries can be imported"""
    print("Testing imports...")

    import numpy  # noqa: F401
    print("  ✅ numpy")

    import pandas  # noqa: F401
    print("  ✅ pandas")

    import torch  # noqa: F401
    print("  ✅ torch")

    from transformers import AutoModel  # noqa: F401
    print("  ✅ transformers")

    print("\n✅ All imports successful!")


def test_data_simulator():
    """Test that data simulator works"""
    print("\nTesting data simulator...")

    from model.data_simulator import OBDDataSimulator

    simulator = OBDDataSimulator(sequence_length=10)
    data = simulator.generate_normal_sequence()

    assert len(data) == 10, "Wrong sequence length"
    assert 'rpm' in data.columns, "Missing RPM column"
    assert 'coolant_temp' in data.columns, "Missing temp column"

    fault = simulator.generate_air_intake_maf_anomaly()
    assert len(fault) == 10, "Wrong fault sequence length"

    print("  ✅ Data simulator working")


@pytest.mark.model_download
def test_model_loading():
    """
    Test that TTM model can be loaded.

    Marked model_download: on a cold cache this makes a real network
    call to the Hugging Face Hub, so it is not run by default in CI
    (see .github/workflows/ci.yml). Run explicitly with
    `pytest -m model_download` to include it.
    """
    print("\nTesting model loading...")

    from tsfm_public.toolkit.get_model import get_model

    get_model(
        "ibm-granite/granite-timeseries-ttm-r2",
        context_length=512,
        prediction_length=96,
    )

    print("  ✅ Model loaded from cache")


if __name__ == "__main__":
    print("=" * 50)
    print("Running Basic Tests")
    print("=" * 50)

    checks = [
        ("Imports", test_imports),
        ("Data Simulator", test_data_simulator),
        ("Model Loading", test_model_loading),
    ]

    results = []
    for name, check in checks:
        try:
            check()
            results.append((name, True))
        except Exception as e:
            print(f"  ❌ {name} failed: {e}")
            if name == "Model Loading":
                print("     Run: python src/model/download_ttm.py")
            results.append((name, False))

    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed! You're ready to start coding!")
    else:
        print("\n⚠️  Some tests failed. Fix them before proceeding.")
