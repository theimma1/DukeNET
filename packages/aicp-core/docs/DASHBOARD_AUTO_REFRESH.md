# DASHBOARD REFRESH ADDON
# Add auto-refresh to your coordinator dashboard

## 🔄 UPDATE YOUR COORDINATOR

Replace the dashboard HTML section in `coordinator_api_fixed.py` with this updated version that includes:
- ✅ Auto-refresh every N seconds
- ✅ Manual refresh button
- ✅ Refresh indicator
- ✅ Configurable refresh interval
- ✅ Live data updates

### STEPS:

1. Open `coordinator_api_fixed.py`
2. Find the line: `@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])`
3. Replace the entire HTML section (from `html = f"""...` to the end) with the code below
4. Save and restart the coordinator

---

### UPDATED DASHBOARD CODE WITH AUTO-REFRESH

```python
@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard(db: Session = Depends(get_db)):
    """Interactive dashboard with Duke metrics and auto-refresh"""
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    processing_tasks = db.query(Task).filter(Task.status == "processing").count()
    success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    agents = db.query(Agent).all()
    total_agents = len(agents)
    total_balance = sum(a.balance_satoshis for a in agents)
    
    # Duke metrics
    training_samples = db.query(TrainingData).count()
    latest_version = db.query(ModelVersion).filter(
        ModelVersion.is_production == True
    ).first()
    duke_accuracy = latest_version.validation_accuracy if latest_version else 0
    
    agent_rows = ""
    for agent in agents:
        agent_rows += f"<tr><td>{agent.name}</td><td>{agent.success_rate*100:.0f}%</td><td>{agent.reputation_multiplier:.2f}x</td><td>{agent.balance_satoshis:,} sat</td></tr>"
    
    recent_tasks = db.query(Task).order_by(Task.created_at.desc()).limit(10).all()
    recent_tasks_rows = ""
    for task in recent_tasks:
        status_color = {"completed": "#10b981", "failed": "#ef4444", "processing": "#8b5cf6"}.get(task.status, "#f59e0b")
        recent_tasks_rows += f"<tr onclick=\"showTaskDetails('{task.id}')\" style='cursor: pointer;'><td>{task.id}</td><td>{task.description[:40]}...</td><td><span style='color: {status_color};'>{task.status}</span></td><td>{task.price_satoshis:,}</td></tr>"
    
    tasks_json = json.dumps([{
        'id': t.id,
        'description': t.description,
        'status': t.status,
        'result': t.result or 'No result yet',
    } for t in recent_tasks])
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AICP Dashboard + Duke Learning</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: #f1f5f9; padding: 20px; min-height: 100vh; }}
.container {{ max-width: 1400px; margin: 0 auto; }}
.header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }}
h1 {{ text-align: center; flex: 1; font-size: 2.5em; margin: 0; }}
.refresh-controls {{ display: flex; gap: 15px; align-items: center; }}
.refresh-btn {{ padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s; }}
.refresh-btn:hover {{ background: #2563eb; transform: scale(1.05); }}
.refresh-btn:active {{ transform: scale(0.95); }}
.refresh-indicator {{ display: flex; align-items: center; gap: 8px; font-size: 0.9em; color: #cbd5e1; }}
.refresh-dot {{ width: 8px; height: 8px; background: #10b981; border-radius: 50%; animation: pulse 2s infinite; }}
.refresh-dot.updating {{ animation: spin 0.6s linear; }}
@keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
@keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
.subtitle {{ text-align: center; margin-bottom: 30px; color: #cbd5e1; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
.card {{ background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 12px; padding: 20px; backdrop-filter: blur(10px); }}
.card h2 {{ font-size: 0.9em; color: #cbd5e1; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }}
.card-value {{ font-size: 2em; font-weight: bold; color: #3b82f6; }}
.card-subtext {{ font-size: 0.9em; color: #94a3b8; margin-top: 10px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 12px; overflow: hidden; }}
th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid rgba(100, 116, 139, 0.2); }}
th {{ background: rgba(15, 23, 42, 0.8); font-weight: 600; color: #cbd5e1; }}
tr:hover {{ background: rgba(51, 65, 85, 0.3); }}
h2 {{ margin-top: 40px; margin-bottom: 20px; }}
.refresh-interval {{ display: flex; align-items: center; gap: 10px; font-size: 0.9em; color: #cbd5e1; }}
.refresh-interval select {{ padding: 5px 10px; background: rgba(30, 41, 59, 0.8); color: #f1f5f9; border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 6px; cursor: pointer; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
  <h1>🤖 AICP Marketplace + 🧠 Duke Learning</h1>
  <div class="refresh-controls">
    <button class="refresh-btn" onclick="manualRefresh()">🔄 Refresh Now</button>
    <div class="refresh-interval">
      <label>Auto-refresh:</label>
      <select id="refreshInterval" onchange="changeRefreshInterval()">
        <option value="0">Off</option>
        <option value="5" selected>5s</option>
        <option value="10">10s</option>
        <option value="15">15s</option>
        <option value="30">30s</option>
        <option value="60">60s</option>
      </select>
    </div>
    <div class="refresh-indicator">
      <div class="refresh-dot" id="refreshDot"></div>
      <span id="lastRefresh">Just now</span>
    </div>
  </div>
</div>

<p class="subtitle">OpenAI executes tasks → Duke learns from everything</p>

<div class="grid">
<div class="card">
<h2>System Status</h2>
<div class="card-value">✅ Online</div>
<div class="card-subtext">Database: Connected</div>
<div class="card-subtext">AI: OpenAI GPT-3.5</div>
</div>

<div class="card">
<h2>Total Tasks</h2>
<div class="card-value" id="totalTasksValue">{total_tasks}</div>
<div class="card-subtext">Completed: <span id="completedTasksValue">{completed_tasks}</span></div>
<div class="card-subtext">Processing: <span id="processingTasksValue">{processing_tasks}</span></div>
</div>

<div class="card">
<h2>Success Rate</h2>
<div class="card-value" id="successRateValue">{success_rate:.1f}%</div>
<div class="card-subtext" id="successTasksValue">{completed_tasks} successful tasks</div>
</div>

<div class="card">
<h2>Duke Learning Status</h2>
<div class="card-value" id="dukeVersionValue">v{latest_version.version_number if latest_version else 0}</div>
<div class="card-subtext">Accuracy: <span id="dukeAccuracyValue">{duke_accuracy*100:.1f}%</span></div>
<div class="card-subtext">Samples: <span id="dukeSamplesValue">{training_samples}/100</span></div>
</div>
</div>

<h2>Agent Performance</h2>
<table>
<thead><tr><th>Agent</th><th>Success Rate</th><th>Reputation</th><th>Balance (sat)</th></tr></thead>
<tbody id="agentTableBody">{agent_rows if agent_rows else "<tr><td colspan='4'>No agents</td></tr>"}</tbody>
</table>

<h2>Recent Tasks (Duke learns from all results)</h2>
<table>
<thead><tr><th>Task ID</th><th>Description</th><th>Status</th><th>Price (sat)</th></tr></thead>
<tbody id="tasksTableBody">{recent_tasks_rows if recent_tasks_rows else "<tr><td colspan='4' style='text-align: center;'>No tasks yet</td></tr>"}</tbody>
</table>
</div>

<script>
const tasksData = {tasks_json};
let autoRefreshInterval = null;
let lastRefreshTime = new Date();

function showTaskDetails(taskId) {{
  const task = tasksData.find(t => t.id === taskId);
  if (!task) return;
  alert(`Task: ${{task.id}}\n\n${{task.result}}`);
}}

function updateLastRefreshTime() {{
  const now = new Date();
  const diff = now - lastRefreshTime;
  if (diff < 1000) {{
    document.getElementById('lastRefresh').textContent = 'Just now';
  }} else if (diff < 60000) {{
    document.getElementById('lastRefresh').textContent = Math.floor(diff / 1000) + 's ago';
  }} else {{
    document.getElementById('lastRefresh').textContent = Math.floor(diff / 60000) + 'm ago';
  }}
}}

async function manualRefresh() {{
  const dot = document.getElementById('refreshDot');
  dot.classList.add('updating');
  
  try {{
    const response = await fetch(window.location.href);
    const html = await response.text();
    
    // Parse the response to extract new data
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    // Update cards
    const cards = tempDiv.querySelectorAll('.card-value');
    const currentCards = document.querySelectorAll('.card-value');
    cards.forEach((card, index) => {{
      if (currentCards[index]) {{
        currentCards[index].textContent = card.textContent;
      }}
    }});
    
    // Update subtexts
    const subtexts = tempDiv.querySelectorAll('.card-subtext');
    const currentSubtexts = document.querySelectorAll('.card-subtext');
    subtexts.forEach((text, index) => {{
      if (currentSubtexts[index]) {{
        currentSubtexts[index].textContent = text.textContent;
      }}
    }});
    
    // Update tables
    const agentTable = tempDiv.querySelector('#agentTableBody');
    if (agentTable) {{
      document.querySelector('#agentTableBody').innerHTML = agentTable.innerHTML;
    }}
    
    const tasksTable = tempDiv.querySelector('#tasksTableBody');
    if (tasksTable) {{
      document.querySelector('#tasksTableBody').innerHTML = tasksTable.innerHTML;
    }}
    
    lastRefreshTime = new Date();
    updateLastRefreshTime();
  }} catch (error) {{
    console.error('Refresh failed:', error);
  }} finally {{
    dot.classList.remove('updating');
  }}
}}

function changeRefreshInterval() {{
  const interval = parseInt(document.getElementById('refreshInterval').value);
  
  // Clear existing interval
  if (autoRefreshInterval) {{
    clearInterval(autoRefreshInterval);
    autoRefreshInterval = null;
  }}
  
  // Set new interval if not 0
  if (interval > 0) {{
    autoRefreshInterval = setInterval(manualRefresh, interval * 1000);
    console.log(`Auto-refresh enabled: every ${{interval}} seconds`);
  }} else {{
    console.log('Auto-refresh disabled');
  }}
}}

// Update last refresh time display every second
setInterval(updateLastRefreshTime, 1000);

// Initialize with selected interval
document.addEventListener('DOMContentLoaded', () => {{
  const interval = parseInt(document.getElementById('refreshInterval').value);
  if (interval > 0) {{
    autoRefreshInterval = setInterval(manualRefresh, interval * 1000);
  }}
  updateLastRefreshTime();
}});
</script>
</body>
</html>"""
    
    return HTMLResponse(content=html)
```

---

## ✨ NEW FEATURES

### 1. **Manual Refresh Button**
- Click 🔄 "Refresh Now" to update immediately
- No page reload needed

### 2. **Auto-Refresh Dropdown**
- Off (default)
- 5s ⭐ (Recommended - see live updates)
- 10s, 15s, 30s, 60s
- Switch anytime without restarting

### 3. **Refresh Indicator**
- Green dot shows status
- "Just now" / "5s ago" / "1m ago"
- Auto-updates every second

### 4. **Smart Data Updates**
- Updates cards, tables, and metrics
- No full page reload
- Preserves scroll position

---

## 🚀 HOW TO INSTALL

### Option 1: Replace Dashboard Function (Easiest)
1. Open `coordinator_api_fixed.py`
2. Find: `@app.get("/dashboard"...`
3. Replace entire function with code above
4. Save & restart coordinator

### Option 2: Full File Update
```bash
# Use the complete updated coordinator file
# (Available on request)
```

---

## 📊 USAGE

### After Installing:
```
1. Open http://localhost:8000/dashboard
2. Click dropdown, select "5s" (or your preference)
3. Dashboard auto-updates every 5 seconds
4. Watch metrics change in real-time
5. Click "🔄 Refresh Now" for instant update
```

### What Updates:
- Total tasks & status
- Success rate
- Duke version & accuracy
- Training samples progress
- Agent balances
- Recent tasks table

---

## 💡 TIPS

- **5s refresh**: Best for watching action live
- **10-15s**: Good balance (less network requests)
- **30-60s**: Light monitoring (less strain)
- **Off**: If you prefer manual refresh

---

**Your dashboard now refreshes automatically! 🔄✨**
