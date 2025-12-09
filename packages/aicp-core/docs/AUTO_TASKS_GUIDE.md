# AUTO-TASK SUBMITTER GUIDE
# Automatically submit tasks to your coordinator and help Duke learn

## 🚀 QUICK START

```bash
# Make sure coordinator is running
python coordinator_api_fixed.py

# In another terminal, run auto-tasks
python auto_tasks.py

# That's it! Tasks are being submitted automatically
```

---

## 📋 USAGE MODES

### 1. **Submit 10 Random Tasks (DEFAULT)**
```bash
python auto_tasks.py
```
- Submits 10 random tasks from the sample list
- 2-second delay between submissions
- Perfect for quick testing

### 2. **Submit ALL Tasks**
```bash
python auto_tasks.py all
```
- Submits all 30 sample tasks
- Takes ~60 seconds
- Great for initial data collection

### 3. **Submit Specific Number**
```bash
python auto_tasks.py count 50
```
- Submits 50 random tasks (repeating from sample list)
- Useful for testing with larger datasets

### 4. **Batch Submission**
```bash
python auto_tasks.py batch 5 10
```
- 5 batches × 10 tasks per batch = 50 total tasks
- 60-second delay between batches
- Lets you watch Duke training progress

### 5. **Continuous Submission (RECOMMENDED)**
```bash
python auto_tasks.py continuous
```
- 10 batches × 5 tasks each
- Automatic, hands-off
- Perfect for letting Duke learn over time

---

## 🎯 RECOMMENDED WORKFLOW

### For Immediate Testing
```bash
# Terminal 1: Start coordinator
python coordinator_api_fixed.py

# Terminal 2: Submit initial tasks
python auto_tasks.py all

# Terminal 3: Watch dashboard
open http://localhost:8000/dashboard
```

### For Duke Learning (BEST)
```bash
# Terminal 1: Start coordinator
python coordinator_api_fixed.py

# Terminal 2: Continuous submission (let it run)
python auto_tasks.py continuous

# Terminal 3: Monitor dashboard in real-time
# Refresh: http://localhost:8000/dashboard
```

### For Custom Testing
```bash
# Get 100+ samples to trigger Duke training
python auto_tasks.py count 100

# Then check status
curl http://localhost:8000/model/status
```

---

## 📊 WHAT YOU'LL SEE

### Console Output
```
🤖 AICP AUTO-TASK SUBMITTER
====================================================================
Coordinator URL: http://localhost:8000
Buyer ID: buyer-test-001
Delay Between Tasks: 2s
====================================================================

📝 Will submit 10 tasks

[1/10] Submitting: What is the capital of France?...
    ✅ Task a1b2c3d4 submitted (Price: 200,000 sat)
[2/10] Submitting: Explain quantum computing...
    ✅ Task e5f6g7h8 submitted (Price: 1,000,000 sat)
...
✅ Submitted 10/10 tasks successfully!

📊 SYSTEM STATUS
====================================================================
Tasks Submitted: 10
Training Samples: 5
🧠 Duke Status: Untrained (needs 95 more samples)
====================================================================
```

### Dashboard Updates
```
After 30 tasks:
- Training samples: 30/100
- Duke: Still untrained

After 100 tasks:
- Training samples: 100/100
- Duke: v1 trained (88% accuracy)

After 200 tasks:
- Training samples: 200+
- Duke: v2 trained (91% accuracy)
```

---

## ⚙️ CUSTOMIZATION

### Edit Configuration
Edit the top of `auto_tasks.py`:

```python
COORDINATOR_URL = "http://localhost:8000"  # Your coordinator URL
BUYER_ID = "buyer-test-001"                # Test buyer ID
PASSWORD = "testpassword123"               # Test password

# Add/modify SAMPLE_TASKS list with your own tasks
SAMPLE_TASKS = [
    {"description": "Your custom task", "complexity": 5},
    # ... more tasks
]
```

### Change Delays
```bash
# Modify delays in continuous_submission call
# delay_between_tasks: seconds between each task
# delay_between_batches: seconds between batches
```

---

## 🧠 HELPING DUKE LEARN

### What Duke Learns From
- **Task descriptions** (what to do)
- **Task complexity** (1-10 scale)
- **OpenAI results** (how to solve it)

### Optimal Data Mix
- ✅ Mix of simple (1-3), medium (4-6), complex (7-10) tasks
- ✅ Diverse topics (technical, business, creative, etc.)
- ✅ 100+ samples to trigger first training
- ✅ 200+ samples for meaningful improvement

### Current Task Types
- Simple Q&A (geography, history, trivia)
- Science & nature explanations
- Technical concepts
- Complex analysis & design
- Business strategy
- Creative content

---

## 📈 MONITORING PROGRESS

### Check Status
```bash
# Get model status
curl http://localhost:8000/model/status \
  -H "Authorization: Bearer <token>"

# Expected output:
# {
#   "status": "ready",
#   "version": 2,
#   "accuracy": 0.91,
#   "f1_score": 0.90,
#   "training_samples": 150,
#   "is_production": true
# }
```

### Watch Logs
```bash
# In coordinator terminal, watch for Duke updates
# Look for:
# "📚 Collected 100 training samples for Duke"
# "🧠 Duke training with 100 samples (v1)"
# "🎯 Duke v1 promoted! (accuracy: 91%)"
```

### Dashboard Monitoring
- **System Status**: Total tasks, success rate
- **Duke Status**: Current version, accuracy, training progress
- **Recent Tasks**: See results as they complete
- **Agent Performance**: Track earnings

---

## ⏱️ TIMING ESTIMATES

### To Get First Duke Training
```
Sample Rate: ~1 task per 2 seconds
100 tasks needed: ~200 seconds (~3.3 minutes)
First training: v1 at ~88% accuracy
```

### To Get Multiple Versions
```
Batch 1: 100 tasks → v1 (88%)
Batch 2: 100 tasks → v2 (91%)
Batch 3: 100 tasks → v3 (94%)
Batch 4: 100 tasks → v4 (95%)+ → Production Ready
```

### Full Learning Cycle
```
Week 1: Collect 500+ samples, train v1-3
Week 2: 1000+ samples, train v4-6
Week 3: 1500+ samples, train v7-10
Month 2: 2000+ samples, Duke at 95%+ accuracy
```

---

## 🔧 TROUBLESHOOTING

### "Connection refused"
```bash
# Make sure coordinator is running
python coordinator_api_fixed.py

# Check it's accessible
curl http://localhost:8000/health
```

### "Login failed"
```bash
# Check PASSWORD matches your actual password
# Default: "testpassword123"

# Edit auto_tasks.py to use correct credentials
```

### "Rate limiting errors"
```bash
# Increase delay_between_tasks
# Or reduce tasks_per_batch
python auto_tasks.py batch 10 5  # More time between tasks
```

### Tasks stuck in "processing"
```bash
# Check OpenAI API key in coordinator
echo $OPENAI_API_KEY

# Check coordinator logs for OpenAI errors
# Verify API key is valid at: https://platform.openai.com/api/keys
```

---

## 💡 TIPS

1. **Run Overnight**: Start continuous mode and let it run
2. **Monitor Dashboard**: Keep dashboard open to see progress
3. **Check Logs**: Watch coordinator logs for training events
4. **Vary Tasks**: Use mix of complexities and topics
5. **Regular Backups**: Database grows with each task
6. **Track Accuracy**: Note Duke's improvement over time

---

## 🎯 GOALS

- **After 100 tasks**: Duke trains, first version created
- **After 200 tasks**: Better models auto-promoted
- **After 500 tasks**: Duke hitting 90%+ accuracy
- **After 1000 tasks**: Duke ready for production use

---

## 📊 EXAMPLE FULL WORKFLOW

```bash
# Terminal 1: Start coordinator
$ python coordinator_api_fixed.py
🚀 Starting AICP Coordinator Service v3.3.0
✅ Duke Learning Pipeline enabled
✅ Server ready! Dashboard: http://localhost:8000/dashboard

# Terminal 2: Auto-submit tasks
$ python auto_tasks.py continuous
🤖 AICP AUTO-TASK SUBMITTER
📝 Will submit 50 tasks (5 batches × 10 each)

🔄 BATCH 1/5
  📤 What is the capital of France?... ✅ a1b2c3
  📤 Explain quantum computing... ✅ d4e5f6
  ... (10 tasks)
  📊 Training samples collected: 10

🔄 BATCH 2/5
  ... (10 more tasks)
  📊 Training samples collected: 20

... (batches 3-5)

✅ Continuous submission complete!
Total tasks submitted: 50

📊 SYSTEM STATUS
====================================================================
Training Samples: 50
🧠 Duke Status: Untrained (needs 50 more samples)
====================================================================

# Terminal 3: Monitor dashboard
$ open http://localhost:8000/dashboard
# Refresh to see real-time updates
# After 100 tasks: Duke trains, v1 created
# After 200 tasks: Better versions trained
```

---

**Your system is now auto-populated! Duke will learn from all tasks. 🚀🧠**
