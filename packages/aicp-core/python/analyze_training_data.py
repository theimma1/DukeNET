#!/usr/bin/env python3
"""
Duke Training Data Analyzer
Analyze collected OpenAI training data for quality and readiness
"""

import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

TRAINING_LOG_FILE = Path("duke_training_logs.jsonl")

def load_training_data():
    """Load all training data from JSONL file"""
    if not TRAINING_LOG_FILE.exists():
        print(f"❌ Training log file not found: {TRAINING_LOG_FILE}")
        return []
    
    data = []
    with open(TRAINING_LOG_FILE, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                entry = json.loads(line)
                data.append(entry)
            except json.JSONDecodeError as e:
                print(f"⚠️  Warning: Skipping malformed line {line_num}: {e}")
    
    return data

def analyze_data(data):
    """Perform comprehensive analysis on training data"""
    
    if not data:
        print("❌ No training data to analyze")
        return
    
    print("╔════════════════════════════════════════════════════════════════╗")
    print("║          DUKE TRAINING DATA ANALYSIS REPORT                   ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    print()
    
    # Basic statistics
    total_samples = len(data)
    successful = sum(1 for d in data if d.get('success'))
    failed = total_samples - successful
    
    print("📊 BASIC STATISTICS")
    print("=" * 60)
    print(f"Total samples: {total_samples}")
    print(f"Successful:    {successful} ({successful/total_samples*100:.1f}%)")
    print(f"Failed:        {failed} ({failed/total_samples*100:.1f}%)")
    print()
    
    # Token analysis
    total_input_tokens = sum(d['input']['estimated_tokens'] for d in data if d.get('success'))
    total_output_tokens = sum(d['output']['estimated_tokens'] for d in data if d.get('success'))
    
    # Get actual token counts if available
    actual_tokens = []
    for d in data:
        if d.get('metadata', {}).get('tokens_used'):
            tokens = d['metadata']['tokens_used']
            actual_tokens.append({
                'prompt': tokens.get('prompt_tokens', 0),
                'completion': tokens.get('completion_tokens', 0),
                'total': tokens.get('total_tokens', 0)
            })
    
    print("🎯 TOKEN ANALYSIS")
    print("=" * 60)
    print(f"Estimated input tokens:  {total_input_tokens:,}")
    print(f"Estimated output tokens: {total_output_tokens:,}")
    
    if actual_tokens:
        actual_input = sum(t['prompt'] for t in actual_tokens)
        actual_output = sum(t['completion'] for t in actual_tokens)
        actual_total = sum(t['total'] for t in actual_tokens)
        
        print(f"\nActual tokens (from {len(actual_tokens)} samples):")
        print(f"  Input:      {actual_input:,}")
        print(f"  Output:     {actual_output:,}")
        print(f"  Total:      {actual_total:,}")
        print(f"  Avg/sample: {actual_total//len(actual_tokens):,}")
        
        # Cost estimation (GPT-3.5-turbo rates)
        input_cost = actual_input * 0.0005 / 1000
        output_cost = actual_output * 0.0015 / 1000
        total_cost = input_cost + output_cost
        print(f"\n💰 Estimated cost: ${total_cost:.4f}")
    print()
    
    # Complexity distribution
    complexities = Counter(d['complexity'] for d in data)
    
    print("📈 COMPLEXITY DISTRIBUTION")
    print("=" * 60)
    for level in sorted(complexities.keys()):
        count = complexities[level]
        bar = "█" * (count * 40 // max(complexities.values()))
        print(f"Level {level:2d}: {count:3d} {bar}")
    print()
    
    # Response length analysis
    response_lengths = [
        len(d['output']['response']) 
        for d in data 
        if d.get('success') and d['output'].get('response')
    ]
    
    if response_lengths:
        print("📝 RESPONSE LENGTH ANALYSIS")
        print("=" * 60)
        print(f"Shortest: {min(response_lengths):,} chars")
        print(f"Longest:  {max(response_lengths):,} chars")
        print(f"Average:  {sum(response_lengths)//len(response_lengths):,} chars")
        print(f"Median:   {sorted(response_lengths)[len(response_lengths)//2]:,} chars")
        print()
    
    # Time distribution
    timestamps = [datetime.fromisoformat(d['timestamp']) for d in data]
    if timestamps:
        first = min(timestamps)
        last = max(timestamps)
        duration = (last - first).total_seconds()
        
        print("⏰ TIME ANALYSIS")
        print("=" * 60)
        print(f"First sample: {first.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Last sample:  {last.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Duration:     {duration/60:.1f} minutes")
        print(f"Rate:         {total_samples/(duration/60):.1f} samples/minute")
        print()
    
    # Model distribution
    models = Counter(d['model'] for d in data)
    
    print("🤖 MODEL USAGE")
    print("=" * 60)
    for model, count in models.items():
        print(f"{model}: {count} samples")
    print()
    
    # Quality checks
    print("✅ QUALITY CHECKS")
    print("=" * 60)
    
    # Check for empty responses
    empty_responses = sum(
        1 for d in data 
        if d.get('success') and not d['output'].get('response')
    )
    
    # Check for very short responses
    short_responses = sum(
        1 for d in data 
        if d.get('success') and d['output'].get('response') 
        and len(d['output']['response']) < 50
    )
    
    # Check for errors
    errors = [d for d in data if not d.get('success')]
    
    print(f"Empty responses:     {empty_responses}")
    print(f"Very short (<50ch):  {short_responses}")
    print(f"Failed with errors:  {len(errors)}")
    
    if errors:
        print("\n⚠️  Error details:")
        error_types = Counter(d.get('error', 'Unknown') for d in errors)
        for error, count in error_types.most_common(5):
            print(f"  - {error}: {count}")
    print()
    
    # Duke readiness assessment
    print("🧠 DUKE ML READINESS")
    print("=" * 60)
    
    complexity_range = max(complexities.keys()) - min(complexities.keys()) + 1
    avg_samples_per_level = total_samples / len(complexities)
    
    readiness_score = 0
    max_score = 5
    
    # Criterion 1: Enough samples
    if total_samples >= 100:
        readiness_score += 1
        print("✅ Sample count: Excellent (100+)")
    elif total_samples >= 50:
        readiness_score += 0.5
        print("⚠️  Sample count: Good (50-99), more recommended")
    else:
        print("❌ Sample count: Insufficient (<50)")
    
    # Criterion 2: Success rate
    success_rate = successful / total_samples
    if success_rate >= 0.95:
        readiness_score += 1
        print(f"✅ Success rate: Excellent ({success_rate*100:.1f}%)")
    elif success_rate >= 0.85:
        readiness_score += 0.5
        print(f"⚠️  Success rate: Good ({success_rate*100:.1f}%)")
    else:
        print(f"❌ Success rate: Low ({success_rate*100:.1f}%)")
    
    # Criterion 3: Complexity coverage
    if complexity_range >= 8:
        readiness_score += 1
        print(f"✅ Complexity range: Excellent (covers {complexity_range}/10 levels)")
    elif complexity_range >= 5:
        readiness_score += 0.5
        print(f"⚠️  Complexity range: Good ({complexity_range}/10 levels)")
    else:
        print(f"❌ Complexity range: Limited ({complexity_range}/10 levels)")
    
    # Criterion 4: Distribution balance
    if avg_samples_per_level >= 5:
        readiness_score += 1
        print(f"✅ Distribution: Well-balanced ({avg_samples_per_level:.1f} samples/level)")
    elif avg_samples_per_level >= 3:
        readiness_score += 0.5
        print(f"⚠️  Distribution: Acceptable ({avg_samples_per_level:.1f} samples/level)")
    else:
        print(f"❌ Distribution: Sparse ({avg_samples_per_level:.1f} samples/level)")
    
    # Criterion 5: Response quality
    if empty_responses == 0 and short_responses < total_samples * 0.1:
        readiness_score += 1
        print("✅ Response quality: High")
    elif short_responses < total_samples * 0.2:
        readiness_score += 0.5
        print("⚠️  Response quality: Good")
    else:
        print("❌ Response quality: Needs improvement")
    
    print()
    print(f"OVERALL READINESS: {readiness_score:.1f}/{max_score}")
    print()
    
    if readiness_score >= 4.5:
        print("🎉 READY FOR PRODUCTION TRAINING!")
        print("   Duke can be trained with this dataset for excellent results.")
    elif readiness_score >= 3.5:
        print("✅ READY FOR TRAINING")
        print("   Dataset is good enough to train Duke. More data will improve results.")
    elif readiness_score >= 2.5:
        print("⚠️  MARGINAL - COLLECT MORE DATA")
        print("   Training possible but results may be limited. Recommend 50+ samples.")
    else:
        print("❌ NOT READY - INSUFFICIENT DATA")
        print("   Collect more diverse samples before training Duke.")
    print()
    
    # Sample showcase
    if successful > 0:
        print("📋 SAMPLE SHOWCASE (Latest 3)")
        print("=" * 60)
        recent = [d for d in data if d.get('success')][-3:]
        for i, sample in enumerate(recent, 1):
            prompt = sample['input']['prompt'][:60] + "..." if len(sample['input']['prompt']) > 60 else sample['input']['prompt']
            response = sample['output']['response'][:80] + "..." if len(sample['output']['response']) > 80 else sample['output']['response']
            
            print(f"\nSample {i} (Complexity {sample['complexity']}/10):")
            print(f"  Q: {prompt}")
            print(f"  A: {response}")

def main():
    print()
    data = load_training_data()
    
    if data:
        print(f"✅ Loaded {len(data)} training samples\n")
        analyze_data(data)
        
        print("\n" + "=" * 60)
        print("📁 Files:")
        print(f"   Training data: {TRAINING_LOG_FILE}")
        print(f"   Metadata:      duke_training_metadata.json")
        print("\n💡 Next steps:")
        print("   - Submit more tasks to improve coverage")
        print("   - Run: curl http://localhost:8000/model/train (when ready)")
        print("   - Monitor: http://localhost:8000/dashboard")
        print()
    else:
        print("❌ No training data found. Submit some tasks first!")
        print("\n💡 Quick start:")
        print("   ./collect_training_data.sh")
        print()

if __name__ == "__main__":
    main()