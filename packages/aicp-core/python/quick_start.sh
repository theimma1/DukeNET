# ============================================================================
# QUICK START: RUN THIS NOW TO START PRODUCTION DEPLOYMENT
# ============================================================================

#!/bin/bash

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   DUKE ML PRODUCTION DEPLOYMENT - QUICK START              ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1: BACKUP CURRENT STATE
# ============================================================================

echo "📦 Step 1: Backing up current state..."
mkdir -p backups
cp aicp.db backups/aicp.db.backup.$(date +%Y%m%d_%H%M%S)
cp -r duke_checkpoints backups/duke_checkpoints.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
echo "✅ Backup complete"
echo ""

# ============================================================================
# STEP 2: KILL EXISTING SERVERS
# ============================================================================

echo "🔌 Step 2: Stopping existing servers..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2
echo "✅ Existing servers stopped"
echo ""

# ============================================================================
# STEP 3: CREATE NECESSARY DIRECTORIES
# ============================================================================

echo "📁 Step 3: Creating directories..."
mkdir -p logs reports
echo "✅ Directories created"
echo ""

# ============================================================================
# STEP 4: START SERVER (Terminal 1)
# ============================================================================

echo "🚀 Step 4: Starting FastAPI server..."
echo "   This will run in the background"
echo ""

python3 coordinator_api.py 2>&1 | tee logs/server_$(date +%Y%m%d_%H%M%S).log &
SERVER_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 5

# Test server
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Server started successfully (PID: $SERVER_PID)"
else
    echo "❌ Server failed to start. Check logs/server_*.log"
    exit 1
fi
echo ""

# ============================================================================
# STEP 5: MAKE SCRIPTS EXECUTABLE
# ============================================================================

echo "📝 Step 5: Setting up scripts..."
chmod +x collect_training_data.sh 2>/dev/null || true
chmod +x test_duke_performance.sh 2>/dev/null || true
chmod +x advanced_tasks.py
echo "✅ Scripts ready"
echo ""

# ============================================================================
# STEP 6: CREATE AUTO-RETRAINING SCRIPT
# ============================================================================

echo "🤖 Step 6: Creating auto-retraining monitor..."

cat > auto_retrain.sh << 'EOF'
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
EOF

chmod +x auto_retrain.sh
echo "✅ Auto-retraining monitor created"
echo ""

# ============================================================================
# STEP 7: CREATE MONITORING DASHBOARD
# ============================================================================

echo "📊 Step 7: Creating monitoring dashboard..."

cat > monitor.sh << 'EOF'
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
EOF

chmod +x monitor.sh
echo "✅ Monitoring dashboard created"
echo ""

# ============================================================================
# STEP 8: INSTRUCTIONS FOR USER
# ============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 PRODUCTION DEPLOYMENT READY!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✅ Server running: PID $SERVER_PID"
echo "📊 Dashboard: http://localhost:8000/dashboard"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 NEXT STEPS - Run in NEW TERMINALS:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Terminal 2 - DATA COLLECTION:"
echo "  while true; do"
echo "    ./collect_training_data.sh"
echo "    sleep 60"
echo "  done"
echo ""
echo "Terminal 3 - AUTO-RETRAINING:"
echo "  ./auto_retrain.sh"
echo ""
echo "Terminal 4 - LIVE MONITORING:"
echo "  ./monitor.sh"
echo ""
echo "Terminal 5 - SUBMIT DIVERSE TASKS:"
echo "  python3 advanced_tasks.py comprehensive 50"
echo "  # OR for specific domains:"
echo "  python3 advanced_tasks.py domain programming 20"
echo "  python3 advanced_tasks.py domain machine_learning 15"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📚 DOCUMENTATION:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📖 Deployment Guide:    deployment_steps.md"
echo "📖 Advanced Tasks:      advanced_tasks.py --help"
echo "📖 Specialists Guide:   specialists_guide.md"
echo "📖 Production Playbook: production_deployment.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 TARGET MILESTONES:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏱️  In 1 hour:    ~700 samples"
echo "⏱️  In 6 hours:   ~2,400 samples"
echo "⏱️  In 24 hours:  ~5,200 samples ✅ SPECIALISTS READY!"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "✨ Duke ML is now in PRODUCTION MODE! ✨"
echo ""
EOF

chmod +x quick_start.sh

# ============================================================================
# FINAL OUTPUT
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         🎉 DEPLOYMENT COMPLETE - READY TO GO! 🎉           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Server: Running on http://localhost:8000"
echo "✅ Dashboard: http://localhost:8000/dashboard"
echo "✅ Scripts: All ready in current directory"
echo ""
echo "🚀 START DATA COLLECTION IN NEW TERMINALS:"
echo ""
echo "   Terminal 2:"
echo "   while true; do ./collect_training_data.sh; sleep 60; done"
echo ""
echo "   Terminal 3:"
echo "   ./auto_retrain.sh"
echo ""
echo "   Terminal 4:"
echo "   ./monitor.sh"
echo ""
echo "   Terminal 5:"
echo "   python3 advanced_tasks.py comprehensive 50"
echo ""
echo "📊 Monitor progress at: http://localhost:8000/dashboard"
echo ""
