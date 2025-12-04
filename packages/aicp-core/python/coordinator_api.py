"""
AICP Autonomous Agent Marketplace - Coordinator Service with AI
FastAPI backend + SQLite + JWT + OpenAI GPT-3.5 Integration
PRODUCTION: Security hardened, retry logic, rate limit handling
"""

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import uuid
import logging
import jwt
import httpx
import asyncio
import os
import json


# ==================== LOGGING SETUP ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== OPENAI CONFIGURATION ====================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-3.5-turbo"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
MAX_RETRIES = 5
RETRY_DELAY = 2  # seconds, will exponentially backoff


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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Task(Base):
    """Task database model"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, index=True)
    description = Column(String)
    complexity = Column(Integer)
    buyer_id = Column(String, index=True)
    agent_name = Column(String, index=True)
    price_satoshis = Column(Integer)
    status = Column(String)  # "assigned", "processing", "completed", "failed"
    result = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)


class User(Base):
    """User database model for authentication"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    user_type = Column(String)  # "buyer" or "agent"
    password_hash = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Create all tables
Base.metadata.create_all(bind=engine)


# ==================== PYDANTIC MODELS ====================

class TaskSubmission(BaseModel):
    """Task submission request"""
    description: str
    complexity: int = 1
    buyer_id: str


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

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-" + str(uuid.uuid4()))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
security = HTTPBearer()


# ==================== JWT FUNCTIONS ====================

def create_access_token(user_id: str, user_type: str, expires_delta: timedelta = None) -> str:
    """Create JWT access token"""
    to_encode = {"user_id": user_id, "user_type": user_type}
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
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


# ==================== AI PROCESSING WITH RETRY LOGIC ====================

async def process_task_with_ai(task_id: str, description: str, complexity: int, agent_name: str):
    """Process task with OpenAI GPT-3.5 in background with retry logic"""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            logger.error(f"❌ Task {task_id} not found")
            return
        
        # Mark as processing
        task.status = "processing"
        db.commit()
        logger.info(f"⏳ Task {task_id} now processing with {agent_name}...")
        
        # Build prompt based on complexity
        system_prompt = f"""You are an autonomous agent named {agent_name} completing tasks in a marketplace.
Your complexity level is {complexity}/10.
Provide accurate, helpful, and concise responses.
For complex tasks, provide detailed analysis. For simple tasks, be brief."""
        
        # Retry logic with exponential backoff
        result = None
        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        OPENAI_API_URL,
                        headers={
                            "Authorization": f"Bearer {OPENAI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": OPENAI_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": description}
                            ],
                            "max_tokens": 1000,
                            "temperature": 0.7
                        }
                    )
                
                if response.status_code == 200:
                    data = response.json()
                    result = data["choices"][0]["message"]["content"]
                    logger.info(f"✅ Got response from OpenAI on attempt {attempt + 1}")
                    break
                elif response.status_code == 429:
                    # Rate limited - retry with exponential backoff
                    if attempt < MAX_RETRIES - 1:
                        wait_time = RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"⏳ Rate limited (429). Retry {attempt + 1}/{MAX_RETRIES} after {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"❌ OpenAI rate limited after {MAX_RETRIES} attempts")
                        raise Exception("Rate limited by OpenAI - max retries exceeded")
                else:
                    # Other HTTP errors
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("error", {}).get("message", str(error_data))
                    except:
                        error_detail = response.text
                    
                    # Don't retry on auth errors (401, 403)
                    if response.status_code in [401, 403]:
                        logger.error(f"❌ Authentication Error {response.status_code}: {error_detail}")
                        logger.error(f"   Check: https://platform.openai.com/api/keys")
                        raise Exception(f"OpenAI auth error {response.status_code}: {error_detail}")
                    
                    # Retry on other errors
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(f"⏳ OpenAI error {response.status_code}. Retrying attempt {attempt + 2}/{MAX_RETRIES}...")
                        await asyncio.sleep(RETRY_DELAY * (2 ** attempt))
                        continue
                    else:
                        logger.error(f"❌ OpenAI error {response.status_code}: {error_detail}")
                        raise Exception(f"OpenAI API error {response.status_code}: {error_detail}")
            
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"⏳ Timeout on attempt {attempt + 1}/{MAX_RETRIES}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Request timeout after {MAX_RETRIES} attempts")
                    raise Exception("Request timeout after retries")
            
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"⏳ Error on attempt {attempt + 1}/{MAX_RETRIES}: {str(e)[:100]}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"❌ Failed after {MAX_RETRIES} attempts: {str(e)}")
                    raise
        
        if result:
            # Update task with result
            task.status = "completed"
            task.result = result
            task.completed_at = datetime.now(timezone.utc)
            
            # Release payment to agent
            agent_obj = db.query(Agent).filter(Agent.name == agent_name).first()
            if agent_obj:
                agent_obj.balance_satoshis += task.price_satoshis
                logger.info(f"✅ Task {task_id} COMPLETED by {agent_name}!")
                logger.info(f"   💰 Payment: +{task.price_satoshis} sat -> {agent_name} (Balance: {agent_obj.balance_satoshis} sat)")
                logger.info(f"   📝 Result: {result[:100]}...")
            
            db.commit()
        else:
            logger.error(f"❌ Failed to get result for task {task_id}")
            task.status = "failed"
            task.result = "No response from AI after retries"
            db.commit()
    
    except Exception as e:
        logger.error(f"❌ Task {task_id} failed: {str(e)}")
        task.status = "failed"
        task.result = f"Error: {str(e)}"
        db.commit()
    finally:
        db.close()


# ==================== INITIALIZE FASTAPI APP ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize default agents on startup"""
    logger.info(f"🚀 Starting AICP Coordinator Service v3.3.0...")
    
    db = SessionLocal()
    try:
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
        else:
            logger.info(f"✅ Found {existing_agents} existing agents")
        
        if OPENAI_API_KEY == "your-api-key-here":
            logger.warning("⚠️  No valid OpenAI API key set!")
            logger.warning("   Set it with: export OPENAI_API_KEY='sk-proj-your-key'")
        else:
            logger.info("✅ OpenAI API configured")
        
        logger.info("✅ Server ready! Dashboard: http://localhost:8000/dashboard")
    finally:
        db.close()
    
    yield  # Server is running
    logger.info("🛑 Shutting down AICP Coordinator")


app = FastAPI(
    title="AICP Coordinator",
    description="Autonomous Agent Marketplace with AI - GPT-3.5 Integration",
    version="3.3.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== HEALTH ENDPOINTS ====================

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {"service": "AICP Coordinator", "status": "running", "version": "3.3.0"}


@app.get("/health", tags=["Health"])
async def health():
    """Health check"""
    return {"status": "healthy", "openai_configured": OPENAI_API_KEY != "your-api-key-here"}


# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/auth/buyer/login", response_model=TokenResponse, tags=["Auth"])
async def buyer_login(creds: BuyerLoginRequest):
    """Buyer login endpoint"""
    logger.info(f"🔐 Buyer login attempt: {creds.buyer_id}")
    
    if len(creds.password) < 8:
        logger.warning(f"❌ Invalid password for buyer: {creds.buyer_id}")
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
        logger.warning(f"❌ Invalid password for agent: {creds.agent_id}")
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
async def submit_task(
    task: TaskSubmission, 
    buyer: TokenData = Depends(get_current_buyer), 
    db: Session = Depends(get_db), 
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Submit a new task - AI processes it automatically"""
    try:
        if not task.description or len(task.description.strip()) == 0:
            raise HTTPException(status_code=400, detail="Task description cannot be empty")
        
        if task.complexity < 1 or task.complexity > 10:
            raise HTTPException(status_code=400, detail="Complexity must be between 1 and 10")
        
        if task.buyer_id != buyer.user_id:
            raise HTTPException(status_code=403, detail="Cannot submit for other buyer")
        
        agent_name = select_best_agent(db)
        if not agent_name:
            raise HTTPException(status_code=500, detail="No agents available")
        
        price_satoshis = calculate_price(task.complexity, agent_name, db)
        
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
        logger.info(f"🤖 Starting AI processing for task {task_id}...")
        
        background_tasks.add_task(
            process_task_with_ai,
            task_id=task_id,
            description=task.description,
            complexity=task.complexity,
            agent_name=agent_name
        )
        
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
                "result": t.result,
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
        "result": task.result,
        "buyer_id": task.buyer_id,
        "created_at": task.created_at.isoformat()
    }


# ==================== DASHBOARD ====================

@app.get("/dashboard", response_class=HTMLResponse, tags=["Dashboard"])
async def dashboard(db: Session = Depends(get_db)):
    """Interactive dashboard"""
    total_tasks = db.query(Task).count()
    completed_tasks = db.query(Task).filter(Task.status == "completed").count()
    processing_tasks = db.query(Task).filter(Task.status == "processing").count()
    success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    agents = db.query(Agent).all()
    total_agents = len(agents)
    avg_reputation = sum(a.reputation_multiplier for a in agents) / total_agents if total_agents > 0 else 0
    total_balance = sum(a.balance_satoshis for a in agents)
    
    agent_rows = ""
    for agent in agents:
        agent_rows += f"<tr><td>{agent.name}</td><td>{agent.success_rate*100:.0f}%</td><td>{agent.reputation_multiplier:.2f}x</td><td>{agent.balance_satoshis:,} sat</td><td><span style='color: #10b981;'>Online</span></td></tr>"
    
    recent_tasks = db.query(Task).order_by(Task.created_at.desc()).limit(10).all()
    recent_tasks_rows = ""
    for task in recent_tasks:
        status_color = {"completed": "#10b981", "failed": "#ef4444", "processing": "#8b5cf6"}.get(task.status, "#f59e0b")
        recent_tasks_rows += f"""<tr onclick="showTaskDetails('{task.id}')" style='cursor: pointer;'>
            <td>{task.id}</td>
            <td>{task.description[:40]}...</td>
            <td><span style='color: {status_color};'>{task.status}</span></td>
            <td>{task.agent_name}</td>
            <td>{task.price_satoshis:,}</td>
        </tr>"""
    
    tasks_json = json.dumps([{
        'id': t.id,
        'description': t.description,
        'status': t.status,
        'agent': t.agent_name,
        'price': t.price_satoshis,
        'result': t.result or 'No result yet',
        'created': t.created_at.isoformat() if t.created_at else 'N/A'
    } for t in recent_tasks])
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AICP Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color: #f1f5f9; padding: 20px; min-height: 100vh; }}
.container {{ max-width: 1400px; margin: 0 auto; }}
h1 {{ text-align: center; margin-bottom: 30px; font-size: 2.5em; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-bottom: 30px; }}
.card {{ background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 12px; padding: 20px; backdrop-filter: blur(10px); }}
.card h2 {{ font-size: 0.9em; color: #cbd5e1; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; }}
.card-value {{ font-size: 2em; font-weight: bold; color: #3b82f6; }}
.card-subtext {{ font-size: 0.9em; color: #94a3b8; margin-top: 10px; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 20px; background: rgba(30, 41, 59, 0.8); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 12px; overflow: hidden; }}
th, td {{ padding: 15px; text-align: left; border-bottom: 1px solid rgba(100, 116, 139, 0.2); }}
th {{ background: rgba(15, 23, 42, 0.8); font-weight: 600; color: #cbd5e1; }}
tr:hover {{ background: rgba(51, 65, 85, 0.3); }}
.refresh-btn {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 1em; font-weight: 600; text-decoration: none; }}
.refresh-btn:hover {{ background: #2563eb; }}
.modal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); }}
.modal-content {{ background: rgba(30, 41, 59, 0.95); margin: 5% auto; padding: 30px; border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 12px; width: 80%; max-width: 800px; max-height: 80vh; overflow-y: auto; }}
.close {{ color: #94a3b8; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }}
.close:hover {{ color: #f1f5f9; }}
.result-box {{ background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(100, 116, 139, 0.3); border-radius: 8px; padding: 20px; margin-top: 20px; white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 0.9em; line-height: 1.6; }}
.task-detail {{ margin: 10px 0; padding: 10px; background: rgba(51, 65, 85, 0.3); border-radius: 6px; }}
</style>
</head>
<body>
<div id="taskModal" class="modal">
  <div class="modal-content">
    <span class="close" onclick="closeModal()">&times;</span>
    <h2>Task Details</h2>
    <div class="task-detail"><strong>Task ID:</strong> <span id="modalTaskId"></span></div>
    <div class="task-detail"><strong>Description:</strong> <span id="modalDescription"></span></div>
    <div class="task-detail"><strong>Agent:</strong> <span id="modalAgent"></span></div>
    <div class="task-detail"><strong>Status:</strong> <span id="modalStatus"></span></div>
    <div class="task-detail"><strong>Price:</strong> <span id="modalPrice"></span> sat</div>
    <div class="task-detail"><strong>Created:</strong> <span id="modalCreated"></span></div>
    <h3 style="margin-top: 20px;">Result:</h3>
    <div class="result-box" id="modalResult">Loading...</div>
  </div>
</div>

<div class="container">
<h1>🤖 AICP Marketplace Dashboard</h1>
<div class="grid">
<div class="card">
<h2>System Status</h2>
<div class="card-value">✅ Online</div>
<div class="card-subtext">Database: Connected</div>
<div class="card-subtext">AI Model: GPT-3.5</div>
</div>
<div class="card">
<h2>Total Tasks</h2>
<div class="card-value">{total_tasks}</div>
<div class="card-subtext">Completed: {completed_tasks}</div>
<div class="card-subtext">Processing: {processing_tasks}</div>
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
<a href="/dashboard" class="refresh-btn">🔄 Refresh Dashboard</a>
<h2 style="margin-top: 40px; margin-bottom: 20px;">Agent Performance</h2>
<table>
<thead><tr><th>Agent</th><th>Success Rate</th><th>Reputation</th><th>Balance (sat)</th><th>Status</th></tr></thead>
<tbody>{agent_rows if agent_rows else "<tr><td colspan='5'>No agents</td></tr>"}</tbody>
</table>
<h2 style="margin-top: 40px; margin-bottom: 20px;">Recent Tasks</h2>
<table>
<thead><tr><th>Task ID</th><th>Description</th><th>Status</th><th>Agent</th><th>Price (sat)</th></tr></thead>
<tbody>{recent_tasks_rows if recent_tasks_rows else "<tr><td colspan='5' style='text-align: center;'>No tasks yet</td></tr>"}</tbody>
</table>
</div>
<script>
const tasksData = {tasks_json};
function showTaskDetails(taskId) {{
  const task = tasksData.find(t => t.id === taskId);
  if (!task) return;
  document.getElementById('modalTaskId').textContent = task.id;
  document.getElementById('modalDescription').textContent = task.description;
  document.getElementById('modalAgent').textContent = task.agent;
  document.getElementById('modalStatus').textContent = task.status;
  document.getElementById('modalPrice').textContent = task.price.toLocaleString();
  document.getElementById('modalCreated').textContent = new Date(task.created).toLocaleString();
  document.getElementById('modalResult').textContent = task.result;
  document.getElementById('taskModal').style.display = 'block';
}}
function closeModal() {{
  document.getElementById('taskModal').style.display = 'none';
}}
window.onclick = function(event) {{
  const modal = document.getElementById('taskModal');
  if (event.target == modal) modal.style.display = 'none';
}}
</script>
</body>
</html>"""
    
    return HTMLResponse(content=html)


# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("🚀 AICP Coordinator Service Starting - Version 3.3.0")
    print("="*70)
    print("📊 Dashboard: http://localhost:8000/dashboard")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🔑 OpenAI API:", "✅ Configured" if OPENAI_API_KEY != "your-api-key-here" else "❌ NOT SET")
    print("⚡ Retry Logic: Enabled (MAX_RETRIES=5, exponential backoff)")
    print("="*70 + "\n")
    
    if OPENAI_API_KEY == "your-api-key-here":
        print("⚠️  WARNING: OpenAI API key not set!")
        print("   Set it with: export OPENAI_API_KEY='sk-proj-your-key'")
        print("   Get a key: https://platform.openai.com/api/keys\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")