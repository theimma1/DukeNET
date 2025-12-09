# DukeNET v2.0 - COMPLETE PRODUCTION SYSTEM INTEGRATION GUIDE
# Full end-to-end setup with Duke Labelee ML Model

## 🎯 WHAT YOU GET

A **complete, production-ready AI Agent Marketplace** where:
- ✅ Users (buyers/agents/admins) register & authenticate
- ✅ Buyers submit tasks with complexity ratings & files  
- ✅ Duke MultiModal Model executes tasks & learns from results
- ✅ All results are captured and feed ML training pipeline
- ✅ Model automatically retrains on new data (every 24h or 100 samples)
- ✅ Performance improves over time as Duke learns from successes & failures
- ✅ System includes full monitoring, metrics, and admin controls
- ✅ Bitcoin satoshi pricing with agent reputation multipliers
- ✅ Professional React UI with real-time dashboards

---

## 📦 PROJECT STRUCTURE

```
dukenete/
├── backend/
│   ├── main.py                          (FastAPI app - from dukenete_backend_complete.py)
│   ├── requirements.txt                 (Python dependencies)
│   ├── Dockerfile                       (Docker container)
│   ├── new_labelee_model.py            (Your Duke model - paste here)
│   ├── models/                         (Trained models storage)
│   ├── uploads/                        (File uploads)
│   └── training_data/                  (ML training datasets)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                     (Main component)
│   │   ├── pages/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── RegisterPage.jsx
│   │   │   ├── BuyerDashboard.jsx
│   │   │   ├── AgentDashboard.jsx
│   │   │   ├── AdminDashboard.jsx
│   │   │   └── ModelTrainingDashboard.jsx
│   │   ├── components/
│   │   │   ├── Navigation.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── TaskCreationForm.jsx
│   │   │   ├── FileUploader.jsx
│   │   │   ├── TaskList.jsx
│   │   │   ├── ResultsDisplay.jsx
│   │   │   ├── SystemMetrics.jsx
│   │   │   ├── AgentLeaderboard.jsx
│   │   │   └── MLTrainingPanel.jsx
│   │   ├── stores/
│   │   │   ├── authStore.js
│   │   │   └── marketplaceStore.js
│   │   ├── styles/
│   │   │   ├── App.css
│   │   │   └── tailwind.css
│   │   ├── main.jsx
│   │   └── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── Dockerfile
│   └── .env.local
│
├── docker-compose.yml
├── .env.example
├── README.md
└── requirements.txt

```

---

## 🚀 QUICK START (5 MINUTES)

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone repo and enter directory
git clone <your-repo> dukenete
cd dukenete

# 2. Create .env file
cp .env.example .env

# 3. Edit .env with your settings
# - Change POSTGRES_PASSWORD
# - Set SECRET_KEY to a strong random string
# - Adjust API_URL if needed

# 4. Start everything with Docker
docker-compose up -d

# 5. Wait for services to be ready (about 30 seconds)
docker-compose logs -f backend

# 6. Access the system
# Frontend:  http://localhost:3001
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
```

### Option 2: Manual Setup

#### Backend Setup:
```bash
cd backend

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Create PostgreSQL database (use your credentials)
createdb dukenete
createuser dukenete_user

# Set environment variables
cp ../.env.example .env
# Edit .env with DATABASE_URL and SECRET_KEY

# Run migrations (if using Alembic - optional)
# alembic upgrade head

# Start backend
python main.py
# Server runs on http://localhost:8000
```

#### Frontend Setup:
```bash
cd frontend

# Install Node dependencies
npm install

# Create env file
cp ../.env.example .env.local

# Start dev server
npm run dev
# Frontend runs on http://localhost:3001
```

#### Database Setup (if not using Docker):
```bash
# PostgreSQL must be running

# Connect to PostgreSQL
psql -U postgres

# Run these commands:
CREATE DATABASE dukenete;
CREATE USER dukenete_user WITH PASSWORD 'your_secure_password';
ALTER ROLE dukenete_user SET client_encoding TO 'utf8';
ALTER ROLE dukenete_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE dukenete_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE dukenete TO dukenete_user;

# Exit psql
\q
```

---

## 📝 DATABASE SCHEMA (Automatically Created)

The backend automatically creates these tables on first run:

```sql
-- Users & Authentication
users
├── id (UUID)
├── email (unique)
├── password_hash
├── user_type (buyer|agent|admin)
├── full_name
├── created_at
└── is_active

-- File Storage
files
├── id (UUID)
├── user_id (FK users)
├── filename
├── file_type
├── file_size
├── storage_path
├── file_hash (SHA256)
└── created_at

-- Tasks
tasks
├── id (UUID)
├── buyer_id (FK users)
├── description
├── complexity (1-10)
├── assigned_agent
├── price_satoshis
├── status (created|assigned|executing|completed|failed)
├── created_at
├── completed_at
└── updated_at

-- Results
results
├── id (UUID)
├── task_id (FK tasks)
├── agent_name
├── result_text
├── success (boolean)
├── confidence_score (0-1)
├── execution_time_ms
├── metadata (JSON)
└── created_at

-- Training Data (for ML)
training_data
├── id (UUID)
├── task_id (FK tasks)
├── result_id (FK results)
├── input_data (JSON)
├── output_data (JSON)
├── success (boolean)
├── agent_name
├── model_version
└── created_at

-- Model Versions
model_versions
├── id (UUID)
├── version_number
├── model_name (default: duke-mm)
├── created_at
├── training_samples
├── validation_accuracy
├── validation_f1
├── is_production
└── metadata (JSON)

-- Agent Statistics
agent_stats
├── id (UUID)
├── agent_name (unique)
├── total_tasks
├── successful_tasks
├── failed_tasks
├── success_rate
├── reputation_multiplier
├── total_earnings_satoshis
├── last_task_at
└── updated_at
```

---

## 🔑 API ENDPOINTS (Full List)

### Authentication
```
POST   /api/v2/auth/register          Register new user
POST   /api/v2/auth/login             Login & get token
GET    /api/v2/auth/profile           Get current user
```

### Files
```
POST   /api/v2/files/upload           Upload file
GET    /api/v2/files/list             List user files
GET    /api/v2/files/{file_id}        Download file
DELETE /api/v2/files/{file_id}        Delete file
```

### Tasks
```
POST   /api/v2/tasks/create           Create new task
GET    /api/v2/tasks/list             List tasks (filtered by user)
GET    /api/v2/tasks/{task_id}        Get task details
```

### Results & Feedback
```
POST   /api/v2/results/submit         Submit task result
GET    /api/v2/results/{task_id}      Get task results
```

### Model Training
```
POST   /api/v2/model/train            Trigger model training
GET    /api/v2/model/status           Get model status
GET    /api/v2/model/metrics          Get model performance metrics
```

### Admin
```
GET    /api/v2/admin/metrics          System-wide metrics
GET    /api/v2/admin/agents           List all agents with stats
```

### Health
```
GET    /api/v2/health                 Health check
GET    /api/v2/version                API version
```

---

## 🤖 DUKE LABELEE MODEL INTEGRATION

### How Your Model Learns:

1. **Task Submitted** → Description stored in `training_data.input_data`
2. **Agent Executes** → Uses current Duke MM model version
3. **Result Submitted** → Stored in `training_data.output_data`
4. **Success/Failure** → Logged as `training_data.success`
5. **Automatic Training** (when 100+ new samples collected or 24h passed):
   - Query results from database
   - Prepare train/validation split (80/20)
   - Fine-tune Duke model on new data
   - Evaluate on validation set
   - Compare with previous model
   - If better: promote to production (update `model_versions.is_production`)
6. **Agent Reputation Updated** → Based on success rate
7. **Next Cycle** → New model learns from ALL previous + new data

### Custom Duke Model Integration:

```python
# In backend/main.py, create a wrapper:

from new_labelee_model import EnhancedLabeleeFoundation, EnhancedModelConfig

class DukeMMAgent:
    def __init__(self):
        self.config = EnhancedModelConfig()
        self.model = EnhancedLabeleeFoundation(self.config)
        # Load weights from trained checkpoint
        checkpoint = torch.load("models/duke-mm-latest.pt")
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.eval()
    
    def process_task(self, task_description, files=[]):
        # Preprocess inputs
        # Run through model
        # Get predictions + confidence
        return {
            'result': output_text,
            'confidence': confidence_score,
            'execution_time_ms': execution_time
        }

# Use in MLTrainingPipeline:
class MLTrainingPipeline:
    async def train_model(self, db):
        # Get training data
        # Prepare batch
        # Train Duke model
        # Evaluate
        # Promote if better
        pass
```

### Training Status Monitoring:

Admin dashboard shows:
- Current model version
- Validation accuracy
- F1 score
- Number of training samples
- Last training date
- Agent reputation multipliers
- System success rate trends

---

## 👥 USER ROLES & PERMISSIONS

### Buyer
- ✅ Register & login
- ✅ Create tasks (set description, complexity, attach files)
- ✅ Upload files (CSV, JSON, PDF, images, etc.)
- ✅ View task history & status
- ✅ See results when completed
- ✅ Track total spent in satoshis
- ❌ Cannot create agents or access admin features

### Agent
- ✅ Register & login
- ✅ View assigned tasks
- ✅ Execute tasks (process files/data)
- ✅ Submit results with confidence scores
- ✅ Track success rate & earnings
- ✅ See reputation multiplier
- ❌ Cannot create tasks or manage system

### Admin
- ✅ All buyer & agent permissions
- ✅ View system-wide metrics
- ✅ Manage users & agents
- ✅ Trigger model training manually
- ✅ Monitor Duke model performance
- ✅ View agent leaderboard
- ✅ Download/export data

---

## 💰 SATOSHI PRICING FORMULA

```
Price (satoshis) = 100,000 × Task_Complexity × Agent_Reputation_Multiplier

Examples:
- Complexity 1 task, agent-1 (2.0x multiplier) = 100k × 1 × 2.0 = 200,000 sat
- Complexity 5 task, agent-2 (1.8x multiplier) = 100k × 5 × 1.8 = 900,000 sat
- Complexity 10 task, Duke MM (2.0x multiplier) = 100k × 10 × 2.0 = 2,000,000 sat

Agent Reputation Multipliers (earned):
- Success Rate 95%+ → 2.0x (maximum)
- Success Rate 85%+ → 1.8x
- Success Rate 70%+ → 1.5x
- Success Rate <70% → 1.2x (minimum)
```

---

## 📊 ADMIN DASHBOARD FEATURES

Real-time monitoring of:
- Total tasks created
- Total users registered
- Total agents active
- Average system success rate
- Total satoshis transacted
- Training samples collected
- Latest model version & accuracy
- Agent leaderboard (ranked by reputation & earnings)
- Model training history
- System health indicators

---

## 🔒 SECURITY FEATURES

- ✅ JWT token-based authentication
- ✅ Bcrypt password hashing (10 rounds)
- ✅ CORS protection
- ✅ File type validation
- ✅ File size limits (50MB max)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Rate limiting ready (add Redis + FastAPI-Limiter)
- ✅ Secure headers recommended (add python-dotenv + .env)
- ✅ Environment variable protection
- ✅ Transaction integrity for satoshi settlements

---

## 📈 SCALING RECOMMENDATIONS

As you grow:

1. **Database**
   - Add read replicas for analytics queries
   - Implement connection pooling (pgBouncer)
   - Archive old training data to S3
   
2. **Backend**
   - Use Gunicorn + Nginx reverse proxy
   - Add Redis for caching & sessions
   - Implement message queues (Celery + RabbitMQ) for async training
   - Auto-scale with Kubernetes

3. **Frontend**
   - Build static assets with `npm run build`
   - Serve from CDN (CloudFront, etc.)
   - Implement service workers for offline support

4. **ML**
   - Train on GPU cluster (CUDA/Torch)
   - Use model quantization for faster inference
   - Distributed training with PyTorch DDP
   - A/B test models before production

---

## 🆘 TROUBLESHOOTING

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000
kill -9 <PID>

# Check database connection
psql postgresql://dukenete_user:password@localhost/dukenete

# Check logs
tail -f dukenete_backend.log
```

### Frontend can't connect to backend
```bash
# Check backend is running
curl http://localhost:8000/api/v2/health

# Check CORS is enabled (should be in main.py)
# Check .env.local has correct VITE_API_URL

# Clear browser cache
# In DevTools: Application → Storage → Clear Site Data
```

### Database migration issues
```bash
# Reset database (WARNING: deletes all data)
dropdb dukenete
createdb dukenete

# Restart backend to recreate schema
python main.py
```

### Model training not triggering
```bash
# Check training_data table has entries
psql dukenete
SELECT COUNT(*) FROM training_data;

# Manually trigger
curl -X POST http://localhost:8000/api/v2/model/train \
  -H "Authorization: Bearer <admin_token>"

# Check logs for training errors
tail -f dukenete_backend.log | grep -i training
```

---

## 📚 FURTHER LEARNING

- FastAPI docs: https://fastapi.tiangolo.com/
- SQLAlchemy: https://www.sqlalchemy.org/
- React docs: https://react.dev/
- PyTorch: https://pytorch.org/
- PostgreSQL: https://www.postgresql.org/docs/
- Docker: https://docs.docker.com/

---

## 🎯 NEXT STEPS

1. ✅ **Setup**: Follow Quick Start above
2. ✅ **Customize**: Edit config in backend/main.py
3. ✅ **Train**: Submit test tasks, get them executed
4. ✅ **Monitor**: Watch model improve in Admin Dashboard
5. ✅ **Deploy**: Follow production deployment guide
6. ✅ **Scale**: Use recommendations above

---

## 📄 LICENSE & SUPPORT

Built with ❤️ for the DukeNET marketplace.

For support, check:
- API Docs at /docs
- Backend logs: dukenete_backend.log
- Frontend console: Browser DevTools
- Database: psql dukenete

---

**Ready to launch your self-improving AI agent marketplace? Let's go! 🚀**
