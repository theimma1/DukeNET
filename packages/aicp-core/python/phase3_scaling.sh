#!/bin/bash

echo "STARTING PHASE 3: SCALING TO 5,000+ SAMPLES ON POSTGRESQL"
echo "============================================================"

# Phase 3A: Machine Learning Domain (500 samples)
echo "Phase 3A: Machine Learning Expert Training (500 samples)..."
for i in {1..10}; do
    echo "  Batch $i/10"
    python3 advanced_tasks.py domain machine_learning 50
    sleep 1
done

# Phase 3B: System Design Domain (400 samples)
echo "Phase 3B: Systems Expert Training (400 samples)..."
for i in {1..8}; do
    echo "  Batch $i/8"
    python3 advanced_tasks.py domain system_design 50
    sleep 1
done

# Phase 3C: Security Domain (300 samples)
echo "Phase 3C: Security Expert Training (300 samples)..."
for i in {1..6}; do
    echo "  Batch $i/6"
    python3 advanced_tasks.py domain security 50
    sleep 1
done

# Phase 3D: Advanced Topics (300 samples)
echo "Phase 3D: Advanced Expert Training (300 samples)..."
for i in {1..6}; do
    echo "  Batch $i/6"
    python3 advanced_tasks.py domain advanced 50
    sleep 1
done

# Phase 3E: Generalist Bulk Fill (2,500 samples)
echo "Phase 3E: Generalist Training - BULK FILL (2,500 samples)..."
for i in {1..13}; do
    echo "  Comprehensive Batch $i/13"
    python3 advanced_tasks.py comprehensive 200
    sleep 2
done

echo ""
echo "============================================================"
echo "PHASE 3 SCALING COMPLETE!"
echo "============================================================"

# Final verification
sleep 10
curl http://localhost:8000/model/status | jq '{samples: .training_samples, status: .status}'