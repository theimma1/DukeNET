from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from aicp.metrics import MetricsCollector
import asyncio, json

router = APIRouter()
metrics = MetricsCollector()  # Replace with your global singleton if needed

@router.get("/api/metrics/agents")
async def get_agent_metrics():
    data = {}
    for agent_id, m in metrics.get_all_metrics().items():
        data[agent_id] = {
            "trust_score": m.trust_score,
            "success_rate": m.success_rate,
            "avg_latency": m.avg_latency,
            "request_count": m.request_count,
        }
    return data

@router.get("/api/metrics/summary")
async def get_summary():
    ms = list(metrics.get_all_metrics().values())
    if not ms:
        return {"agents": 0, "avg_trust": 0, "total_requests": 0}
    return {
        "agents": len(ms),
        "avg_trust": sum(m.trust_score for m in ms) / len(ms),
        "total_requests": sum(m.request_count for m in ms),
        "avg_latency": sum(m.avg_latency for m in ms) / len(ms)
    }

class MetricsWSManager:
    def __init__(self):
        self.connections = []
        self.broadcast_task = None

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)
        if not self.broadcast_task:
            self.broadcast_task = asyncio.create_task(self.broadcast_loop())

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
        if not self.connections and self.broadcast_task:
            self.broadcast_task.cancel()
            self.broadcast_task = None

    async def broadcast_loop(self):
        while True:
            snapshot = await get_summary()
            dead = []
            for ws in self.connections:
                try:
                    await ws.send_text(json.dumps(snapshot))
                except WebSocketDisconnect:
                    dead.append(ws)
            for ws in dead:
                self.disconnect(ws)
            await asyncio.sleep(1.0)

manager = MetricsWSManager()

@router.websocket("/ws/metrics")
async def metrics_ws(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)
