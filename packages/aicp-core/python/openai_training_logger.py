"""
OpenAI API Logger for Duke Training Data Collection
Securely logs all OpenAI API calls for future machine learning training
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import logging
from functools import wraps
import hashlib

# ==================== CONFIGURATION ====================

TRAINING_LOG_FILE = Path("duke_training_logs.jsonl")
METADATA_FILE = Path("duke_training_metadata.json")

# Security: Never hardcode API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logging.warning("⚠️ OPENAI_API_KEY not found in environment variables")

logger = logging.getLogger(__name__)

# ==================== LOGGING FUNCTIONS ====================

def sanitize_for_training(text: str, max_length: int = 5000) -> str:
    """Sanitize text for training data storage"""
    if not text:
        return ""
    # Remove any potential PII patterns (basic sanitization)
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length] + "...[truncated]"
    return text

def calculate_token_estimate(text: str) -> int:
    """Rough token estimate (GPT-3.5: ~4 chars = 1 token)"""
    return len(text) // 4

def log_openai_call(
    prompt: str,
    response: str,
    model: str,
    complexity: int,
    task_id: str,
    success: bool,
    error: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log OpenAI API call to JSONL file for Duke training
    
    Args:
        prompt: User input/task description
        response: OpenAI response
        model: Model used (e.g., gpt-3.5-turbo)
        complexity: Task complexity (1-10)
        task_id: Unique task identifier
        success: Whether the call succeeded
        error: Error message if failed
        metadata: Additional metadata (agent, price, etc.)
    """
    try:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "task_id": task_id,
            "model": model,
            "complexity": complexity,
            "success": success,
            "input": {
                "prompt": sanitize_for_training(prompt),
                "estimated_tokens": calculate_token_estimate(prompt),
            },
            "output": {
                "response": sanitize_for_training(response) if response else None,
                "estimated_tokens": calculate_token_estimate(response) if response else 0,
            },
            "error": error,
            "metadata": metadata or {},
        }
        
        # Append to JSONL file (one JSON object per line)
        with open(TRAINING_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        logger.info(f"📝 Logged OpenAI call for task {task_id[:8]}... to training data")
        
        # Update metadata file with statistics
        update_training_metadata(success, complexity, model)
        
    except Exception as e:
        logger.error(f"💥 Failed to log OpenAI call: {e}")

def update_training_metadata(success: bool, complexity: int, model: str) -> None:
    """Update aggregate metadata for training statistics"""
    try:
        # Load existing metadata
        if METADATA_FILE.exists():
            with open(METADATA_FILE, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "total_estimated_cost": 0.0,
                "complexity_distribution": {},
                "model_usage": {},
                "first_logged": datetime.now(timezone.utc).isoformat(),
                "last_updated": None,
            }
        
        # Update statistics
        metadata["total_calls"] += 1
        if success:
            metadata["successful_calls"] += 1
        else:
            metadata["failed_calls"] += 1
        
        # Track complexity distribution
        complexity_key = str(complexity)
        metadata["complexity_distribution"][complexity_key] = \
            metadata["complexity_distribution"].get(complexity_key, 0) + 1
        
        # Track model usage
        metadata["model_usage"][model] = metadata["model_usage"].get(model, 0) + 1
        
        # Estimate cost (GPT-3.5-turbo: $0.0005/1K input tokens, $0.0015/1K output tokens)
        # This is a rough estimate for tracking purposes
        metadata["total_estimated_cost"] += 0.001  # Simplified estimate per call
        
        metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # Save metadata
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)
            
    except Exception as e:
        logger.error(f"💥 Failed to update training metadata: {e}")

def get_training_stats() -> Dict[str, Any]:
    """Get current training data statistics"""
    try:
        if not METADATA_FILE.exists():
            return {
                "total_calls": 0,
                "training_samples_available": 0,
                "status": "No training data yet"
            }
        
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)
        
        # Count lines in JSONL file
        if TRAINING_LOG_FILE.exists():
            with open(TRAINING_LOG_FILE, 'r') as f:
                training_samples = sum(1 for _ in f)
        else:
            training_samples = 0
        
        return {
            "total_calls": metadata.get("total_calls", 0),
            "successful_calls": metadata.get("successful_calls", 0),
            "failed_calls": metadata.get("failed_calls", 0),
            "training_samples_available": training_samples,
            "estimated_cost_usd": round(metadata.get("total_estimated_cost", 0), 4),
            "complexity_distribution": metadata.get("complexity_distribution", {}),
            "model_usage": metadata.get("model_usage", {}),
            "first_logged": metadata.get("first_logged"),
            "last_updated": metadata.get("last_updated"),
        }
    except Exception as e:
        logger.error(f"💥 Failed to get training stats: {e}")
        return {"error": str(e)}

def load_training_data_for_duke(
    min_complexity: int = 1,
    max_complexity: int = 10,
    limit: Optional[int] = None
) -> list:
    """
    Load training data from JSONL file for Duke model training
    
    Args:
        min_complexity: Minimum complexity to include
        max_complexity: Maximum complexity to include
        limit: Maximum number of samples to return
    
    Returns:
        List of training samples
    """
    try:
        if not TRAINING_LOG_FILE.exists():
            logger.warning("⚠️ No training data file found")
            return []
        
        training_samples = []
        
        with open(TRAINING_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    
                    # Filter by complexity
                    if min_complexity <= entry["complexity"] <= max_complexity:
                        # Only include successful calls with responses
                        if entry["success"] and entry["output"]["response"]:
                            training_samples.append({
                                "input": entry["input"]["prompt"],
                                "output": entry["output"]["response"],
                                "complexity": entry["complexity"],
                                "task_id": entry["task_id"],
                                "timestamp": entry["timestamp"],
                                "metadata": entry.get("metadata", {}),
                            })
                            
                            if limit and len(training_samples) >= limit:
                                break
                                
                except json.JSONDecodeError:
                    continue
        
        logger.info(f"📚 Loaded {len(training_samples)} training samples for Duke")
        return training_samples
        
    except Exception as e:
        logger.error(f"💥 Failed to load training data: {e}")
        return []

def export_training_data_to_jsonl(
    output_file: str = "duke_export.jsonl",
    format_type: str = "simple"
) -> bool:
    """
    Export training data in various formats for Duke training
    
    Args:
        output_file: Output filename
        format_type: 'simple' (prompt/completion) or 'detailed' (full metadata)
    
    Returns:
        True if successful
    """
    try:
        training_data = load_training_data_for_duke()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in training_data:
                if format_type == "simple":
                    export_entry = {
                        "prompt": sample["input"],
                        "completion": sample["output"],
                        "complexity": sample["complexity"],
                    }
                else:  # detailed
                    export_entry = sample
                
                f.write(json.dumps(export_entry) + '\n')
        
        logger.info(f"✅ Exported {len(training_data)} samples to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"💥 Failed to export training data: {e}")
        return False

# ==================== DECORATOR FOR AUTOMATIC LOGGING ====================

def log_openai_training(func):
    """
    Decorator to automatically log OpenAI API calls for training
    
    Usage:
        @log_openai_training
        async def call_openai(description, complexity, task_id):
            # ... your OpenAI API call
            return response
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract parameters (adjust based on your function signature)
        description = kwargs.get('description') or (args[0] if len(args) > 0 else None)
        complexity = kwargs.get('complexity') or (args[1] if len(args) > 1 else None)
        task_id = kwargs.get('task_id') or (args[2] if len(args) > 2 else None)
        
        try:
            # Call the original function
            result = await func(*args, **kwargs)
            
            # Log successful call
            if result:
                log_openai_call(
                    prompt=description,
                    response=result,
                    model="gpt-3.5-turbo",
                    complexity=complexity,
                    task_id=task_id,
                    success=True,
                    metadata={"function": func.__name__}
                )
            
            return result
            
        except Exception as e:
            # Log failed call
            log_openai_call(
                prompt=description,
                response=None,
                model="gpt-3.5-turbo",
                complexity=complexity,
                task_id=task_id,
                success=False,
                error=str(e),
                metadata={"function": func.__name__}
            )
            raise
    
    return wrapper

# ==================== HELPER FUNCTIONS ====================

def get_api_key_status() -> Dict[str, Any]:
    """Check OpenAI API key configuration status"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return {
            "configured": False,
            "status": "missing",
            "message": "OPENAI_API_KEY not found in environment variables",
            "help": "Set it with: export OPENAI_API_KEY='your-key-here'"
        }
    
    # Basic validation (without exposing the key)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:8]
    
    return {
        "configured": True,
        "status": "active",
        "key_hash": key_hash,
        "message": "API key configured successfully"
    }

def clear_training_logs(confirm: bool = False) -> bool:
    """
    Clear all training logs (use with caution!)
    
    Args:
        confirm: Must be True to actually delete
    
    Returns:
        True if cleared successfully
    """
    if not confirm:
        logger.warning("⚠️ clear_training_logs() called without confirmation")
        return False
    
    try:
        if TRAINING_LOG_FILE.exists():
            # Backup before deleting
            backup_file = f"duke_training_logs_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
            TRAINING_LOG_FILE.rename(backup_file)
            logger.info(f"📦 Backed up training logs to {backup_file}")
        
        if METADATA_FILE.exists():
            METADATA_FILE.unlink()
        
        logger.info("🗑️ Training logs cleared successfully")
        return True
        
    except Exception as e:
        logger.error(f"💥 Failed to clear training logs: {e}")
        return False

# ==================== GPT INTEGRATION HELPERS ====================

def get_gpt_explanation(prompt: str, max_tokens: int = 150) -> str:
    """
    Get a brief explanation from GPT-3.5 (for testing/debugging)
    This is a helper function separate from the main training pipeline
    """
    import httpx
    import asyncio
    
    async def _call():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant. Be concise."},
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": max_tokens,
                        "temperature": 0.7
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    return response.json()['choices'][0]['message']['content']
                else:
                    return f"Error: {response.status_code}"
        except Exception as e:
            return f"Exception: {str(e)}"
    
    # Run async function
    return asyncio.run(_call())

def get_gpt_explanation_for_task(description: str, complexity: int) -> str:
    """
    Generate explanation specifically formatted for task responses
    """
    prompt = f"Explain this task (complexity {complexity}/10) briefly: {description}"
    return get_gpt_explanation(prompt, max_tokens=200)

# ==================== TESTING UTILITIES ====================

def test_logging_system():
    """Test the logging system with sample data"""
    print("🧪 Testing OpenAI Training Logger...")
    print()
    
    # Test 1: API Key Status
    print("1️⃣ Checking API Key Status:")
    key_status = get_api_key_status()
    print(f"   Status: {key_status['status']}")
    print(f"   Message: {key_status['message']}")
    print()
    
    # Test 2: Log Sample Data
    print("2️⃣ Logging Sample Training Data:")
    log_openai_call(
        prompt="What is machine learning?",
        response="Machine learning is a subset of artificial intelligence...",
        model="gpt-3.5-turbo",
        complexity=3,
        task_id="test-001",
        success=True,
        metadata={"test": True}
    )
    print("   ✅ Sample logged successfully")
    print()
    
    # Test 3: Get Statistics
    print("3️⃣ Training Data Statistics:")
    stats = get_training_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    print()
    
    # Test 4: Load Training Data
    print("4️⃣ Loading Training Data:")
    samples = load_training_data_for_duke(limit=5)
    print(f"   Loaded {len(samples)} samples")
    print()
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    test_logging_system()