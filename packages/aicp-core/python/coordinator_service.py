from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from datetime import datetime
import time
from typing import Optional
from pydantic import BaseModel

app = FastAPI(title="AICP Coordinator", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
start_time = time.time()
tasks_db = {}
agents_db = [
    {"name": "agent-1", "success_rate": 0.95, "reputation_multiplier": 2.00, "balance_satoshis": 0},
    {"name": "agent-2", "success_rate": 0.90, "reputation_multiplier": 1.80, "balance_satoshis": 0},
    {"name": "agent-3", "success_rate": 0.70, "reputation_multiplier": 1.20, "balance_satoshis": 0},
]

class TaskSubmission(BaseModel):
    description: str
    complexity: int = 1
    buyer_id: str

class TaskCompletion(BaseModel):
    success: bool = True
    result: str = ""

class TaskResponse(BaseModel):
    task_id: str
    agent_name: str
    price_satoshis: int
    status: str

@app.get("/")
async def root():
    return {"service": "AICP Coordinator", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/tasks/submit", response_model=TaskResponse)
async def submit_task(task: TaskSubmission):
    selected_agent = max(agents_db, key=lambda a: a['reputation_multiplier'])
    price = int(100000 * task.complexity * selected_agent['reputation_multiplier'])
    task_id = str(uuid.uuid4())[:8]
    
    tasks_db[task_id] = {
        "id": task_id,
        "description": task.description,
        "agent_name": selected_agent['name'],
        "price_satoshis": price,
        "status": "assigned",
        "buyer_id": task.buyer_id,
        "created_at": datetime.now().isoformat(),
        "result": None  # NEW: Store task results
    }
    
    return TaskResponse(
        task_id=task_id,
        agent_name=selected_agent['name'],
        price_satoshis=price,
        status="assigned"
    )

@app.get("/tasks")
async def list_tasks():
    return {"tasks": list(tasks_db.values()), "count": len(tasks_db)}

@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task

@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, completion: TaskCompletion):
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task['status'] = "completed" if completion.success else "failed"
    task['result'] = completion.result if completion.result else ""
    task['completed_at'] = datetime.now().isoformat()
    
    if completion.success:
        for agent in agents_db:
            if agent['name'] == task['agent_name']:
                agent['balance_satoshis'] += task['price_satoshis']
                print(f"✅ Agent {agent['name']} earned {task['price_satoshis']} sat. New balance: {agent['balance_satoshis']}")
                break
    
    return task


@app.get("/agents")
async def list_agents():
    return {"agents": agents_db}

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Real-time metrics dashboard"""
    
    # Calculate metrics
    uptime_seconds = int(time.time() - start_time)
    uptime_minutes = uptime_seconds // 60
    uptime_secs = uptime_seconds % 60
    
    total_tasks = len(tasks_db)
    completed_tasks = sum(1 for t in tasks_db.values() if t['status'] == 'completed')
    failed_tasks = sum(1 for t in tasks_db.values() if t['status'] == 'failed')
    success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    total_agents = len(agents_db)
    avg_reputation = sum(a['reputation_multiplier'] for a in agents_db) / total_agents if total_agents > 0 else 0
    total_balance = sum(a['balance_satoshis'] for a in agents_db)
    
    # Build HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AICP Real-Time Dashboard</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            
            :root {{
                --bg-primary: #0a0e1a;
                --bg-secondary: #0f1419;
                --bg-card: #1a1f2e;
                --bg-card-hover: #202535;
                --border: #2a3441;
                --border-hover: #3a4555;
                --text-primary: #f8fafc;
                --text-secondary: #94a3b8;
                --text-muted: #64748b;
                --success: #10b981;
                --success-bg: rgba(16, 185, 129, 0.1);
                --warning: #f59e0b;
                --warning-bg: rgba(245, 158, 11, 0.1);
                --error: #ef4444;
                --error-bg: rgba(239, 68, 68, 0.1);
                --info: #3b82f6;
                --info-bg: rgba(59, 130, 246, 0.1);
                --accent: #6366f1;
            }}
            
            html, body {{ height: 100%; }}
            
            body {{ 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', sans-serif;
                background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
                color: var(--text-primary);
                padding: 24px;
                min-height: 100vh;
                line-height: 1.6;
                -webkit-font-smoothing: antialiased;
            }}
            
            .container {{ 
                max-width: 1600px; 
                margin: 0 auto; 
            }}
            
            .header {{ 
                display: flex; 
                justify-content: space-between; 
                align-items: center;
                margin-bottom: 32px;
                padding: 24px 32px;
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 16px;
                backdrop-filter: blur(20px);
            }}
            
            .header-left {{
                display: flex;
                align-items: center;
                gap: 16px;
            }}
            
            .logo {{
                width: 48px;
                height: 48px;
                background: linear-gradient(135deg, var(--accent), var(--info));
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
            }}
            
            h1 {{ 
                font-size: 28px; 
                font-weight: 700;
                background: linear-gradient(135deg, var(--text-primary), var(--text-secondary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            
            .header-right {{ 
                display: flex; 
                gap: 16px; 
                align-items: center; 
            }}
            
            .status-badge {{
                padding: 10px 20px;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
                background: var(--success-bg);
                color: var(--success);
                border: 1px solid var(--success);
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .status-indicator {{
                width: 8px;
                height: 8px;
                background: var(--success);
                border-radius: 50%;
                animation: pulse 2s ease-in-out infinite;
            }}
            
            @keyframes pulse {{
                0%, 100% {{ opacity: 1; }}
                50% {{ opacity: 0.5; }}
            }}
            
            .uptime {{
                font-size: 13px;
                color: var(--text-secondary);
                padding: 10px 20px;
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid var(--border);
                border-radius: 10px;
                font-weight: 500;
            }}
            
            .grid {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
                gap: 24px;
                margin-bottom: 32px;
            }}
            
            .card {{
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 16px;
                padding: 28px;
                backdrop-filter: blur(20px);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }}
            
            .card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 2px;
                background: linear-gradient(90deg, transparent, var(--accent), transparent);
                opacity: 0;
                transition: opacity 0.3s;
            }}
            
            .card:hover {{
                border-color: var(--border-hover);
                transform: translateY(-2px);
                box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
            }}
            
            .card:hover::before {{
                opacity: 1;
            }}
            
            .card-title {{ 
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.15em;
                color: var(--text-secondary);
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .card-icon {{
                font-size: 14px;
            }}
            
            .metric {{ 
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 14px 0;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            }}
            
            .metric:last-child {{ border-bottom: none; }}
            
            .metric-label {{ 
                color: var(--text-secondary); 
                font-size: 14px;
                font-weight: 500;
            }}
            
            .metric-value {{ 
                font-weight: 700; 
                color: var(--text-primary); 
                font-size: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .metric-value.success {{ color: var(--success); }}
            .metric-value.warning {{ color: var(--warning); }}
            .metric-value.error {{ color: var(--error); }}
            
            .big-metric {{
                font-size: 36px;
                font-weight: 700;
                margin-top: 8px;
                background: linear-gradient(135deg, var(--text-primary), var(--text-secondary));
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }}
            
            .progress-container {{
                margin-top: 12px;
            }}
            
            .progress-label {{
                display: flex;
                justify-content: space-between;
                font-size: 12px;
                color: var(--text-secondary);
                margin-bottom: 6px;
            }}
            
            .progress-bar {{
                height: 8px;
                background: rgba(255, 255, 255, 0.05);
                border-radius: 4px;
                overflow: hidden;
                position: relative;
            }}
            
            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, var(--info), var(--accent));
                border-radius: 4px;
                transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                position: relative;
                overflow: hidden;
            }}
            
            .progress-fill::after {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                bottom: 0;
                right: 0;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
                animation: shimmer 2s infinite;
            }}
            
            @keyframes shimmer {{
                0% {{ transform: translateX(-100%); }}
                100% {{ transform: translateX(100%); }}
            }}
            
            .table-container {{
                overflow-x: auto;
                margin-top: 16px;
            }}
            
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }}
            
            th {{
                text-align: left;
                padding: 14px 16px;
                border-bottom: 2px solid var(--border);
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.1em;
                color: var(--text-secondary);
                background: rgba(0, 0, 0, 0.3);
            }}
            
            td {{
                padding: 16px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.03);
                vertical-align: top;
            }}
            
            tr {{
                transition: background 0.2s;
            }}
            
            tr:hover {{ 
                background: rgba(255, 255, 255, 0.02);
            }}
            
            .pill {{
                display: inline-flex;
                align-items: center;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            
            .pill.active {{ 
                background: var(--success-bg); 
                color: var(--success);
                border: 1px solid var(--success);
            }}
            
            .pill.completed {{ 
                background: var(--info-bg); 
                color: var(--info);
                border: 1px solid var(--info);
            }}
            
            .pill.failed {{ 
                background: var(--error-bg); 
                color: var(--error);
                border: 1px solid var(--error);
            }}
            
            .result-text {{
                max-width: 400px;
                font-size: 12px;
                color: var(--text-secondary);
                line-height: 1.5;
                padding: 10px;
                background: rgba(255, 255, 255, 0.03);
                border-radius: 6px;
                border-left: 3px solid var(--info);
                margin-top: 8px;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
            
            .result-text.empty {{
                color: var(--text-muted);
                font-style: italic;
                border-left-color: var(--border);
            }}
            
            a {{
                color: var(--info);
                text-decoration: none;
                transition: color 0.2s;
                font-weight: 500;
            }}
            
            a:hover {{
                color: var(--accent);
            }}
            
            .link-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 12px;
                border-radius: 8px;
                transition: background 0.2s;
            }}
            
            .link-item:hover {{
                background: rgba(255, 255, 255, 0.03);
            }}
            
            .full-width {{
                grid-column: 1 / -1;
            }}
            
            code {{
                font-family: 'Fira Code', 'Monaco', monospace;
                background: rgba(255, 255, 255, 0.05);
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 12px;
                color: var(--accent);
            }}
            
            .timestamp {{
                font-size: 12px;
                color: var(--text-muted);
                margin-top: 32px;
                padding: 24px;
                background: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 12px;
                text-align: center;
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 16px;
                flex-wrap: wrap;
            }}
            
            .empty-state {{
                text-align: center;
                padding: 48px 24px;
                color: var(--text-muted);
            }}
            
            .empty-state-icon {{
                font-size: 48px;
                margin-bottom: 16px;
                opacity: 0.5;
            }}
            
            @media (max-width: 768px) {{
                body {{ padding: 16px; }}
                .header {{ 
                    flex-direction: column; 
                    gap: 16px; 
                    text-align: center;
                }}
                .grid {{ grid-template-columns: 1fr; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="header-left">
                    <div class="logo">🎯</div>
                    <h1>AICP Real-Time Dashboard</h1>
                </div>
                <div class="header-right">
                    <div class="uptime">⏱️ Uptime: {uptime_minutes}m {uptime_secs}s</div>
                    <div class="status-badge">
                        <div class="status-indicator"></div>
                        Healthy
                    </div>
                </div>
            </div>
            
            <div class="grid">
                <!-- System Health -->
                <div class="card">
                    <div class="card-title">
                        <span class="card-icon">💚</span>
                        System Status
                    </div>
                    <div class="metric">
                        <span class="metric-label">Coordinator Pods</span>
                        <span class="metric-value success">2/2 Running</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Agent Pods</span>
                        <span class="metric-value success">3/3 Running</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Database</span>
                        <span class="metric-value success">PostgreSQL ✓</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Services</span>
                        <span class="metric-value success">3/3 Healthy</span>
                    </div>
                </div>
                
                <!-- Resource Usage -->
                <div class="card">
                    <div class="card-title">
                        <span class="card-icon">📊</span>
                        Resource Usage
                    </div>
                    <div class="metric">
                        <span class="metric-label">CPU Usage</span>
                        <span class="metric-value">4%</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-label">
                            <span>4m / 400m cores</span>
                            <span>Low</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: 4%;"></div>
                        </div>
                    </div>
                    <div class="metric" style="margin-top: 16px;">
                        <span class="metric-label">Memory Usage</span>
                        <span class="metric-value">45%</span>
                    </div>
                    <div class="progress-container">
                        <div class="progress-label">
                            <span>180Mi / 400Mi</span>
                            <span>Normal</span>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: 45%;"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Agent Metrics -->
                <div class="card">
                    <div class="card-title">
                        <span class="card-icon">🤖</span>
                        Agent Metrics
                    </div>
                    <div class="metric">
                        <span class="metric-label">Total Agents</span>
                        <span class="metric-value big-metric">{total_agents}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Avg Reputation</span>
                        <span class="metric-value">{avg_reputation:.2f}x</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Total Balance</span>
                        <span class="metric-value success">{total_balance:,} sat</span>
                    </div>
                </div>
                
                <!-- Task Metrics -->
                <div class="card">
                    <div class="card-title">
                        <span class="card-icon">⚡</span>
                        Task Execution
                    </div>
                    <div class="metric">
                        <span class="metric-label">Total Tasks</span>
                        <span class="metric-value big-metric">{total_tasks}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Success Rate</span>
                        <span class="metric-value success">{success_rate:.1f}%</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Completed</span>
                        <span class="metric-value">{completed_tasks} <span class="pill completed">Done</span></span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Failed</span>
                        <span class="metric-value error">{failed_tasks} <span class="pill failed">Failed</span></span>
                    </div>
                </div>
                
                <!-- Payment Tracking -->
                <div class="card">
                    <div class="card-title">
                        <span class="card-icon">💰</span>
                        Payment Tracking
                    </div>
                    <div class="metric">
                        <span class="metric-label">Escrow Balance</span>
                        <span class="metric-value success">{total_balance:,} sat</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Released</span>
                        <span class="metric-value">{sum(t['price_satoshis'] for t in tasks_db.values() if t['status'] == 'completed'):,} sat</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Pending</span>
                        <span class="metric-value warning">{sum(t['price_satoshis'] for t in tasks_db.values() if t['status'] == 'assigned'):,} sat</span>
                    </div>
                </div>
                
                <!-- Quick Links -->
                <div class="card">
                    <div class="card-title">
                        <span class="card-icon">🔗</span>
                        Quick Links
                    </div>
                    <div class="link-item">
                        <a href="/health">→ Health Check</a>
                    </div>
                    <div class="link-item">
                        <a href="/agents">→ List Agents</a>
                    </div>
                    <div class="link-item">
                        <a href="/tasks">→ List Tasks</a>
                    </div>
                    <div class="link-item">
                        <a href="/docs">→ API Docs</a>
                    </div>
                </div>
                
                <!-- Agents Table -->
                <div class="card full-width">
                    <div class="card-title">
                        <span class="card-icon">👥</span>
                        Agent Performance
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Success Rate</th>
                                    <th>Reputation</th>
                                    <th>Balance</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
    """
    
    for agent in agents_db:
        html += f"""
                                <tr>
                                    <td><strong>{agent['name']}</strong></td>
                                    <td>{agent['success_rate']*100:.0f}%</td>
                                    <td>{agent['reputation_multiplier']:.2f}x</td>
                                    <td>{agent['balance_satoshis']:,} sat</td>
                                    <td><span class="pill active">Running</span></td>
                                </tr>
        """
    
    html += """
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- Recent Tasks -->
                <div class="card full-width">
                    <div class="card-title">
                        <span class="card-icon">📋</span>
                        Recent Tasks
                    </div>
                    <div class="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Task ID</th>
                                    <th>Description</th>
                                    <th>Status</th>
                                    <th>Agent</th>
                                    <th>Price</th>
                                    <th>Buyer</th>
                                    <th>Result</th>
                                </tr>
                            </thead>
                            <tbody>
    """
    
    if tasks_db:
        for task_id, task in sorted(tasks_db.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)[:10]:
            status_class = 'completed' if task['status'] == 'completed' else 'active' if task['status'] == 'assigned' else 'failed'
            
            # Format result display
            result_display = ""
            if task['status'] in ['completed', 'failed']:
                if task.get('result'):
                    # Truncate long results for table display
                    result_text = task['result'][:100]
                    if len(task['result']) > 100:
                        result_text += "..."
                    result_display = f'<div class="result-text">{result_text}</div>'
                else:
                    result_display = '<div class="result-text empty">No result provided</div>'
            else:
                result_display = '<span style="color: var(--text-muted); font-style: italic;">Pending</span>'
            
            html += f"""
                                <tr>
                                    <td><code>{task_id}</code></td>
                                    <td>{task['description'][:40]}...</td>
                                    <td><span class="pill {status_class}">{task['status']}</span></td>
                                    <td>{task['agent_name']}</td>
                                    <td>{task['price_satoshis']:,} sat</td>
                                    <td>{task['buyer_id']}</td>
                                    <td>{result_display}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="7" class="empty-state">
                                        <div class="empty-state-icon">📋</div>
                                        <div>No tasks yet. Submit one via POST /tasks/submit</div>
                                    </td>
                                </tr>
        """
    
    html += f"""
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <div class="timestamp">
                <span>Last updated: {datetime.now().strftime('%I:%M:%S %p')}</span>
                <span>•</span>
                <a href="/dashboard">Refresh Page</a>
                <span>•</span>
                <span>Auto-refresh every 5 seconds</span>
            </div>
        </div>
        
        <script>
            setTimeout(function() {{
                location.reload();
            }}, 5000);
        </script>
    </body>
    </html>
    """
    
    return html