#!/bin/bash

# Duke Performance Test Suite
# Tests Duke across complexity levels and compares with OpenAI

echo "🧪 Duke Performance Test Suite"
echo "========================================"
echo ""

BASE_URL="http://localhost:8000"

# Test tasks across Duke's capability range (complexity 1-7)
declare -a DUKE_TESTS=(
    "What is Python?|1"
    "Explain REST APIs|3"
    "How does blockchain work?|5"
    "Describe neural networks|7"
)

# Test tasks beyond Duke's range (complexity 8-10, should use OpenAI)
declare -a OPENAI_TESTS=(
    "Explain quantum computing in detail|8"
    "Describe distributed consensus algorithms|9"
    "How does transformer architecture work?|10"
)

echo "📊 Phase 1: Testing Duke (Complexity 1-7)"
echo "========================================"
echo ""

DUKE_TASKS=()

for test_data in "${DUKE_TESTS[@]}"; do
    IFS='|' read -r description complexity <<< "$test_data"
    
    echo "⏳ Submitting: $description (Complexity: $complexity)"
    
    response=$(curl -s -X POST "$BASE_URL/tasks/submit" \
        -H "Content-Type: application/json" \
        -d "{
            \"description\": \"$description\",
            \"complexity\": $complexity,
            \"buyer_id\": \"duke-performance-test\"
        }")
    
    task_id=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    DUKE_TASKS+=("$task_id")
    
    echo "   ✅ Task ID: ${task_id:0:8}..."
    sleep 2
done

echo ""
echo "📊 Phase 2: Testing OpenAI Fallback (Complexity 8-10)"
echo "========================================"
echo ""

OPENAI_TASKS=()

for test_data in "${OPENAI_TESTS[@]}"; do
    IFS='|' read -r description complexity <<< "$test_data"
    
    echo "⏳ Submitting: $description (Complexity: $complexity)"
    
    response=$(curl -s -X POST "$BASE_URL/tasks/submit" \
        -H "Content-Type: application/json" \
        -d "{
            \"description\": \"$description\",
            \"complexity\": $complexity,
            \"buyer_id\": \"openai-test\"
        }")
    
    task_id=$(echo "$response" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    OPENAI_TASKS+=("$task_id")
    
    echo "   ✅ Task ID: ${task_id:0:8}..."
    sleep 2
done

echo ""
echo "⏳ Waiting 15 seconds for processing..."
sleep 15

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESULTS: Duke Tasks (Should use duke-ml)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

DUKE_COUNT=0
for task_id in "${DUKE_TASKS[@]}"; do
    task_data=$(curl -s "$BASE_URL/tasks/$task_id")
    
    agent=$(echo "$task_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_name', 'unknown'))")
    status=$(echo "$task_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status', 'unknown'))")
    complexity=$(echo "$task_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('complexity', 'unknown'))")
    time=$(echo "$task_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('processing_time_seconds', 0))")
    
    if [ "$agent" = "duke-ml" ]; then
        echo "✅ Task ${task_id:0:8}... | Agent: $agent | Status: $status | Time: ${time}s | Complexity: $complexity"
        ((DUKE_COUNT++))
    else
        echo "❌ Task ${task_id:0:8}... | Agent: $agent | Status: $status | Time: ${time}s | Complexity: $complexity"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 RESULTS: OpenAI Tasks (Should use openai-gpt4)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

OPENAI_COUNT=0
for task_id in "${OPENAI_TASKS[@]}"; do
    task_data=$(curl -s "$BASE_URL/tasks/$task_id")
    
    agent=$(echo "$task_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('agent_name', 'unknown'))")
    status=$(echo "$task_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status', 'unknown'))")
    complexity=$(echo "$task_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('complexity', 'unknown'))")
    time=$(echo "$task_data" | python3 -c "import sys,json; print(json.load(sys.stdin).get('processing_time_seconds', 0))")
    
    if [ "$agent" = "openai-gpt4" ]; then
        echo "✅ Task ${task_id:0:8}... | Agent: $agent | Status: $status | Time: ${time}s | Complexity: $complexity"
        ((OPENAI_COUNT++))
    else
        echo "⚠️  Task ${task_id:0:8}... | Agent: $agent | Status: $status | Time: ${time}s | Complexity: $complexity"
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📈 PERFORMANCE SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

TOTAL_DUKE_TASKS=${#DUKE_TASKS[@]}
TOTAL_OPENAI_TASKS=${#OPENAI_TASKS[@]}

DUKE_SUCCESS_RATE=$((DUKE_COUNT * 100 / TOTAL_DUKE_TASKS))
OPENAI_SUCCESS_RATE=$((OPENAI_COUNT * 100 / TOTAL_OPENAI_TASKS))

echo "Duke Tasks (Complexity 1-7):"
echo "  Submitted: $TOTAL_DUKE_TASKS"
echo "  Handled by Duke: $DUKE_COUNT"
echo "  Success Rate: $DUKE_SUCCESS_RATE%"
echo ""

echo "OpenAI Tasks (Complexity 8-10):"
echo "  Submitted: $TOTAL_OPENAI_TASKS"
echo "  Handled by OpenAI: $OPENAI_COUNT"
echo "  Success Rate: $OPENAI_SUCCESS_RATE%"
echo ""

# Get current Duke stats
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 CURRENT DUKE STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

curl -s "$BASE_URL/model/status" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Version: {data['version']}\")
print(f\"Accuracy: {data['accuracy']*100:.2f}%\")
print(f\"Training Samples: {data['training_samples']}\")
print(f\"Vocabulary Size: {data['vocabulary_size']}\")
print(f\"Status: {data['status']}\")
"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Test Complete!"
echo ""
echo "💡 View detailed results in dashboard:"
echo "   http://localhost:8000/dashboard"
echo ""