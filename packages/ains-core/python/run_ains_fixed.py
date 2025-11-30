import sys
sys.path.insert(0, '.')

from ains.api import app
from fastapi.responses import FileResponse
from fastapi import WebSocket
import uvicorn
import asyncio
import json

# Mock metrics storage
metrics_history = {
    "total_requests": 0,
    "avg_latency": 0,
    "avg_trust": 0.95,
    "agents": {}
}

ws_connections = []

@app.get("/dashboard")
async def serve_dashboard():
    dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AICP Agent Network Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
      min-height: 100vh;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #e2e8f0;
    }
    .card { 
      background: rgba(30, 41, 59, 0.5);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(71, 85, 105, 0.5);
      border-radius: 1rem;
      transition: all 0.3s ease;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }
    .stat-card { 
      background: linear-gradient(135deg, rgba(30, 58, 138, 0.3) 0%, rgba(30, 64, 175, 0.1) 100%);
      border: 1px solid rgba(59, 130, 246, 0.2);
      padding: 1.5rem;
      border-radius: 0.75rem;
      flex: 1;
      min-width: 200px;
    }
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
    .chart-container { position: relative; height: 300px; }
    canvas { max-height: 300px !important; }
    .agent-card { 
      background: rgba(30, 41, 59, 0.5); 
      border: 1px solid rgba(34, 211, 238, 0.3);
      border-radius: 0.5rem;
      padding: 1rem;
      margin-bottom: 1rem;
    }
    .header { padding: 2rem; margin-bottom: 2rem; border-bottom: 1px solid rgba(71, 85, 105, 0.3); }
    .h1 { font-size: 2.5rem; font-weight: bold; margin-bottom: 0.5rem; background: linear-gradient(90deg, #60a5fa, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .live { 
      display: inline-block;
      width: 12px;
      height: 12px;
      background: #22c55e;
      border-radius: 50%;
      animation: pulse 2s infinite;
      margin-right: 0.5rem;
    }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
    .stat-value { font-size: 2rem; font-weight: bold; color: #60a5fa; margin: 0.5rem 0; }
    .stat-label { color: #cbd5e1; font-size: 0.875rem; text-transform: uppercase; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
    .ws-status { padding: 1rem; text-align: center; color: #cbd5e1; }
    .status-connected { color: #22c55e; font-weight: bold; }
    .status-disconnected { color: #ef4444; font-weight: bold; }
  </style>
</head>
<body>
  <div class="header">
    <h1 class="h1"><span class="live"></span>DukeNET AICP Network</h1>
    <p style="color: #cbd5e1;">Real-time Agent Metrics & Performance</p>
  </div>

  <div style="padding: 0 2rem;">
    <div class="stat-grid">
      <div class="stat-card">
        <p class="stat-label">Agents Online</p>
        <p class="stat-value" id="agents">0</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">Total Requests</p>
        <p class="stat-value" id="requests">0</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">Avg Latency</p>
        <p class="stat-value"><span id="latency">0</span>ms</p>
      </div>
      <div class="stat-card">
        <p class="stat-label">Network Health</p>
        <p class="stat-value" id="trust">0.00</p>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h2 style="margin-bottom: 1rem; color: #e2e8f0;">📊 Request Volume</h2>
        <div class="chart-container">anvas id="requestsChart"></canvas></div>
      </div>
      <div class="card">
        <h2 style="margin-bottom: 1rem; color: #e2e8f0;">⚡ Latency Trend</h2>
        <div class="chart-container">anvas id="latencyChart"></canvas></div>
      </div>
    </div>

    <div class="card">
      <h2 style="margin-bottom: 1rem; color: #e2e8f0;">🤖 Connected Agents (<span id="agentCount">0</span>)</h2>
      <div id="agentsList"></div>
    </div>

    <div class="ws-status">
      Status: <span id="wsStatus" class="status-disconnected">Connecting...</span>
      | Last Update: <span id="lastUpdate" style="color: #22d3ee; font-family: monospace;">--:--:--</span>
    </div>
  </div>

  <script>
    const chartDefaults = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#94a3b8' } } },
      scales: {
        y: { grid: { color: 'rgba(100, 116, 139, 0.1)' }, ticks: { color: '#94a3b8' }, min: 0 },
        x: { grid: { color: 'rgba(100, 116, 139, 0.1)' }, ticks: { color: '#94a3b8' } }
      },
      animation: { duration: 0 }
    };

    const requestsChart = new Chart(document.getElementById('requestsChart'), {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Requests/sec', data: [], borderColor: '#22d3ee', backgroundColor: 'rgba(34, 211, 238, 0.1)', borderWidth: 2, fill: true, tension: 0.4 }] },
      options: chartDefaults
    });

    const latencyChart = new Chart(document.getElementById('latencyChart'), {
      type: 'line',
      data: { labels: [], datasets: [{ label: 'Latency (ms)', data: [], borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', borderWidth: 2, fill: true, tension: 0.4 }] },
      options: chartDefaults
    });

    function updateDashboard(data) {
      document.getElementById('agents').textContent = data.agents || 0;
      document.getElementById('requests').textContent = data.total_requests || 0;
      document.getElementById('latency').textContent = Math.round((data.avg_latency || 0) * 1000);
      document.getElementById('trust').textContent = (data.avg_trust || 0).toFixed(2);
      document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();

      const now = new Date().toLocaleTimeString('en-US', { hour12: false });
      requestsChart.data.labels.push(now);
      requestsChart.data.datasets[0].data.push(data.total_requests || 0);
      latencyChart.data.labels.push(now);
      latencyChart.data.datasets[0].data.push(Math.round((data.avg_latency || 0) * 1000));

      if (requestsChart.data.labels.length > 30) {
        requestsChart.data.labels.shift();
        requestsChart.data.datasets[0].data.shift();
        latencyChart.data.labels.shift();
        latencyChart.data.datasets[0].data.shift();
      }

      requestsChart.update('none');
      latencyChart.update('none');

      if (data.agents_detail) {
        document.getElementById('agentCount').textContent = Object.keys(data.agents_detail).length;
        document.getElementById('agentsList').innerHTML = Object.entries(data.agents_detail).map(([id, m]) => `
          <div class="agent-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
              <span style="color: #22d3ee; font-weight: bold; word-break: break-all;">${id}</span>
              <span style="color: #22c55e; font-size: 0.75rem; font-weight: bold;">● LIVE</span>
            </div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.875rem;">
              <div><span style="color: #cbd5e1;">Trust:</span> <span style="color: #60a5fa;">${(m.trust_score || 0).toFixed(2)}</span></div>
              <div><span style="color: #cbd5e1;">Success:</span> <span style="color: #10b981;">${((m.success_rate || 0) * 100).toFixed(1)}%</span></div>
              <div><span style="color: #cbd5e1;">Latency:</span> <span style="color: #fbbf24;">${Math.round((m.avg_latency || 0) * 1000)}ms</span></div>
              <div><span style="color: #cbd5e1;">Requests:</span> <span style="color: #c084fc;">${m.request_count || 0}</span></div>
            </div>
          </div>
        `).join('');
      }
    }

    // Fetch initial metrics
    fetch('/api/metrics/summary').then(r => r.json()).then(updateDashboard).catch(e => console.log('Waiting for metrics...'));

    // Connect to WebSocket using current window location
    let wsUrl;
    if (window.location.protocol === 'https:') {
      wsUrl = 'wss://' + window.location.host + '/ws/metrics';
    } else {
      wsUrl = 'ws://' + window.location.host + '/ws/metrics';
    }

    console.log('Connecting to:', wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      document.getElementById('wsStatus').textContent = 'Connected';
      document.getElementById('wsStatus').className = 'status-connected';
    };

    ws.onmessage = (e) => {
      console.log('Received:', e.data);
      updateDashboard(JSON.parse(e.data));
    };

    ws.onerror = (e) => {
      console.log('WebSocket error:', e);
      document.getElementById('wsStatus').textContent = 'Connection Error';
      document.getElementById('wsStatus').className = 'status-disconnected';
    };

    ws.onclose = () => {
      console.log('WebSocket closed');
      document.getElementById('wsStatus').textContent = 'Disconnected';
      document.getElementById('wsStatus').className = 'status-disconnected';
    };
  </script>
</body>
</html>'''
    return FileResponse(content=dashboard_html, media_type="text/html")


@app.get("/api/metrics/summary")
async def get_metrics_summary():
    return {
        "agents": len(metrics_history.get("agents", {})),
        "total_requests": metrics_history.get("total_requests", 0),
        "avg_latency": metrics_history.get("avg_latency", 0),
        "avg_trust": metrics_history.get("avg_trust", 0.95),
        "agents_detail": metrics_history.get("agents", {})
    }


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await websocket.accept()
    ws_connections.append(websocket)
    print(f"✅ WebSocket connected. Total connections: {len(ws_connections)}")
    
    try:
        while True:
            data = {
                "agents": len(metrics_history.get("agents", {})),
                "total_requests": metrics_history.get("total_requests", 0),
                "avg_latency": metrics_history.get("avg_latency", 0),
                "avg_trust": metrics_history.get("avg_trust", 0.95),
                "agents_detail": metrics_history.get("agents", {})
            }
            await websocket.send_text(json.dumps(data))
            await asyncio.sleep(2)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        if websocket in ws_connections:
            ws_connections.remove(websocket)


@app.get("/api/metrics/agents")
async def get_agents():
    return metrics_history.get("agents", {})


async def update_metrics_loop():
    """Simulate metrics data for demo"""
    import random
    iteration = 0
    
    while True:
        iteration += 1
        
        metrics_history["total_requests"] = iteration * 5
        metrics_history["avg_latency"] = random.uniform(20, 150) / 1000
        metrics_history["avg_trust"] = 0.90 + random.uniform(-0.05, 0.05)
        
        metrics_history["agents"] = {
            "labelee-duke-REAL": {
                "trust_score": 0.95 + random.uniform(-0.1, 0.05),
                "success_rate": 0.98 + random.uniform(-0.1, 0.01),
                "avg_latency": random.uniform(30, 120) / 1000,
                "request_count": iteration * 3
            }
        }
        
        await asyncio.sleep(2)


@app.on_event("startup")
async def startup():
    asyncio.create_task(update_metrics_loop())
    print("✅ Metrics update loop started")


if __name__ == "__main__":
    print('🚀 Starting AINS API with Full Dashboard & Metrics')
    print('📊 Dashboard: http://127.0.0.1:8000/dashboard')
    print('📈 Metrics API: http://127.0.0.1:8000/api/metrics/summary')
    print('🔌 WebSocket: ws://127.0.0.1:8000/ws/metrics')
    print()
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='info')
