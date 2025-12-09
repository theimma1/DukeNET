#!/usr/bin/env python3
"""
Duke Model Diagnostic Tool - Fixed Version
Checks Duke checkpoint files and provides detailed status
"""

import torch
import pickle
from pathlib import Path
import sys

# Add dummy classes for unpickling
class TextEmbedder:
    pass

class ResponseGenerator:
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
        "generator": "duke_responses.pkl"  # Changed from duke_generator.pkl
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
    
    # Check embedder
    if file_status["embedder"]["exists"]:
        print("\n📚 INSPECTING EMBEDDER")
        print("=" * 60)
        try:
            with open(file_status["embedder"]["path"], "rb") as f:
                embedder = pickle.load(f)
            
            if hasattr(embedder, 'vocab_size'):
                print(f"Vocabulary size: {embedder.vocab_size:,} words")
            if hasattr(embedder, 'embedding_dim'):
                print(f"Embedding dimension: {embedder.embedding_dim}")
            if hasattr(embedder, 'vocab'):
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
            
            if hasattr(generator, 'response_database'):
                db_size = len(generator.response_database)
                print(f"Response database size: {db_size:,}")
                
                if db_size > 0:
                    lengths = [item["length"] for item in generator.response_database]
                    print(f"Average response length: {sum(lengths)/len(lengths):.0f} chars")
                    print(f"Total learned responses: {db_size:,}")
                    print(f"✅ Duke has learned {db_size} response patterns!")
                else:
                    print("⚠️ Response database is empty (needs training)")
            
            if hasattr(generator, 'min_similarity_threshold'):
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