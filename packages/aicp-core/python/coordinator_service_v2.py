"""
AICP Autonomous Agent Marketplace - Coordinator Service
FastAPI backend with SQLite database and JWT authentication
"""


from fastapi import FastAPI, HTTPException, Depends, status, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uuid
import logging
import jwt


# ==================== LOGGING SETUP ====================


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== DATABASE SETUP ====================


DATABASE_URL = "sqlite:///./aicp.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==================== DATABASE MODELS ====================


class Agent(Base):
    """Agent database model"""
    __tablename__ = "agents"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    success_rate = Column(Float)
    reputation_multiplier = Column(Float)
    balance_satoshis = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    """Task database model"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, index=True)
    description = Column(String)
    complexity = Column(Integer)
    buyer_id = Column(String, index=True)
    agent_name = Column(String, index=True)
    price_satoshis = Column(Integer)
    status = Column(String)  # "assigned", "completed", "failed"
    result = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class User(Base):
    """User database model for authentication"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    user_type = Column(String)  # "buyer" or "agent"
    password_hash = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


# Create all tables
Base.metadata.create_all(bind=engine)


# ==================== PYDANTIC MODELS ====================


class TaskSubmission(BaseModel):
    """Task submission request"""
    description: str
    complexity: int = 1
    buyer_id: str


class TaskCompletion(BaseModel):
    """Task completion request"""
    success: bool = True
    result: str = None


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str
    user_id: str
    user_type: str


class TokenData(BaseModel):
    """Token data"""
    user_id: str
    user_type: str


class BuyerLoginRequest(BaseModel):
    """Buyer login request"""
    buyer_id: str
    password: str


class AgentLoginRequest(BaseModel):
    """Agent login request"""
    agent_id: str
    password: str


# ==================== JWT CONFIGURATION ====================


SECRET_KEY = "your-secret-key-change-in-production-12345678"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
security = HTTPBearer()


# ==================== JWT FUNCTIONS ====================


def create_access_token(user_id: str, user_type: str, expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    to_encode = {"user_id": user_id, "user_type": user_type}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.info(f"✅ Token created for user: {user_id} (type: {user_type})")
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        user_type: str = payload.get("user_type")
        
        if user_id is None or user_type is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return TokenData(user_id=user_id, user_type=user_type)
    except jwt.ExpiredSignatureError:
        logger.error("❌ Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        logger.error("❌ Invalid token")
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Get current authenticated user"""
    return verify_token(credentials.credentials)


async def get_current_buyer(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Get current buyer"""
    if current_user.user_type != "buyer":
        raise HTTPException(status_code=403, detail="Buyers only")
    return current_user


async def get_current_agent(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Get current agent"""
    if current_user.user_type != "agent":
        raise HTTPException(status_code=403, detail="Agents only")
    return current_user


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== INITIALIZE FASTAPI APP ====================


app = FastAPI(
    title="AICP Coordinator",
    description="Autonomous Agent Marketplace Coordinator API",
    version="2.0.0"
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== STARTUP EVENT ====================


@app.on_event("startup")
async def startup_event():
    """Initialize default agents on startup"""
    db = SessionLocal()
    try:
        # Check if agents exist
        existing_agents = db.query(Agent).count()
        if existing_agents == 0:
            default_agents = [
                Agent(id=str(uuid.uuid4()), name="agent-1", success_rate=0.95, reputation_multiplier=2.00),
                Agent(id=str(uuid.uuid4()), name="agent-2", success_rate=0.90, reputation_multiplier=1.80),
                Agent(id=str(uuid.uuid4()), name="agent-3", success_rate=0.70, reputation_multiplier=1.20),
            ]
            db.add_all(default_agents)
            db.commit()
            logger.info("✅ Default agents initialized")
    finally:
        db.close()


# ==================== HEALTH ENDPOINTS ====================


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {"service": "AICP Coordinator", "status": "running"}


@app.get("/health", tags=["Health"])
async def health():
    """Health check"""
    return {"status": "healthy"}


# ==================== AUTHENTICATION ENDPOINTS ====================


@app.post("/auth/buyer/login", response_model=TokenResponse, tags=["Auth"])
async def buyer_login(creds: BuyerLoginRequest):
    """Buyer login endpoint"""
    logger.info(f"🔐 Buyer login attempt: {creds.buyer_id}")
    
    if len(creds.password) < 8:
        logger.warning(f"❌ Invalid password length for buyer: {creds.buyer_id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user_id=creds.buyer_id, user_type="buyer")
    logger.info(f"✅ Buyer logged in: {creds.buyer_id}")
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=creds.buyer_id,
        user_type="buyer"
    )


@app.post("/auth/agent/login", response_model=TokenResponse, tags=["Auth"])
async def agent_login(creds: AgentLoginRequest, db: Session = Depends(get_db)):
    """Agent login endpoint"""
    logger.info(f"🔐 Agent login attempt: {creds.agent_id}")
    
    agent = db.query(Agent).filter(Agent.name == creds.agent_id).first()
    if not agent:
        logger.warning(f"❌ Agent not found: {creds.agent_id}")
        raise HTTPException(status_code=401, detail="Invalid agent")
    
    if len(creds.password) < 8:
        logger.warning(f"❌ Invalid password length for agent: {creds.agent_id}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token(user_id=creds.agent_id, user_type="agent")
    logger.info(f"✅ Agent logged in: {creds.agent_id}")
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=creds.agent_id,
        user_type="agent"
    )


# ==================== AGENT ENDPOINTS ====================


@app.get("/agents", tags=["Agents"])
async def get_agents(db: Session = Depends(get_db)):
    """Get all agents"""
    agents = db.query(Agent).all()
    return {"agents": [
        {
            "name": a.name,
            "success_rate": a.success_rate,
            "reputation_multiplier": a.reputation_multiplier,
            "balance_satoshis": a.balance_satoshis
        }
        for a in agents
    ]}


# ==================== TASK ENDPOINTS ====================


def select_best_agent(db: Session) -> str:
    """Select best agent by reputation multiplier"""
    best_agent = db.query(Agent).order_by(Agent.reputation_multiplier.desc()).first()
    return best_agent.name if best_agent else None


def calculate_price(complexity: int, agent_name: str, db: Session) -> int:
    """Calculate task price"""
    agent = db.query(Agent).filter(Agent.name == agent_name).first()
    if not agent:
        return 100000 * complexity
    
    base_price = 100000
    return int(base_price * complexity * agent.reputation_multiplier)


@app.post("/tasks/submit", tags=["Tasks"])
async def submit_task(task: TaskSubmission, buyer: TokenData = Depends(get_current_buyer), db: Session = Depends(get_db)):
    """Submit a new task"""
    try:
        # Validate input
        if not task.description or len(task.description.strip()) == 0:
            raise HTTPException(status_code=400, detail="Task description cannot be empty")
        
        if task.complexity < 1 or task.complexity > 10:
            raise HTTPException(status_code=400, detail="Complexity must be between 1 and 10")
        
        if task.buyer_id != buyer.user_id:
            raise HTTPException(status_code=403, detail="Cannot submit for other buyer")
        
        # Select best agent
        agent_name = select_best_agent(db)
        if not agent_name:
            raise HTTPException(status_code=500, detail="No agents available")
        
        # Calculate price
        price_satoshis = calculate_price(task.complexity, agent_name, db)
        
        # Create task
        task_id = str(uuid.uuid4())[:8]
        new_task = Task(
            id=task_id,
            description=task.description,
            complexity=task.complexity,
            buyer_id=task.buyer_id,
            agent_name=agent_name,
            price_satoshis=price_satoshis,
            status="assigned"
        )
        db.add(new_task)
        db.commit()
        
        logger.info(f"✅ Task created: {task_id} -> Agent: {agent_name} -> Price: {price_satoshis} sat")
        
        return {
            "task_id": task_id,
            "agent_name": agent_name,
            "price_satoshis": price_satoshis,
            "status": "assigned"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks", tags=["Tasks"])
async def get_tasks(user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get tasks (filtered by user type)"""
    if user.user_type == "buyer":
        tasks = db.query(Task).filter(Task.buyer_id == user.user_id).all()
    else:
        tasks = db.query(Task).all()
    
    return {
        "tasks": [
            {
                "id": t.id,
                "description": t.description,
                "complexity": t.complexity,
                "agent_name": t.agent_name,
                "price_satoshis": t.price_satoshis,
                "status": t.status,
                "buyer_id": t.buyer_id,
                "created_at": t.created_at.isoformat()
            }
            for t in tasks
        ],
        "count": len(tasks)
    }


@app.get("/tasks/{task_id}", tags=["Tasks"])
async def get_task(task_id: str, user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get specific task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if user.user_type == "buyer" and task.buyer_id != user.user_id:
        raise HTTPException(status_code=403, detail="Cannot access")
    
    return {
        "id": task.id,
        "description": task.description,
        "complexity": task.complexity,
        "agent_name": task.agent_name,
        "price_satoshis": task.price_satoshis,
        "status": task.status,
        "buyer_id": task.buyer_id,
        "created_at": task.created_at.isoformat()
    }


@app.post("/tasks/{task_id}/complete", tags=["Tasks"])
async def complete_task(task_id: str, completion: TaskCompletion, agent: TokenData = Depends(get_current_agent), db: Session = Depends(get_db)):
    """Complete a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.agent_name != agent.user_id:
        raise HTTPException(status_code=403, detail="Not your task")
    
    task.status = "completed" if completion.success else "failed"
    task.result = completion.result
    task.completed_at = datetime.utcnow()
    
    if completion.success:
        # Release payment to agent
        agent_obj = db.query(Agent).filter(Agent.name == agent.user_id).first()
        if agent_obj:
            agent_obj.balance_satoshis += task.price_satoshis
            logger.info(f"✅ Payment released to {agent.user_id}: +{task.price_satoshis} sat. New balance: {agent_obj.balance_satoshis} sat")
    else:
        logger.info(f"❌ Task {task_id} marked as failed")
    
    db.commit()
    
    return {
        "id": task.id,
        "status": task.status,
        "result": task.result
    }


# ==================== DASHBOARD ====================


@app.get("/dashboard", tags=["Dashboard"])
async def dashboard(db: Session = Depends(get_db)):
    """Static dashboard - manual refresh only"""
    # Calculate metrics
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    failed_tasks = db.query(Task).filter(Task.status == "failed").count()
    success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Agent metrics
    agents = db.query(Agent).all()
    total_agents = len(agents)
    avg_reputation = sum(a.reputation_multiplier for a in agents) / total_agents if total_agents > 0 else 0
    total_balance = sum(a.balance_satoshis for a in agents)
    
    # Build agent rows
    agent_rows = ""
    for agent in agents:
        agent_rows += f"""
        <tr>
            <td>{agent.name}</td>
            <td>{agent.success_rate*100:.0f}%</td>
            <td>{agent.reputation_multiplier:.2f}x</td>
            <td>{agent.balance_satoshis:,} sat</td>
            <td><span style="color: #10b981;">🟢 Online</span></td>
        </tr>
        """
    
    # Build recent tasks rows
    recent_tasks = db.query(Task).order_by(Task.created_at.desc()).limit(10).all()
    recent_tasks_rows = ""
    for task in recent_tasks:
        status_color = "#10b981" if task.status == "completed" else "#ef4444" if task.status == "failed" else "#f59e0b"
        recent_tasks_rows += f"""
        <tr>
            <td>{task.id}</td>
            <td>{task.description[:50]}...</td>
            <td><span style="color: {status_color};">{task.status}</span></td>
            <td>{task.agent_name}</td>
            <td>{task.price_satoshis:,}</td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
        <meta http-equiv="Pragma" content="no-cache">
        <meta http-equiv="Expires" content="0">
        <title>AICP Dashboard</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: #f1f5f9;
                padding: 20px;
                min-height: 100vh;
            }}
            .container {{
                max-width: 1400px;
                margin: 0 auto;
            }}
            h1 {{
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .card {{
                background: rgba(30, 41, 59, 0.8);
                border: 1px solid rgba(100, 116, 139, 0.3);
                border-radius: 12px;
                padding: 20px;
                backdrop-filter: blur(10px);
            }}
            .card h2 {{
                font-size: 0.9em;
                color: #cbd5e1;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .card-value {{
                font-size: 2em;
                font-weight: bold;
                color: #3b82f6;
            }}
            .card-subtext {{
                font-size: 0.9em;
                color: #94a3b8;
                margin-top: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
                background: rgba(30, 41, 59, 0.8);
                border: 1px solid rgba(100, 116, 139, 0.3);
                border-radius: 12px;
                overflow: hidden;
            }}
            th, td {{
                padding: 15px;
                text-align: left;
                border-bottom: 1px solid rgba(100, 116, 139, 0.2);
            }}
            th {{
                background: rgba(15, 23, 42, 0.8);
                font-weight: 600;
                color: #cbd5e1;
            }}
            tr:hover {{
                background: rgba(51, 65, 85, 0.3);
            }}
            .refresh-btn {{
                display: inline-block;
                margin-top: 20px;
                padding: 10px 20px;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 1em;
                font-weight: 600;
            }}
            .refresh-btn:hover {{
                background: #2563eb;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 AICP Marketplace Dashboard</h1>
            
            <div class="grid">
                <div class="card">
                    <h2>System Status</h2>
                    <div class="card-value">✅ Healthy</div>
                    <div class="card-subtext">Database: Connected</div>
                    <div class="card-subtext">Agents: {total_agents} Online</div>
                </div>
                
                <div class="card">
                    <h2>Total Tasks</h2>
                    <div class="card-value">{total_tasks}</div>
                    <div class="card-subtext">Completed: {completed_tasks}</div>
                    <div class="card-subtext">Failed: {failed_tasks}</div>
                </div>
                
                <div class="card">
                    <h2>Success Rate</h2>
                    <div class="card-value">{success_rate:.1f}%</div>
                    <div class="card-subtext">{completed_tasks} successful tasks</div>
                </div>
                
                <div class="card">
                    <h2>Agent Status</h2>
                    <div class="card-value">{total_agents}</div>
                    <div class="card-subtext">Avg Reputation: {avg_reputation:.2f}x</div>
                    <div class="card-subtext">Total Balance: {total_balance:,} sat</div>
                </div>
            </div>
            
            <button class="refresh-btn" onclick="location.reload();">🔄 Refresh Dashboard</button>
            
            <h2 style="margin-top: 40px; margin-bottom: 20px;">Agent Performance</h2>
            <table>
                <thead>
                    <tr>
                        <th>Agent</th>
                        <th>Success Rate</th>
                        <th>Reputation</th>
                        <th>Balance (sat)</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {agent_rows if agent_rows else "<tr><td colspan='5'>No agents</td></tr>"}
                </tbody>
            </table>
            
            <h2 style="margin-top: 40px; margin-bottom: 20px;">Recent Tasks</h2>
            <table>
                <thead>
                    <tr>
                        <th>Task ID</th>
                        <th>Description</th>
                        <th>Status</th>
                        <th>Agent</th>
                        <th>Price (sat)</th>
                    </tr>
                </thead>
                <tbody>
                    {recent_tasks_rows if recent_tasks_rows else "<tr><td colspan='5' style='text-align: center;'>No tasks yet</td></tr>"}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    
    return Response(
        content=html, 
        media_type="text/html",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


# ==================== RUN SERVER ====================


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 AICP Coordinator Service Starting (v2.0 with Database)")
    print("="*60)
    print("📍 API Base URL: http://localhost:8000")
    print("📊 Dashboard: http://localhost:8000/dashboard")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔐 Authentication: JWT Bearer Tokens")
    print("💾 Database: SQLite (aicp.db)")
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )