#!/bin/bash

# Training Data Collection Script for Duke ML
# Submits diverse tasks across complexity levels

echo "🤖 Duke Training Data Collection Script"
echo "========================================"
echo ""

BASE_URL="http://localhost:8000"

# Check if server is running
if ! curl -s "$BASE_URL/health" > /dev/null; then
    echo "❌ Error: Server not running at $BASE_URL"
    echo "Please start coordinator_api.py first"
    exit 1
fi

echo "✅ Server is running"
echo ""

# Define diverse tasks across complexity levels
declare -a TASKS=(
    # Complexity 1-2: Simple facts
    "What is Python?|1"
    "Define photosynthesis|2"
    "What does CPU stand for?|1"
    
    # Complexity 3-4: Basic concepts
    "Explain how HTTP works|3"
    "What is object-oriented programming?|4"
    "Describe the water cycle|3"
    
    # Complexity 5-6: Moderate depth
    "Explain blockchain technology|5"
    "How does encryption protect data?|6"
    "What is machine learning?|5"
    
    # Complexity 7-8: Complex topics
    "Explain neural networks and backpropagation|7"
    "How does quantum entanglement work?|8"
    "Describe distributed systems architecture|7"
    
    # Complexity 9-10: Expert level
    "Explain the Byzantine Generals Problem and its solutions|9"
    "How does gradient descent optimization work in deep learning?|10"
    "Describe the CAP theorem and its implications|9"
)

TOTAL_TASKS=${#TASKS[@]}
SUCCESS_COUNT=0
FAIL_COUNT=0

echo "📝 Submitting $TOTAL_TASKS tasks..."
echo ""

for task_data in "${TASKS[@]}"; do
    IFS='|' read -r description complexity <<< "$task_data"
    
    echo "⏳ Task: $description (Complexity: $complexity/10)"
    
    response=$(curl -s -X POST "$BASE_URL/tasks/submit" \
        -H "Content-Type: application/json" \
        -d "{
            \"description\": \"$description\",
            \"complexity\": $complexity,
            \"buyer_id\": \"training-collector\"
        }")
    
    task_id=$(echo "$response" | grep -o '"id":"[^"]*' | cut -d'"' -f4)
    
    if [ -n "$task_id" ]; then
        echo "   ✅ Submitted - Task ID: ${task_id:0:8}..."
        ((SUCCESS_COUNT++))
    else
        echo "   ❌ Failed to submit"
        ((FAIL_COUNT++))
    fi
    
    # Wait between requests to avoid overwhelming the system
    sleep 3
    
done

echo ""
echo "========================================"
echo "📊 Collection Summary"
echo "========================================"
echo "Total tasks: $TOTAL_TASKS"
echo "Successful: $SUCCESS_COUNT"
echo "Failed: $FAIL_COUNT"
echo ""

# Wait for processing
echo "⏳ Waiting 30 seconds for tasks to process..."
sleep 30

# Get training statistics
echo ""
echo "📈 Training Data Statistics:"
echo "========================================"
curl -s "$BASE_URL/training/stats" | python3 -c "
import sys
import json
data = json.load(sys.stdin)
stats = data.get('data', {})
print(f\"Total API Calls: {stats.get('total_calls', 0)}\")
print(f\"Successful: {stats.get('successful_calls', 0)}\")
print(f\"Failed: {stats.get('failed_calls', 0)}\")
print(f\"Training Samples: {stats.get('training_samples_available', 0)}\")
print(f\"Estimated Cost: \${stats.get('estimated_cost_usd', 0):.4f}\")
print(f\"\\nComplexity Distribution:\")
for k, v in stats.get('complexity_distribution', {}).items():
    print(f\"  Level {k}: {v} samples\")
"

echo ""
echo "✅ Data collection complete!"
echo ""
echo "📁 View logs: cat duke_training_logs.jsonl | python3 -m json.tool"
echo "🌐 Dashboard: http://localhost:8000/dashboard"
echo "📊 Stats API: curl http://localhost:8000/training/stats"