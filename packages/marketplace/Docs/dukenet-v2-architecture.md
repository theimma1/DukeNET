# DukeNET Marketplace: Self-Improving AI Agent System
## Complete Architecture & Implementation Plan

**Status:** Production-Ready Specification  
**Version:** 2.0 - Self-Improving AI Agent Marketplace  
**Date:** December 6, 2025

---

## PART 1: SYSTEM ARCHITECTURE OVERVIEW

### High-Level System Design

```
┌────────────────────────────────────────────────────────────────┐
│                    DukeNET Marketplace v2.0                     │
│              Self-Improving AI Agent Marketplace                │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Frontend (React + Auth)         Backend (FastAPI)              │
│  ┌──────────────────────┐        ┌──────────────────────┐      │
│  │ Login/Dashboard      │───────▶│ Auth Service (JWT)   │      │
│  │ File Upload          │        │ Task Coordinator     │      │
│  │ Results Display      │        │ File Handler         │      │
│  │ Model Training UI    │        │ Results Processor    │      │
│  └──────────────────────┘        │ Model Training API   │      │
│                                  └──────────────────────┘      │
│                                           │                     │
│                                           ▼                     │
│  ┌────────────────────────────────────────────────────────┐   │
│  │              Data Pipeline & Storage                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │PostgreSQL│  │File Store│  │Cache     │              │   │
│  │  │Database  │  │(S3/Local)│  │(Redis)   │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │           ML Training Pipeline (MLOps)                  │   │
│  │  ┌───────────┐  ┌──────────┐  ┌──────────┐             │   │
│  │  │Data Prep  │─▶│Training  │─▶│Evaluation│             │   │
│  │  │(80/20 split)│ │(Duke MM) │  │(Metrics) │             │   │
│  │  └───────────┘  └──────────┘  └──────────┘             │   │
│  │         │            │             │                    │   │
│  │         └────────────┴─────────────┘                    │   │
│  │              Model Registry                             │   │
│  │         (Versioning & Rollback)                         │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │        Agent Pool & Execution                           │   │
│  │  ┌──────────────────────────────────────┐              │   │
│  │  │ Duke MultiModal Model (v1, v2, v3...) │             │   │
│  │  │ - Real-time predictions               │             │   │
│  │  │ - Learns from task outcomes           │             │   │
│  │  │ - Improves with each iteration        │             │   │
│  │  └──────────────────────────────────────┘              │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐               │   │
│  │  │Agent 1   │ │Agent 2   │ │Agent 3   │               │   │
│  │  │(Optional)│ │(Optional)│ │(Optional)│               │   │
│  │  └──────────┘ └──────────┘ └──────────┘               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │        Monitoring & Observability                       │   │
│  │  - Real-time metrics dashboard                         │   │
│  │  - Model performance tracking                          │   │
│  │  - Task success/failure logs                           │   │
│  │  - Agent learning progress                             │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

---

## PART 2: KEY FEATURES & CAPABILITIES

### 2.1 User Authentication & Authorization

**JWT-Based Token System:**
- Register new users (buyers/agents/admin)
- Login with secure password hashing (bcrypt)
- Token refresh mechanism
- Role-based access control (RBAC)
- Multi-tenant support (future)

**Database Schema:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    user_type ENUM('buyer', 'agent', 'admin') NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2.2 Data Ingestion & File Handling

**Supported File Types:**
- CSV (task datasets)
- JSON (structured data)
- PDF (documents/specs)
- Images (training data)
- Raw text files

**Upload Pipeline:**
```
User Upload → Validation → Storage → Processing → Indexing
    │            │             │         │           │
    └─ Size check └─ Type check └─ S3/Local └─ Metadata └─ DB
```

**File Management:**
```python
class FileHandler:
    - upload_file(file, user_id)
    - validate_format(file)
    - extract_metadata(file)
    - store_file(file, storage_type='s3'|'local')
    - list_user_files(user_id)
    - delete_file(file_id)
    - get_file_stats(file_id)
```

### 2.3 Task & Results System

**Task Lifecycle:**
```
1. CREATE TASK
   ├─ Description: string
   ├─ Complexity: 1-10
   ├─ Files: array[file_id]
   ├─ Buyer ID: uuid
   └─ Created At: timestamp

2. ASSIGN AGENT
   ├─ Auto-select best agent (Duke MM, agent-1, agent-2, agent-3)
   ├─ Calculate price (100k × complexity × reputation)
   ├─ Set status: "assigned"
   └─ Notify agent

3. EXECUTE TASK
   ├─ Agent receives task
   ├─ Process files/data
   ├─ Generate results
   └─ Submit for validation

4. CAPTURE RESULTS
   ├─ Result text/output
   ├─ Execution time
   ├─ Success status (pass/fail)
   ├─ Confidence score
   ├─ Reasoning/explanation
   └─ Timestamp

5. SETTLEMENT & LEARNING
   ├─ Release satoshi payment (if success)
   ├─ Log to training database
   ├─ Trigger model retraining
   ├─ Update agent reputation
   └─ Archive for historical analysis
```

**Results Database Schema:**
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    buyer_id UUID REFERENCES users(id),
    description TEXT NOT NULL,
    complexity INT CHECK (complexity >= 1 AND complexity <= 10),
    assigned_agent VARCHAR NOT NULL,
    price_satoshis INT NOT NULL,
    status ENUM('created', 'assigned', 'executing', 'completed', 'failed'),
    created_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE results (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    agent_name VARCHAR NOT NULL,
    result_text TEXT,
    success BOOLEAN NOT NULL,
    confidence_score FLOAT,
    execution_time_ms INT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE training_data (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    result_id UUID REFERENCES results(id),
    input_data JSONB,
    output_data JSONB,
    success BOOLEAN,
    agent_name VARCHAR,
    model_version VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 2.4 ML Training Pipeline Integration

**Continuous Training Architecture:**

```python
class MLPipeline:
    def prepare_training_data():
        """Collect passed/failed tasks from training_data table"""
        - Query results from last N days
        - Filter: success=true AND confidence>0.7
        - Split: 80% train, 20% validation
        - Balance: equal passed/failed samples
        - Return: (X_train, y_train, X_val, y_val)
    
    def train_model():
        """Train Duke MultiModal Model on new data"""
        - Load latest base model
        - Fine-tune on new training data
        - Epoch-based training with early stopping
        - Track loss, accuracy, F1 score
        - Return: trained_model, metrics
    
    def evaluate_model():
        """Test model on validation set"""
        - Precision, recall, F1
        - Confusion matrix
        - Feature importance
        - Compare vs baseline
        - Return: evaluation_metrics
    
    def promote_model():
        """Move best model to production"""
        - Check if new_model_accuracy > current_model_accuracy
        - If yes: promote to production, increment version
        - If no: keep current model, log metrics
        - Archive old model (can rollback)
        - Update model registry
```

**Training Triggers:**
1. **Scheduled:** Every 24 hours (nightly)
2. **On-Demand:** Manual trigger by admin
3. **Event-Based:** After 100 new results collected
4. **Performance-Based:** If success rate drops below 85%

### 2.5 Duke MultiModal Model as Primary Agent

**Model Integration:**
```python
class DukeMMAgent:
    def __init__(self, model_version='latest'):
        self.model = load_model(f'duke-mm-{model_version}.pth')
        self.reputation = 2.0  # Start high, adjust based on performance
        self.success_rate = 0.95
        self.tasks_completed = 0
        self.earnings_satoshis = 0
    
    def process_task(self, task_data, files):
        """Execute task using multimodal understanding"""
        - Load files (images, text, data)
        - Process with multimodal encoder
        - Generate predictions
        - Produce structured output
        - Calculate confidence
        - Return: (result, confidence, execution_time)
    
    def update_reputation(self, success_rate):
        """Adjust multiplier based on performance"""
        - Track last 100 tasks
        - Calculate success rate
        - Update: reputation = 1.2 + (success_rate - 0.7) * 4
        - Min: 1.2x, Max: 2.0x
    
    def learn_from_feedback(self, task_result):
        """Collect data for next training cycle"""
        - Store in training_data table
        - Track: input, output, success/failure
        - Aggregate features for model improvement
```

**Model Architecture (Conceptual):**
```
Input Layer (Multimodal)
├─ Text Encoder (BERT-based)
├─ Image Encoder (Vision Transformer)
├─ Data Encoder (Tabular MLP)
└─ Audio Encoder (Wav2Vec, if applicable)
         │
         ▼
    Fusion Layer (Multi-Head Attention)
         │
         ▼
    Task-Specific Heads
    ├─ Classification Head
    ├─ Regression Head
    ├─ Generation Head
    └─ Confidence Head
         │
         ▼
    Output: (prediction, confidence, explanation)
```

### 2.6 Professional UI Improvements

**Dashboard Components:**

1. **Authentication Pages**
   - Login/Register forms
   - Forgot password flow
   - Profile management

2. **Buyer Dashboard**
   - Task submission form
   - File upload area (drag-drop)
   - Task history & results
   - Real-time status updates
   - Success/failure analytics

3. **Agent Dashboard**
   - Task queue
   - Assigned tasks
   - Execution interface
   - Results submission
   - Earnings & reputation tracking

4. **Admin Dashboard**
   - User management
   - System metrics
   - Model performance tracking
   - Training pipeline status
   - Agent reputation leaderboard

5. **Model Training Dashboard**
   - Training progress (loss curves)
   - Validation metrics
   - Model version history
   - Performance comparison (old vs new)
   - Promotion/rollback controls

---

## PART 3: IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-2)
- [ ] Set up PostgreSQL database
- [ ] Implement user authentication (JWT)
- [ ] Create file upload system
- [ ] Build React authentication UI
- [ ] Deploy to localhost:3001

### Phase 2: Core Functionality (Weeks 3-4)
- [ ] Implement task submission & assignment
- [ ] Build results capture system
- [ ] Create buyer/agent dashboards
- [ ] Integrate Duke MM as agent
- [ ] Professional UI styling

### Phase 3: ML Pipeline (Weeks 5-6)
- [ ] Build training data pipeline
- [ ] Implement model training scripts
- [ ] Create model registry
- [ ] Automated retraining triggers
- [ ] Model performance monitoring

### Phase 4: Advanced Features (Weeks 7-8)
- [ ] Model versioning & rollback
- [ ] A/B testing framework
- [ ] Feedback loops & learning
- [ ] Advanced analytics
- [ ] Production deployment

---

## PART 4: SETUP INSTRUCTIONS

### Prerequisites
```bash
# Backend
- Python 3.10+
- PostgreSQL 13+
- FastAPI, SQLAlchemy, Pydantic
- PyTorch, scikit-learn (for ML)

# Frontend
- Node.js 16+
- React 18
- TailwindCSS or similar

# Infrastructure
- Docker & Docker Compose
- (Optional) AWS S3 for file storage
```

### Quick Start

**1. Clone and Setup Backend:**
```bash
cd /path/to/DukeNET/backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Run backend
python main.py
# Starts on http://localhost:8000
```

**2. Setup Frontend:**
```bash
cd /path/to/DukeNET/frontend
npm install
npm start
# Runs on http://localhost:3001
```

**3. Access System:**
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## PART 5: API ENDPOINTS (v2.0)

### Authentication
```
POST   /api/v2/auth/register
POST   /api/v2/auth/login
POST   /api/v2/auth/refresh
POST   /api/v2/auth/logout
GET    /api/v2/auth/profile
PUT    /api/v2/auth/profile
```

### Tasks
```
POST   /api/v2/tasks/create
GET    /api/v2/tasks/list
GET    /api/v2/tasks/{task_id}
POST   /api/v2/tasks/{task_id}/submit-result
GET    /api/v2/tasks/{task_id}/results
```

### Files
```
POST   /api/v2/files/upload
GET    /api/v2/files/list
GET    /api/v2/files/{file_id}
DELETE /api/v2/files/{file_id}
```

### Results & Feedback
```
POST   /api/v2/results/create
GET    /api/v2/results/list
GET    /api/v2/results/{result_id}
POST   /api/v2/results/{result_id}/feedback
```

### Model Training
```
POST   /api/v2/model/train
GET    /api/v2/model/status
GET    /api/v2/model/metrics
POST   /api/v2/model/promote/{version}
```

### Admin
```
GET    /api/v2/admin/users
GET    /api/v2/admin/agents
GET    /api/v2/admin/system-metrics
POST   /api/v2/admin/trigger-retraining
```

---

## PART 6: DATABASE SCHEMA (Complete)

```sql
-- Users & Authentication
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR NOT NULL,
    user_type ENUM('buyer', 'agent', 'admin') NOT NULL,
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Files
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR NOT NULL,
    file_type VARCHAR(50),
    file_size INT,
    storage_path VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id UUID REFERENCES users(id),
    description TEXT NOT NULL,
    complexity INT CHECK (complexity >= 1 AND complexity <= 10),
    assigned_agent VARCHAR NOT NULL,
    price_satoshis INT NOT NULL,
    status ENUM('created', 'assigned', 'executing', 'completed', 'failed') DEFAULT 'created',
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Task Files (Many-to-Many)
CREATE TABLE task_files (
    task_id UUID REFERENCES tasks(id),
    file_id UUID REFERENCES files(id),
    PRIMARY KEY (task_id, file_id)
);

-- Results
CREATE TABLE results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    agent_name VARCHAR NOT NULL,
    result_text TEXT,
    success BOOLEAN NOT NULL,
    confidence_score FLOAT,
    execution_time_ms INT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Training Data (for ML pipeline)
CREATE TABLE training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id),
    result_id UUID REFERENCES results(id),
    input_data JSONB NOT NULL,
    output_data JSONB NOT NULL,
    success BOOLEAN NOT NULL,
    agent_name VARCHAR,
    model_version VARCHAR,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Model Versions
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_number INT NOT NULL,
    model_name VARCHAR DEFAULT 'duke-mm',
    created_at TIMESTAMP DEFAULT NOW(),
    training_samples INT,
    validation_accuracy FLOAT,
    validation_f1 FLOAT,
    is_production BOOLEAN DEFAULT FALSE,
    metadata JSONB
);

-- Agent Reputation Tracking
CREATE TABLE agent_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR UNIQUE NOT NULL,
    total_tasks INT DEFAULT 0,
    successful_tasks INT DEFAULT 0,
    failed_tasks INT DEFAULT 0,
    success_rate FLOAT,
    reputation_multiplier FLOAT DEFAULT 1.2,
    total_earnings_satoshis BIGINT DEFAULT 0,
    last_task_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## PART 7: KEY FEATURES BREAKDOWN

### Real-Time Feedback Loop

**System Flow:**
```
Task Submitted
    ↓
Agent Executes (uses current Duke MM model)
    ↓
Results Captured (success/failure)
    ↓
Logged to Training Data
    ↓
Performance Metrics Calculated
    ↓
Every 24h or 100 samples:
    ├─ Prepare training batch
    ├─ Retrain Duke MM model
    ├─ Evaluate on validation set
    ├─ Compare vs current production model
    └─ Promote if better (or keep current)
```

### Learning from Failures

**Key Insight:**
- Failed tasks are MOST valuable for learning
- System stores both successful and failed executions
- Model learns: "What NOT to do"
- Reduces failure rate over time

**Example:**
```
Task: Classify medical images
Model v1: 85% accuracy (15% failures)
  → Collect 100 failures
  → Retrain with failures as hard examples
Model v2: 92% accuracy (8% failures)
  → Better at edge cases
```

### Self-Improving Agent Lifecycle

**Duke MM Agent Evolution:**
```
Day 1: Fresh model
  - Reputation: 2.00x
  - Success rate: 95%
  - Learning capacity: High

Week 1: First 500 tasks
  - Failures analyzed
  - Model retrained
  - Reputation adjusts based on actual success

Month 1: 5,000 tasks completed
  - Significant learning from diverse tasks
  - Model becomes task-specialist
  - Success rate improves to 97%+
  - Reputation solidifies

Ongoing: Continuous improvement
  - Learns from every task
  - Becomes only agent (others optional)
  - Monopolizes marketplace execution
  - Reaches human-level or better performance
```

---

## PART 8: DEPLOYMENT CHECKLIST

### Before Production Launch

- [ ] Database backup strategy
- [ ] API rate limiting
- [ ] CORS configuration
- [ ] SSL/TLS certificates
- [ ] Environment variables secured
- [ ] Logging and monitoring setup
- [ ] Error handling comprehensive
- [ ] Load testing completed
- [ ] Security audit passed
- [ ] Disaster recovery plan

### Ongoing Operations

- [ ] Monitor training pipeline success rate
- [ ] Track model performance metrics
- [ ] Watch for data drift
- [ ] Maintain model version history
- [ ] Regular database backups
- [ ] System health checks
- [ ] User feedback collection
- [ ] Performance optimization

---

## CONCLUSION

DukeNET v2.0 is a **self-improving AI agent marketplace** where:

✅ Buyers submit tasks with files and complexity ratings  
✅ Duke MultiModal Model (and optional agents) execute tasks  
✅ Results are captured and logged  
✅ Model continuously learns from all task outcomes  
✅ Performance improves with each cycle  
✅ Eventually Duke MM becomes the only agent needed  

**The magic:** Every failed task teaches the model. Every success validates its approach. Over time, the system becomes increasingly intelligent and effective.

**Timeline to Autonomy:** 
- Month 1: 5,000 tasks, 90%+ success rate
- Month 3: 20,000+ tasks, 95%+ success rate  
- Month 6: Duke MM runs entire marketplace solo

---

*Generated: December 6, 2025*  
*DukeNET Marketplace v2.0 - Self-Improving AI Agent System*  
*Status: Production-Ready Architecture*
