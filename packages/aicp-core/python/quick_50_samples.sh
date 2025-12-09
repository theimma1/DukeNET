#!/bin/bash

# Quick 50+ Samples Collection
# Runs multiple batches automatically to reach training threshold

echo "🚀 Duke Quick Training: Path to 50+ Samples"
echo "==========================================="
echo ""

BASE_URL="http://localhost:8000"

# Check server
if ! curl -s "$BASE_URL/health" > /dev/null; then
    echo "❌ Server not running. Start coordinator_api.py first."
    exit 1
fi

# Get current stats
CURRENT=$(curl -s "$BASE_URL/training/stats" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['data']['training_samples_available'])
" 2>/dev/null || echo "0")

echo "📊 Current training samples: $CURRENT"
echo ""

TARGET=50
NEEDED=$((TARGET - CURRENT))

if [ $NEEDED -le 0 ]; then
    echo "✅ You already have $CURRENT samples! Training ready!"
    echo ""
    echo "🧠 Trigger Duke training:"
    echo "   curl -X POST $BASE_URL/model/train"
    exit 0
fi

echo "🎯 Target: $TARGET samples"
echo "📝 Need: $NEEDED more samples"
echo ""

# Calculate batches (15 samples per batch)
BATCHES=$(( (NEEDED + 14) / 15 ))

echo "🔄 Will run $BATCHES collection batch(es)"
echo ""
read -p "Press Enter to start collection..."
echo ""

for i in $(seq 1 $BATCHES); do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 BATCH $i/$BATCHES"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    ./collect_training_data.sh
    
    echo ""
    
    # Check progress
    NEW_COUNT=$(curl -s "$BASE_URL/training/stats" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['data']['training_samples_available'])
" 2>/dev/null || echo "0")
    
    echo "📈 Progress: $NEW_COUNT/$TARGET samples"
    echo ""
    
    if [ $NEW_COUNT -ge $TARGET ]; then
        echo "🎉 TARGET REACHED! $NEW_COUNT samples collected!"
        break
    fi
    
    if [ $i -lt $BATCHES ]; then
        echo "⏳ Waiting 10 seconds before next batch..."
        sleep 10
        echo ""
    fi
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎊 COLLECTION COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Final analysis
echo "📊 Running final analysis..."
echo ""
python3 analyze_training_data.py

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧠 NEXT STEPS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Review analysis above"
echo "2. Check dashboard: http://localhost:8000/dashboard"
echo "3. Trigger Duke training:"
echo ""
echo "   curl -X POST $BASE_URL/model/train"
echo ""
echo "4. Monitor training in logs:"
echo ""
echo "   tail -f coordinator_api.py.log"
echo ""
echo "✨ Duke will be production-ready after training!"
echo ""