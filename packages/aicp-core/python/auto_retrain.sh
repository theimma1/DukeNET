#!/bin/bash

LAST_TRAINED=0
TRAINING_THRESHOLD=500

# Get initial count
LAST_TRAINED=$(sqlite3 aicp.db "SELECT COUNT(*) FROM training_data;" 2>/dev/null || echo "0")

echo "🧠 Auto-retraining monitor started"
echo "📊 Retraining every $TRAINING_THRESHOLD new samples"
echo "   Current samples: $LAST_TRAINED"

while true; do
  CURRENT=$(sqlite3 aicp.db "SELECT COUNT(*) FROM training_data;" 2>/dev/null || echo "0")
  NEW_SAMPLES=$((CURRENT - LAST_TRAINED))
  
  if [ $NEW_SAMPLES -ge $TRAINING_THRESHOLD ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🚀 RETRAINING TRIGGERED: $CURRENT total samples"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Backup before training
    cp aicp.db backups/aicp.db.pre_train_$CURRENT.backup 2>/dev/null || true
    
    # Trigger retraining
    RESPONSE=$(curl -s -X POST http://localhost:8000/model/train)
    echo "Response: $RESPONSE"
    
    LAST_TRAINED=$CURRENT
    echo "✅ Duke retraining complete!"
    echo ""
  fi
  
  sleep 30
done
