"""
Download IBM Granite TTM model from Hugging Face
This only needs to be run once - the model will be cached locally
"""
MODEL_PATH = "ibm-granite/granite-timeseries-ttm-r2"
CONTEXT_LENGTH = 512
PREDICTION_LENGTH = 96

def _dependency_help(import_error):
    import sys

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    message = (
        "Could not import IBM's TTM loader: tsfm_public.toolkit.get_model.\n"
        f"   Python executable: {sys.executable}\n"
        f"   Python version: {python_version}\n"
        "   Fix: use Python 3.11, 3.12, or 3.13, then install granite-tsfm.\n"
        "   Example:\n"
        "     deactivate\n"
        "     python3.13 -m venv venv\n"
        "     source venv/bin/activate\n"
        "     python -m pip install --upgrade pip\n"
        "     python -m pip install granite-tsfm torch\n"
        "     python src/model/download_ttm.py"
    )
    raise ImportError(message) from import_error

def download_ttm_model():
    """Download and cache TTM model"""
    print("📥 Downloading IBM Granite TTM model...")
    print("   This may take 5-10 minutes on first run...")
    print("   Model size: small TTM checkpoint (about 1M parameters)")
    
    try:
        try:
            from tsfm_public.toolkit.get_model import get_model
        except ImportError as import_error:
            _dependency_help(import_error)

        try:
            import torch
        except ImportError as import_error:
            raise ImportError(
                "PyTorch is required to run the TTM model. "
                "Install it with: pip install torch"
            ) from import_error

        # The TTM R2 Hugging Face repository contains several model revisions.
        # get_model selects a compatible checkpoint revision for this context and horizon.
        model = get_model(
            MODEL_PATH,
            context_length=CONTEXT_LENGTH,
            prediction_length=PREDICTION_LENGTH,
        )
        
        print("\n✅ Model downloaded successfully!")
        print(f"   Model type: {type(model)}")
        print(f"   Context length: {model.config.context_length}")
        print(f"   Prediction length: {model.config.prediction_length}")
        print(f"   Parameters: {sum(p.numel() for p in model.parameters()):,}")
        
        # Test that model can be used
        print("\n🧪 Testing model...")
        model.eval()
        
        # Minimal sanity-check input: raw channels only
        # Note: the full pipeline (ttm_inference.py) will use 8 channels (5 raw + 3 derived
        # features) per the Architecture Diagram. This 5-channel input here is just to
        # confirm the model loads and runs, not the final pipeline shape.
        dummy_input = torch.randn(1, model.config.context_length, 5)
        
        with torch.no_grad():
            output = model(past_values=dummy_input)
        
        print(f"   Input shape: {dummy_input.shape}")
        print(f"   Prediction shape: {output.prediction_outputs.shape}")
        print("\n✅ Model test passed!")
        
        return model
        
    except Exception as e:
        print(f"\n❌ Error downloading model: {e}")
        print("\nTroubleshooting:")
        print("1. Use Python 3.11, 3.12, or 3.13 for the virtual environment")
        print("2. Install IBM's TTM package: python -m pip install granite-tsfm")
        print("3. Try: huggingface-cli login (may need free account)")
        return None

if __name__ == "__main__":
    model = download_ttm_model()
