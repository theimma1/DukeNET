#!/usr/bin/env python3
"""
Duke Model Diagnostic Tool - Enhanced Version
Checks Duke checkpoint files and provides detailed status,
including compatibility with SimpleDukeModel vs EnhancedDukeModel.
"""

import torch
import pickle
from pathlib import Path
import sys
import logging

# Set up logger (mainly for future extensions; current script prints to stdout)
logger = logging.getLogger("duke_diagnostic")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Dummy classes for unpickling legacy objects (if needed)
class TextEmbedder:
    pass

class ResponseGenerator:
    pass

class SimpleDukeModel:
    """Placeholder: used only for compatibility reporting in this script."""
    pass

class EnhancedDukeModel:
    """Placeholder: used only for compatibility reporting in this script."""
    pass

# Make them available for pickle
sys.modules['__main__'].TextEmbedder = TextEmbedder
sys.modules['__main__'].ResponseGenerator = ResponseGenerator


def check_files():
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║            DUKE MODEL DIAGNOSTIC TOOL                         ║")
    print("╚════════════════════════════════════════════════════════════════╝")

    checkpoint_dir = Path("duke_checkpoints")

    print("🔍 CHECKING DUKE FILES")
    print("=" * 60)

    files = {
        "model": "duke_model.pth",
        "embedder": "duke_embedder.pkl",
        "generator": "duke_responses.pkl",  # duke_generator.pkl → duke_responses.pkl
    }

    file_status = {}
    for name, filename in files.items():
        filepath = checkpoint_dir / filename
        if filepath.exists():
            size = filepath.stat().st_size
            file_status[name] = {"exists": True, "size": size, "path": filepath}
            print(f"✅ {name:12}: {filename} ({size:,} bytes)")
        else:
            file_status[name] = {"exists": False}
            print(f"❌ {name:12}: MISSING")

    # Check model architecture
    if file_status["model"]["exists"]:
        print("\n🧠 INSPECTING DUKE MODEL")
        print("=" * 60)
        try:
            model_state = torch.load(file_status["model"]["path"], map_location="cpu")
            print("Model Architecture:")
            total_params = 0
            for key, tensor in model_state.items():
                params = tensor.numel()
                total_params += params
                print(f"  {key:30}: {list(tensor.shape)}")
            print(f"Total parameters: {total_params:,}")
        except Exception as e:
            print(f"❌ Error loading model: {e}")

        # Compatibility check: SimpleDukeModel vs EnhancedDukeModel
        print("\n🧪 COMPATIBILITY CHECK")
        print("=" * 60)
        try:
            model_state = torch.load(file_status["model"]["path"], map_location="cpu")
            actual_keys = set(model_state.keys())

            # Keys expected by the OLD simple model (as seen in the warning)
            expected_simple_keys = {
                "network.0.weight",
                "network.0.bias",
                "network.3.weight",
                "network.3.bias",
                "network.6.weight",
                "network.6.bias",
            }

            missing_for_simple = expected_simple_keys - actual_keys
            unexpected_for_simple = actual_keys - expected_simple_keys

            print("Assuming SimpleDukeModel expected keys:")
            for k in sorted(expected_simple_keys):
                print(f"  - {k}")

            print("\nSample keys present in checkpoint:")
            sample_keys = list(sorted(actual_keys))[:20]
            for k in sample_keys:
                print(f"  - {k}")
            if len(actual_keys) > 20:
                print(f"  ... (+{len(actual_keys) - 20} more keys)")

            print("\nResult relative to SimpleDukeModel:")

            if missing_for_simple:
                print("❌ Missing keys for SimpleDukeModel:")
                for k in sorted(missing_for_simple):
                    print(f"  - {k}")
            else:
                print("✅ No missing keys for SimpleDukeModel")

            if unexpected_for_simple:
                print("\n⚠️ Unexpected keys (indicates Enhanced/Residual model layout):")
                sample_unexpected = list(sorted(unexpected_for_simple))[:20]
                for k in sample_unexpected:
                    print(f"  - {k}")
                if len(unexpected_for_simple) > 20:
                    print(f"  ... (+{len(unexpected_for_simple) - 20} more)")
            else:
                print("✅ No unexpected keys; checkpoint matches SimpleDukeModel exactly")

            # Simple heuristic: if we see 'input_proj.weight' assume Enhanced model
            if "input_proj.weight" in actual_keys:
                print("\n📦 Heuristic detection: This checkpoint looks like an EnhancedDukeModel.")
            else:
                print("\n📦 Heuristic detection: This checkpoint looks like a SimpleDukeModel.")

        except Exception as e:
            print(f"❌ Error during compatibility check: {e}")

    # Check embedder
    if file_status["embedder"]["exists"]:
        print("\n📚 INSPECTING EMBEDDER")
        print("=" * 60)
        try:
            with open(file_status["embedder"]["path"], "rb") as f:
                embedder = pickle.load(f)

            if hasattr(embedder, "vocab_size"):
                print(f"Vocabulary size: {embedder.vocab_size:,} words")
            if hasattr(embedder, "embedding_dim"):
                print(f"Embedding dimension: {embedder.embedding_dim}")
            if hasattr(embedder, "vocab"):
                print(f"Sample words: {list(embedder.vocab.keys())[:10]}")
        except Exception as e:
            print(f"⚠️ Could not inspect embedder: {e}")

    # Check generator
    if file_status["generator"]["exists"]:
        print("\n💬 INSPECTING RESPONSE GENERATOR")
        print("=" * 60)
        try:
            with open(file_status["generator"]["path"], "rb") as f:
                generator = pickle.load(f)

            if hasattr(generator, "response_database"):
                db_size = len(generator.response_database)
                print(f"Response database size: {db_size:,}")

                if db_size > 0:
                    # Expect each item to have a 'length' field
                    try:
                        lengths = [item["length"] for item in generator.response_database]
                        avg_len = sum(lengths) / len(lengths)
                        print(f"Average response length: {avg_len:.0f} chars")
                    except Exception:
                        print("Average response length: (could not compute; missing 'length' field)")
                    print(f"Total learned responses: {db_size:,}")
                    print(f"✅ Duke has learned {db_size} response patterns!")
                else:
                    print("⚠️ Response database is empty (needs training)")

            if hasattr(generator, "min_similarity_threshold"):
                print(f"Similarity threshold: {generator.min_similarity_threshold}")
        except Exception as e:
            print(f"⚠️ Could not inspect generator: {e}")

    # Recommendations
    print("\n💡 DUKE STATUS SUMMARY")
    print("=" * 60)

    all_exist = all(status["exists"] for status in file_status.values())

    if all_exist and file_status["generator"]["size"] > 1000:
        print("✅ All Duke checkpoint files exist")
        print("✅ Duke response database is populated")
        print("✅ Duke is READY to process tasks (complexity 1-7)")
        print("\n📊 To test Duke:")
        print("   ./test_duke_performance.sh")
        print("\n🌐 View dashboard:")
        print("   http://localhost:8000/dashboard")
    elif all_exist:
        print("⚠️ Duke files exist but generator seems empty")
        print("\n🔧 To fix:")
        print("   curl -X POST http://localhost:8000/model/train")
    else:
        print("❌ Some Duke files are missing")
        print("\n🔧 To fix:")
        print("   1. Start the server: python3 coordinator_api.py")
        print("   2. Train Duke: curl -X POST http://localhost:8000/model/train")

    print("=" * 60)
    print("✅ Diagnostic complete")


if __name__ == "__main__":
    check_files()
