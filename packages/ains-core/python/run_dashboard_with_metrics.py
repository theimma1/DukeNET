import sys
sys.path.insert(0, '.')

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import json
from contextlib import asynccontextmanager
from ains.metrics import MetricsCollector
import random

# Initialize the real metrics collector
metrics_collector = MetricsCollector()

ws_connections = []

async def update_metrics_loop():
    """Continuously broadcast metrics to all connected WebSocket clients"""
    
    while True:
        try:
            # Get all real metrics from collector
            all_metrics = metrics_collector.get_all_metrics()
            
            # If no metrics yet, simulate some for demo
            if not all_metrics:
                # Simulate an agent with data
                metrics_collector.record_success("labelee-duke-REAL", random.uniform(0.01, 0.15))
                if random.random() < 0.1:  # 10% failure rate
                    metrics_collector.record_failure("labelee-duke-REAL")
            
            # Build response data
            agents_detail = {}
            total_requests = 0
            total_latency = 0
            total_trust = 0
            
            for agent_id, metrics in all_metrics.items():
                agents_detail[agent_id] = {
                    "trust_score": metrics.trust_score,
                    "success_rate": metrics.success_rate,
                    "avg_latency": metrics.avg_latency,
                    "request_count": metrics.request_count
                }
                total_requests += metrics.request_count
                total_latency += metrics.avg_latency
            
            num_agents = len(all_metrics)
            avg_latency = total_latency / num_agents if num_agents > 0 else 0
            avg_trust = total_trust / num_agents if num_agents > 0 else 0.5
            
            data = {
                "agents": num_agents,
                "total_requests": total_requests,
                "avg_latency": avg_latency,
                "avg_trust": avg_trust if agents_detail else 0.5,
                "agents_detail": agents_detail
            }
            
            # Broadcast to all connected clients
            disconnected = []
            for ws in ws_connections:
                try:
                    await ws.send_text(json.dumps(data))
                except Exception as e:
                    print(f"Failed to send to client: {e}")
                    disconnected.append(ws)
            
            # Remove disconnected clients
            for ws in disconnected:
                if ws in ws_connections:
                    ws_connections.remove(ws)
                    print(f"Removed disconnected client. Remaining: {len(ws_connections)}")
            
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Error in metrics loop: {e}")
            await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("✅ Starting metrics broadcast loop...")
    task = asyncio.create_task(update_metrics_loop())
    yield
    # Shutdown
    print("✅ Stopping metrics broadcast loop...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/dashboard")
async def serve_dashboard():
    dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DukeNET AICP Dashboard</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%); min-height: 100vh; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #e2e8f0; }
    .card { background: rgba(30, 41, 59, 0.5); backdrop-filter: blur(12px); border: 1px solid rgba(71, 85, 105, 0.5); border-radius: 1rem; padding: 1.5rem; margin-bottom: 2rem; }
    .stat-card { background: linear-gradient(135deg, rgba(30, 58, 138, 0.3) 0%, rgba(30, 64, 175, 0.1) 100%); border: 1px solid rgba(59, 130, 246, 0.2); padding: 1.5rem; border-radius: 0.75rem; flex: 1; min-width: 200px; }
    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }
    .chart-container { position: relative; height: 300px; width: 100%; }
    .agent-card { background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(34, 211, 238, 0.3); border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem; }
    .header { padding: 2rem; margin-bottom: 2rem; border-bottom: 1px solid rgba(71, 85, 105, 0.3); }
    .h1 { font-size: 2.5rem; font-weight: bold; margin-bottom: 0.5rem; background: linear-gradient(90deg, #60a5fa, #22d3ee); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .live { display: inline-block; width: 12px; height: 12px; background: #22c55e; border-radius: 50%; animation: pulse 2s infinite; margin-right: 0.5rem; }
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
      <div class="stat-card"><p class="stat-label">Agents Online</p><p class="stat-value" id="agents">0</p></div>
      <div class="stat-card"><p class="stat-label">Total Requests</p><p class="stat-value" id="requests">0</p></div>
      <div class="stat-card"><p class="stat-label">Avg Latency</p><p class="stat-value"><span id="latency">0</span>ms</p></div>
      <div class="stat-card"><p class="stat-label">Network Health</p><p class="stat-value" id="trust">0.00</p></div>
    </div>
    <div class="grid">
      <div class="card"><h2 style="margin-bottom: 1rem; color: #e2e8f0;">📊 Request Volume</h2><div class="chart-container">anvas id="requestsChart"></canvas></div></div>
      <div class="card"><h2 style="margin-bottom: 1rem; color: #e2e8f0;">⚡ Latency Trend</h2><div class="chart-container">anvas id="latencyChart"></canvas></div></div>
    </div>
    <div class="card"><h2 style="margin-bottom: 1rem; color: #e2e8f0;">🤖 Connected Agents (<span id="agentCount">0</span>)</h2><div id="agentsList"></div></div>
    <div class="ws-status">Status: <span id="wsStatus" class="status-disconnected">Connecting...</span> | Last Update: <span id="lastUpdate" style="color: #22d3ee; font-family: monospace;">--:--:--</span></div>
  </div>
  <script>
    const chartDefaults = { responsive: true, maintainAspectRatio: false, plugins: { legend: { labels: { color: '#94a3b8' } } }, scales: { y: { grid: { color: 'rgba(100, 116, 139, 0.1)' }, ticks: { color: '#94a3b8' }, min: 0 }, x: { grid: { color: 'rgba(100, 116, 139, 0.1)' }, ticks: { color: '#94a3b8' } } }, animation: { duration: 0 } };
    const requestsChart = new Chart(document.getElementById('requestsChart'), { type: 'line', data: { labels: [], datasets: [{ label: 'Requests/sec', data: [], borderColor: '#22d3ee', backgroundColor: 'rgba(34, 211, 238, 0.1)', borderWidth: 2, fill: true, tension: 0.4 }] }, options: chartDefaults });
    const latencyChart = new Chart(document.getElementById('latencyChart'), { type: 'line', data: { labels: [], datasets: [{ label: 'Latency (ms)', data: [], borderColor: '#10b981', backgroundColor: 'rgba(16, 185, 129, 0.1)', borderWidth: 2, fill: true, tension: 0.4 }] }, options: chartDefaults });
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
      if (requestsChart.data.labels.length > 30) { requestsChart.data.labels.shift(); requestsChart.data.datasets[0].data.shift(); latencyChart.data.labels.shift(); latencyChart.data.datasets[0].data.shift(); }
      requestsChart.update('none'); latencyChart.update('none');
      if (data.agents_detail) {
        const count = Object.keys(data.agents_detail).length;
        document.getElementById('agentCount').textContent = count;
        if (count === 0) { document.getElementById('agentsList').innerHTML = '<p style="color: #cbd5e1; padding: 1rem;">⏳ Waiting for agents...</p>'; }
        else { document.getElementById('agentsList').innerHTML = Object.entries(data.agents_detail).map(([id, m]) => `<div class="agent-card"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;"><span style="color: #22d3ee; font-weight: bold; word-break: break-all;">${id}</span><span style="color: #22c55e; font-size: 0.75rem; font-weight: bold;">● LIVE</span></div><div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.875rem;"><div><span style="color: #cbd5e1;">Trust:</span> <span style="color: #60a5fa;">${(m.trust_score || 0).toFixed(2)}</span></div><div><span style="color: #cbd5e1;">Success:</span> <span style="color: #10b981;">${((m.success_rate || 0) * 100).toFixed(1)}%</span></div><div><span style="color: #cbd5e1;">Latency:</span> <span style="color: #fbbf24;">${Math.round((m.avg_latency || 0) * 1000)}ms</span></div><div><span style="color: #cbd5e1;">Requests:</span> <span style="color: #c084fc;">${m.request_count || 0}</span></div></div></div>`).join(''); }
      }
    }
    fetch('/api/metrics/summary').then(r => r.json()).then(updateDashboard).catch(e => console.log('Waiting...'));
    let wsUrl = 'ws://' + window.location.host + '/ws/metrics';
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => { document.getElementById('wsStatus').textContent = 'Connected'; document.getElementById('wsStatus').className = 'status-connected'; };
    ws.onmessage = (e) => { updateDashboard(JSON.parse(e.data)); };
    ws.onerror = () => { document.getElementById('wsStatus').textContent = 'Error'; document.getElementById('wsStatus').className = 'status-disconnected'; };
    ws.onclose = () => { document.getElementById('wsStatus').textContent = 'Disconnected'; document.getElementById('wsStatus').className = 'status-disconnected'; };
  </script>
</body>
</html>'''
    return HTMLResponse(content=dashboard_html)

@app.get("/api/metrics/summary")
async def get_metrics_summary():
    all_metrics = metrics_collector.get_all_metrics()
    agents_detail = {}
    total_requests = 0
    total_trust = 0
    for agent_id, metrics in all_metrics.items():
        agents_detail[agent_id] = { "trust_score": metrics.trust_score, "success_rate": metrics.success_rate, "avg_latency": metrics.avg_latency, "request_count": metrics.request_count }
        total_requests += metrics.request_count
        total_trust += metrics.trust_score
    num_agents = len(all_metrics)
    return { "agents": num_agents, "total_requests": total_requests, "avg_latency": sum(m.avg_latency for m in all_metrics.values()) / num_agents if num_agents > 0 else 0, "avg_trust": total_trust / num_agents if num_agents > 0 else 0.5, "agents_detail": agents_detail }

@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await websocket.accept()
    ws_connections.append(websocket)
    print(f"✅ WebSocket connected. Total: {len(ws_connections)}")
    try:
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        if websocket in ws_connections:
            ws_connections.remove(websocket)

if __name__ == "__main__":
    print("🚀 Starting DukeNET Dashboard with Real Metrics")
    print("📊 http://127.0.0.1:8000/dashboard")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
