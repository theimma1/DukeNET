import sys
import os
sys.path.insert(0, '.')

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import json
import random
from contextlib import asynccontextmanager
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict

# ========== EMBEDDED METRICS ==========

@dataclass
class AgentMetrics:
    agent_id: str
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_latency: float = 0.0
    trust_score: float = 0.5
    last_seen: datetime = field(default_factory=datetime.now)
    
    @property
    def success_rate(self) -> float:
        return 1.0 if self.request_count == 0 else self.success_count / self.request_count
    
    @property
    def avg_latency(self) -> float:
        return 0.0 if self.request_count == 0 else self.total_latency / self.request_count
    
    def record_success(self, latency: float):
        self.request_count += 1
        self.success_count += 1
        self.total_latency += latency
        self.trust_score = min(1.0, self.trust_score + 0.02)
        self.last_seen = datetime.now()
    
    def record_failure(self):
        self.request_count += 1
        self.failure_count += 1
        self.trust_score = max(0.0, self.trust_score - 0.05)
        self.last_seen = datetime.now()

class MetricsCollector:
    def __init__(self):
        self.metrics: Dict[str, AgentMetrics] = {}
    
    def get_or_create(self, agent_id: str) -> AgentMetrics:
        if agent_id not in self.metrics:
            self.metrics[agent_id] = AgentMetrics(agent_id=agent_id)
        return self.metrics[agent_id]
    
    def record_success(self, agent_id: str, latency: float):
        self.get_or_create(agent_id).record_success(latency)
    
    def record_failure(self, agent_id: str):
        self.get_or_create(agent_id).record_failure()
    
    def get_metrics(self, agent_id: str) -> AgentMetrics:
        return self.get_or_create(agent_id)
    
    def get_all_metrics(self) -> Dict[str, AgentMetrics]:
        return self.metrics

metrics_collector = MetricsCollector()
ws_connections = []

# Simulate some activity
async def simulate_activity():
    agents = ["labelee-duke-REAL", "agent-alpha", "agent-beta"]
    while True:
        try:
            for agent in agents:
                if random.random() < 0.8:
                    metrics_collector.record_success(agent, random.uniform(0.05, 0.25))
                else:
                    metrics_collector.record_failure(agent)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Simulation error: {e}")
            await asyncio.sleep(3)

async def update_metrics_loop():
    while True:
        try:
            all_metrics = metrics_collector.get_all_metrics()
            
            agents_detail = {}
            total_requests = 0
            total_latency = 0.0
            total_trust = 0.0
            
            for agent_id, metrics in all_metrics.items():
                agents_detail[agent_id] = {
                    "trust_score": metrics.trust_score,
                    "success_rate": metrics.success_rate,
                    "avg_latency": metrics.avg_latency,
                    "request_count": metrics.request_count
                }
                total_requests += metrics.request_count
                total_latency += metrics.avg_latency
                total_trust += metrics.trust_score
            
            num_agents = len(all_metrics)
            avg_latency = total_latency / num_agents if num_agents > 0 else 0
            avg_trust = total_trust / num_agents if num_agents > 0 else 0.5
            
            data = {
                "agents": num_agents,
                "total_requests": total_requests,
                "avg_latency": avg_latency,
                "avg_trust": avg_trust,
                "agents_detail": agents_detail
            }
            
            disconnected = []
            for ws in ws_connections:
                try:
                    await ws.send_text(json.dumps(data))
                except:
                    disconnected.append(ws)
            
            for ws in disconnected:
                if ws in ws_connections:
                    ws_connections.remove(ws)
            
            await asyncio.sleep(2)
        except Exception as e:
            print(f"Metrics loop error: {e}")
            await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ Starting metrics loop...")
    metrics_task = asyncio.create_task(update_metrics_loop())
    sim_task = asyncio.create_task(simulate_activity())
    yield
    metrics_task.cancel()
    sim_task.cancel()
    try:
        await metrics_task
        await sim_task
    except:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/dashboard")
async def serve_dashboard():
    return HTMLResponse("""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DukeNET AICP</title><script src="https://cdn.jsdelivr.net/npm/chart.js"></script><style>*{margin:0;padding:0;box-sizing:border-box}body{background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#0f172a 100%);min-height:100vh;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#e2e8f0;overflow-y:scroll}.container{padding:0 2rem}.card{background:rgba(30,41,59,0.5);backdrop-filter:blur(12px);border:1px solid rgba(71,85,105,0.5);border-radius:1rem;padding:1.5rem;margin-bottom:2rem}.stat-card{background:linear-gradient(135deg,rgba(30,58,138,0.3) 0%,rgba(30,64,175,0.1) 100%);border:1px solid rgba(59,130,246,0.2);padding:1.5rem;border-radius:0.75rem}.stat-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:1.5rem;margin-bottom:2rem}.chart-container{position:relative;height:300px}.agent-card{background:rgba(30,41,59,0.5);border:1px solid rgba(34,211,238,0.3);border-radius:0.5rem;padding:1rem;margin-bottom:1rem}.header{padding:2rem;margin-bottom:2rem;border-bottom:1px solid rgba(71,85,105,0.3)}.h1{font-size:2.5rem;font-weight:bold;margin-bottom:0.5rem;background:linear-gradient(90deg,#60a5fa,#22d3ee);-webkit-background-clip:text;-webkit-text-fill-color:transparent}.live{display:inline-block;width:12px;height:12px;background:#22c55e;border-radius:50%;animation:pulse 2s infinite;margin-right:0.5rem}@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}.stat-value{font-size:2rem;font-weight:bold;color:#60a5fa;margin:0.5rem 0}.stat-label{color:#cbd5e1;font-size:0.875rem;text-transform:uppercase}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1.5rem}.status-bar{padding:1rem;text-align:center;color:#cbd5e1;margin-bottom:2rem}.status-connected{color:#22c55e;font-weight:bold}.status-disconnected{color:#ef4444;font-weight:bold}</style></head><body><div class="header"><h1 class="h1"><span class="live"></span>DukeNET AICP Network</h1><p style="color:#cbd5e1">Real-time Agent Metrics & Performance</p></div><div class="container"><div class="stat-grid"><div class="stat-card"><p class="stat-label">Agents Online</p><p class="stat-value" id="agents">0</p></div><div class="stat-card"><p class="stat-label">Total Requests</p><p class="stat-value" id="requests">0</p></div><div class="stat-card"><p class="stat-label">Avg Latency</p><p class="stat-value"><span id="latency">0</span>ms</p></div><div class="stat-card"><p class="stat-label">Network Health</p><p class="stat-value" id="trust">0.00</p></div></div><div class="grid"><div class="card"><h2 style="margin-bottom:1rem">📊 Request Volume</h2><div class="chart-container"><canvas id="requestsChart"></canvas></div></div><div class="card"><h2 style="margin-bottom:1rem">⚡ Latency Trend</h2><div class="chart-container"><canvas id="latencyChart"></canvas></div></div></div><div class="card"><h2 style="margin-bottom:1rem">🤖 Connected Agents (<span id="agentCount">0</span>)</h2><div id="agentsList"><p style="color:#cbd5e1;padding:1rem">⏳ Loading agents...</p></div></div><div class="status-bar">Status: <span id="wsStatus" class="status-disconnected">Connecting...</span> | Last Update: <span id="lastUpdate" style="color:#22d3ee;font-family:monospace">--:--:--</span></div></div><script>const chartDefaults={responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#94a3b8'}}},scales:{y:{grid:{color:'rgba(100,116,139,0.1)'},ticks:{color:'#94a3b8'},min:0},x:{grid:{color:'rgba(100,116,139,0.1)'},ticks:{color:'#94a3b8',maxTicksLimit:10}}},animation:{duration:0}};const requestsChart=new Chart(document.getElementById('requestsChart'),{type:'line',data:{labels:[],datasets:[{label:'Requests',data:[],borderColor:'#22d3ee',backgroundColor:'rgba(34,211,238,0.1)',borderWidth:2,fill:true,tension:0.4}]},options:chartDefaults});const latencyChart=new Chart(document.getElementById('latencyChart'),{type:'line',data:{labels:[],datasets:[{label:'Latency (ms)',data:[],borderColor:'#10b981',backgroundColor:'rgba(16,185,129,0.1)',borderWidth:2,fill:true,tension:0.4}]},options:chartDefaults});function updateDashboard(data){console.log('Received data:',data);document.getElementById('agents').textContent=data.agents||0;document.getElementById('requests').textContent=data.total_requests||0;document.getElementById('latency').textContent=Math.round((data.avg_latency||0)*1000);document.getElementById('trust').textContent=(data.avg_trust||0).toFixed(2);document.getElementById('lastUpdate').textContent=new Date().toLocaleTimeString();const now=new Date().toLocaleTimeString('en-US',{hour12:false,hour:'2-digit',minute:'2-digit',second:'2-digit'});requestsChart.data.labels.push(now);requestsChart.data.datasets[0].data.push(data.total_requests||0);latencyChart.data.labels.push(now);latencyChart.data.datasets[0].data.push(Math.round((data.avg_latency||0)*1000));if(requestsChart.data.labels.length>30){requestsChart.data.labels.shift();requestsChart.data.datasets[0].data.shift();latencyChart.data.labels.shift();latencyChart.data.datasets[0].data.shift()}requestsChart.update('none');latencyChart.update('none');if(data.agents_detail){const count=Object.keys(data.agents_detail).length;document.getElementById('agentCount').textContent=count;document.getElementById('agentsList').innerHTML=count===0?'<p style="color:#cbd5e1;padding:1rem">⏳ Waiting for agents...</p>':Object.entries(data.agents_detail).map(([id,m])=>`<div class="agent-card"><div style="display:flex;justify-content:space-between;margin-bottom:0.5rem"><span style="color:#22d3ee;font-weight:bold">${id}</span><span style="color:#22c55e;font-size:0.875rem">● LIVE</span></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;font-size:0.875rem"><div><span style="color:#cbd5e1">Trust:</span> <span style="color:#60a5fa;font-weight:bold">${(m.trust_score||0).toFixed(2)}</span></div><div><span style="color:#cbd5e1">Success:</span> <span style="color:#10b981;font-weight:bold">${((m.success_rate||0)*100).toFixed(1)}%</span></div><div><span style="color:#cbd5e1">Latency:</span> <span style="color:#fbbf24;font-weight:bold">${Math.round((m.avg_latency||0)*1000)}ms</span></div><div><span style="color:#cbd5e1">Requests:</span> <span style="color:#c084fc;font-weight:bold">${m.request_count||0}</span></div></div></div>`).join('')}}fetch('/api/metrics/summary').then(r=>r.json()).then(updateDashboard).catch(e=>console.log('Initial fetch:',e));const protocol=window.location.protocol==='https:'?'wss:':'ws:';const ws=new WebSocket(protocol+'//'+window.location.host+'/ws/metrics');ws.onopen=()=>{console.log('WebSocket connected');document.getElementById('wsStatus').textContent='Connected';document.getElementById('wsStatus').className='status-connected'};ws.onmessage=(e)=>{updateDashboard(JSON.parse(e.data))};ws.onerror=(e)=>{console.error('WebSocket error:',e);document.getElementById('wsStatus').textContent='Error';document.getElementById('wsStatus').className='status-disconnected'};ws.onclose=()=>{console.log('WebSocket closed');document.getElementById('wsStatus').textContent='Disconnected';document.getElementById('wsStatus').className='status-disconnected';setTimeout(()=>location.reload(),5000)}</script></body></html>""")

@app.get("/api/metrics/summary")
async def get_metrics_summary():
    all_metrics = metrics_collector.get_all_metrics()
    agents_detail = {}
    total_requests = 0
    total_trust = 0.0
    for agent_id, metrics in all_metrics.items():
        agents_detail[agent_id] = {
            "trust_score": metrics.trust_score,
            "success_rate": metrics.success_rate,
            "avg_latency": metrics.avg_latency,
            "request_count": metrics.request_count
        }
        total_requests += metrics.request_count
        total_trust += metrics.trust_score
    num_agents = len(all_metrics)
    return {
        "agents": num_agents,
        "total_requests": total_requests,
        "avg_latency": sum(m.avg_latency for m in all_metrics.values()) / num_agents if num_agents > 0 else 0,
        "avg_trust": total_trust / num_agents if num_agents > 0 else 0.5,
        "agents_detail": agents_detail
    }

@app.get("/api/metrics/agents")
async def get_agents_detail():
    all_metrics = metrics_collector.get_all_metrics()
    agents_detail = {}
    for agent_id, metrics in all_metrics.items():
        agents_detail[agent_id] = {
            "trust_score": metrics.trust_score,
            "success_rate": metrics.success_rate,
            "avg_latency": metrics.avg_latency,
            "request_count": metrics.request_count
        }
    return agents_detail

@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await websocket.accept()
    ws_connections.append(websocket)
    print(f"✅ WebSocket connected. Total: {len(ws_connections)}")
    try:
        while True:
            await asyncio.sleep(1)
    except:
        if websocket in ws_connections:
            ws_connections.remove(websocket)
        print(f"❌ WebSocket disconnected. Remaining: {len(ws_connections)}")

if __name__ == "__main__":
    print("🚀 Starting DukeNET Dashboard")
    print("📊 Dashboard: http://127.0.0.1:8000/dashboard")
    print("📈 API: http://127.0.0.1:8000/api/metrics/summary")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
