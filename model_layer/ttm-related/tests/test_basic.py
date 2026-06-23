"""
Basic tests to verify setup is working
"""

import sys
sys.path.append('src')

def test_imports():
    """Test that all required libraries can be imported"""
    print("Testing imports...")
    
    try:
        import numpy as np
        print("  ✅ numpy")
        
        import pandas as pd
        print("  ✅ pandas")
        
        import torch
        print("  ✅ torch")
        
        from transformers import AutoModel
        print("  ✅ transformers")
        
        print("\n✅ All imports successful!")
        return True
        
    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        return False

def test_data_simulator():
    """Test that data simulator works"""
    print("\nTesting data simulator...")
    
    try:
        from model.data_simulator import OBDDataSimulator
        
        simulator = OBDDataSimulator(sequence_length=10)
        data = simulator.generate_normal_sequence()
        
        assert len(data) == 10, "Wrong sequence length"
        assert 'engine_rpm' in data.columns, "Missing RPM column"
        assert 'coolant_temp_c' in data.columns, "Missing temp column"
        
        print("  ✅ Data simulator working")
        return True
        
    except Exception as e:
        print(f"  ❌ Data simulator failed: {e}")
        return False

def test_model_loading():
    """Test that TTM model can be loaded"""
    print("\nTesting model loading...")
    
    try:
        from tsfm_public.toolkit.get_model import get_model

        model = get_model(
            "ibm-granite/granite-timeseries-ttm-r2",
            context_length=512,
            prediction_length=96,
         )
        
        print("  ✅ Model loaded from cache")
        return True
        
    except Exception as e:
        print(f"  ❌ Model loading failed: {e}")
        print("     Run: python src/model/download_ttm.py")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Running Basic Tests")
    print("=" * 50)
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Data Simulator", test_data_simulator()))
    results.append(("Model Loading", test_model_loading()))
    
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
