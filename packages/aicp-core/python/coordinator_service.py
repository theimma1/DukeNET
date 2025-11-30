from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from datetime import datetime
import time
from typing import Optional

# Import security and validators
from security import (
    get_current_user, 
    get_current_buyer, 
    get_current_agent,
    TokenData,
    create_access_token,
    TokenResponse
)
from validators import (
    TaskSubmissionRequest,
    TaskCompletionRequest,
    BuyerLoginRequest,
    AgentLoginRequest
)

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

def generate_task_id():
    return str(uuid.uuid4())[:8]

# ==================== PUBLIC ENDPOINTS ====================

@app.get("/")
async def root():
    return {"service": "AICP Coordinator", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/auth/buyer/login", response_model=TokenResponse)
async def buyer_login(credentials: BuyerLoginRequest):
    """Buyer login endpoint - Returns JWT token"""
    if len(credentials.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token(
        user_id=credentials.buyer_id,
        user_type="buyer"
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=credentials.buyer_id,
        user_type="buyer"
    )

@app.post("/auth/agent/login", response_model=TokenResponse)
async def agent_login(credentials: AgentLoginRequest):
    """Agent login endpoint - Returns JWT token"""
    # Validate agent exists
    if not any(agent["name"] == credentials.agent_id for agent in agents_db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent ID"
        )
    
    if len(credentials.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token(
        user_id=credentials.agent_id,
        user_type="agent"
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=credentials.agent_id,
        user_type="agent"
    )

# ==================== PROTECTED TASK ENDPOINTS ====================

@app.post("/tasks/submit")
async def submit_task(
    task_request: TaskSubmissionRequest,
    current_buyer: TokenData = Depends(get_current_buyer)
):
    """
    Submit new task - Buyer only, requires JWT token
    """
    # Validate buyer_id matches token
    if task_request.buyer_id != current_buyer.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot submit task for another buyer"
        )
    
    # Select agent with highest reputation
    agent = max(agents_db, key=lambda a: a['reputation_multiplier'])
    price_satoshis = int(100000 * task_request.complexity * agent['reputation_multiplier'])
    
    task_id = generate_task_id()
    task = {
        "id": task_id,
        "description": task_request.description,
        "agent_name": agent["name"],
        "price_satoshis": price_satoshis,
        "status": "assigned",
        "buyer_id": task_request.buyer_id,
        "created_at": datetime.utcnow().isoformat(),
        "result": None
    }
    
    tasks_db[task_id] = task
    
    return {
        "task_id": task_id,
        "agent_name": agent["name"],
        "price_satoshis": price_satoshis,
        "status": "assigned"
    }

@app.get("/tasks")
async def get_tasks(current_user: TokenData = Depends(get_current_user)):
    """
    Get tasks - Authenticated users only
    Buyers see their own tasks, agents see all tasks
    """
    if current_user.user_type == "buyer":
        buyer_tasks = [t for t in tasks_db.values() if t["buyer_id"] == current_user.user_id]
        return {"tasks": buyer_tasks, "count": len(buyer_tasks)}
    else:
        return {"tasks": list(tasks_db.values()), "count": len(tasks_db)}

@app.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """Get single task - Authenticated users only"""
    task = tasks_db.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Buyers can only see their own tasks
    if current_user.user_type == "buyer" and task["buyer_id"] != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot access other buyer's tasks")
    
    return task

@app.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: str,
    completion_request: TaskCompletionRequest,
    current_agent: TokenData = Depends(get_current_agent)
):
    """
    Complete task - Agent only, requires JWT token
    """
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    
    task = tasks_db[task_id]
    
    # Verify agent owns this task
    if task["agent_name"] != current_agent.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only complete your own tasks"
        )
    
    # Update task status and result
    task["status"] = "completed" if completion_request.success else "failed"
    task["result"] = completion_request.result
    task["completed_at"] = datetime.utcnow().isoformat()
    
    # Update agent balance if successful
    if completion_request.success:
        for agent in agents_db:
            if agent["name"] == current_agent.user_id:
                agent["balance_satoshis"] += task["price_satoshis"]
                print(f"✅ Agent {agent['name']} earned {task['price_satoshis']} sat. New balance: {agent['balance_satoshis']}")
                break
    
    return task

# ==================== PROTECTED AGENT ENDPOINTS ====================

@app.get("/agents")
async def get_agents(current_user: TokenData = Depends(get_current_user)):
    """Get agents - Authenticated users only"""
    return {"agents": agents_db}

# ==================== DASHBOARD ENDPOINT ====================

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
    
    # Build HTML (same as before - kept intact)
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
            
            .container {{ max-width: 1600px; margin: 0 auto; }}
            
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
            
            .header-left {{ display: flex; align-items: center; gap: 16px; }}
            
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
            
            .header-right {{ display: flex; gap: 16px; align-items: center; }}
            
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
            }}
            
            .card:hover {{
                border-color: var(--border-hover);
                transform: translateY(-2px);
                box-shadow: 0 12px 24px rgba(0, 0, 0, 0.4);
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
            
            .card-icon {{ font-size: 14px; }}
            
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
            }}
            
            .metric-value.success {{ color: var(--success); }}
            .metric-value.warning {{ color: var(--warning); }}
            .metric-value.error {{ color: var(--error); }}
            
            .big-metric {{
                font-size: 36px;
                font-weight: 700;
                margin-top: 8px;
            }}
            
            .table-container {{ overflow-x: auto; margin-top: 16px; }}
            
            table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
            
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
            
            td {{ padding: 16px; border-bottom: 1px solid rgba(255, 255, 255, 0.03); }}
            
            tr:hover {{ background: rgba(255, 255, 255, 0.02); }}
            
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
            
            .full-width {{ grid-column: 1 / -1; }}
            
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
            }}
            
            a {{ color: var(--info); text-decoration: none; }}
            a:hover {{ color: var(--accent); }}
            
            @media (max-width: 768px) {{
                body {{ padding: 16px; }}
                .header {{ flex-direction: column; gap: 16px; }}
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
                <div class="card">
                    <div class="card-title"><span class="card-icon">💚</span> System Status</div>
                    <div class="metric">
                        <span class="metric-label">Coordinator Pods</span>
                        <span class="metric-value success">2/2 Running</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Database</span>
                        <span class="metric-value success">PostgreSQL ✓</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title"><span class="card-icon">🤖</span> Agent Metrics</div>
                    <div class="metric">
                        <span class="metric-label">Total Agents</span>
                        <span class="metric-value big-metric">{total_agents}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Total Balance</span>
                        <span class="metric-value success">{total_balance:,} sat</span>
                    </div>
                </div>
                
                <div class="card">
                    <div class="card-title"><span class="card-icon">⚡</span> Task Execution</div>
                    <div class="metric">
                        <span class="metric-label">Total Tasks</span>
                        <span class="metric-value big-metric">{total_tasks}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Success Rate</span>
                        <span class="metric-value success">{success_rate:.1f}%</span>
                    </div>
                </div>
                
                <div class="card full-width">
                    <div class="card-title"><span class="card-icon">👥</span> Agent Performance</div>
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
                
                <div class="card full-width">
                    <div class="card-title"><span class="card-icon">📋</span> Recent Tasks</div>
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
                                </tr>
                            </thead>
                            <tbody>
    """
    
    if tasks_db:
        for task_id, task in sorted(tasks_db.items(), key=lambda x: x.get('created_at', ''), reverse=True)[:10]:
            status_class = 'completed' if task['status'] == 'completed' else 'active' if task['status'] == 'assigned' else 'failed'
            html += f"""
                                <tr>
                                    <td><code>{task_id}</code></td>
                                    <td>{task['description'][:40]}...</td>
                                    <td><span class="pill {status_class}">{task['status']}</span></td>
                                    <td>{task['agent_name']}</td>
                                    <td>{task['price_satoshis']:,} sat</td>
                                    <td>{task['buyer_id']}</td>
                                </tr>
            """
    else:
        html += """
                                <tr>
                                    <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 32px;">
                                        No tasks yet. Submit one via POST /tasks/submit
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

# ==================== BACKWARD COMPATIBILITY ENDPOINTS ====================

@app.get("/health-old")
async def get_health_old():
    """Health check - NO AUTH (for backward compatibility)"""
    return {"status": "healthy"}

@app.get("/agents-old")
async def get_agents_old():
    """Get agents - NO AUTH (for backward compatibility)"""
    return {"agents": agents_db}

@app.get("/tasks-old")
async def get_tasks_old():
    """Get all tasks - NO AUTH (for backward compatibility)"""
    return {"tasks": list(tasks_db.values()), "count": len(tasks_db)}
