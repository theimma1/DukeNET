#!/bin/bash

while true; do
  clear
  echo "╔════════════════════════════════════════════════════════════╗"
  echo "║        DUKE ML PRODUCTION MONITORING DASHBOARD              ║"
  echo "╚════════════════════════════════════════════════════════════╝"
  echo ""
  
  # Get stats
  TOTAL=$(sqlite3 aicp.db "SELECT COUNT(*) FROM training_data;" 2>/dev/null || echo "0")
  SUCCESS=$(sqlite3 aicp.db "SELECT COUNT(*) FROM training_data WHERE status='completed';" 2>/dev/null || echo "0")
  
  # Calculate percentage
  if [ "$TOTAL" -gt "0" ]; then
    SUCCESS_RATE=$(echo "scale=1; $SUCCESS * 100 / $TOTAL" | bc)
  else
    SUCCESS_RATE="0"
  fi
  
  # Progress to 5000
  PROGRESS=$((TOTAL * 100 / 5000))
  
  echo "📊 TRAINING DATA"
  echo "   Total samples: $TOTAL/5000 ($(printf '%3d' $PROGRESS)%)"
  echo "   Successful: $SUCCESS/$TOTAL ($SUCCESS_RATE%)"
  
  echo ""
  echo "📈 PROGRESS TO 5000 SAMPLES"
  printf "   ["
  for i in $(seq 1 50); do
    if [ $i -le $((TOTAL / 100)) ]; then
      printf "█"
    else
      printf "░"
    fi
  done
  printf "] $TOTAL/5000\n"
  
  echo ""
  echo "🎯 MILESTONES"
  if [ "$TOTAL" -ge "5000" ]; then
    echo "   ✅ 5000 samples - READY FOR SPECIALISTS!"
  elif [ "$TOTAL" -ge "3000" ]; then
    echo "   ✅ 3000 samples - Getting close to specialists!"
  elif [ "$TOTAL" -ge "1000" ]; then
    echo "   ✅ 1000 samples - Significant progress!"
  fi
  
  echo ""
  echo "⏰ Last updated: $(date '+%H:%M:%S')"
  echo "📂 Dashboard: http://localhost:8000/dashboard"
  echo "📋 Analysis: python3 analyze_training_data.py"
  echo ""
  echo "Press Ctrl+C to stop monitoring"
  
  sleep 10
done
