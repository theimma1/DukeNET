# DukeNET v2.0 - QUICK REFERENCE & CHECKLIST

## 📋 WHAT'S INCLUDED

### ✅ Complete Backend (FastAPI)
- **dukenete_backend_complete.py** - Full production backend with:
  - User authentication (JWT, bcrypt)
  - Task management system
  - File upload/download
  - Results tracking
  - ML training pipeline
  - Agent reputation tracking
  - Bitcoin satoshi pricing
  - Admin metrics & monitoring

### ✅ Complete Frontend (React)
- **REACT_DASHBOARD_COMPONENTS.md** - Professional UI with:
  - Login/Register pages
  - Buyer dashboard (create tasks, upload files, view results)
  - Agent dashboard (execute tasks)
  - Admin dashboard (system monitoring)
  - Model training controls
  - Real-time metrics
  - Responsive design (Tailwind CSS)

### ✅ Database Setup
- **PostgreSQL schema** - Automatically created with:
  - Users & authentication
  - Files & uploads
  - Tasks & results
  - Training data for ML
  - Model versions & history
  - Agent statistics

### ✅ ML Integration
- **Your Duke Labelee Model** - Integrated to:
  - Learn from all task descriptions & results
  - Automatically retrain every 24h or 100 samples
  - Improve accuracy over time
  - Track performance metrics
  - Manage model versions

### ✅ Deployment
- **Docker Compose** - One-command deployment
- **Complete setup guides** - Step-by-step instructions
- **Production configuration** - Environment-ready setup

---

## 🚀 IMMEDIATE NEXT STEPS (Do These First)

### 1. PROJECT SETUP (5 minutes)
```bash
# Create project directory
mkdir dukenete && cd dukenete
mkdir backend frontend

# Copy backend file
cp dukenete_backend_complete.py backend/main.py

# Create requirements.txt in backend/
# Use the requirements from COMPLETE_SETUP_GUIDE.md
```

### 2. DATABASE SETUP (5 minutes)
```bash
# Option A: Use Docker Compose (recommended)
docker-compose up -d

# Option B: Manual PostgreSQL
createdb dukenete
createuser dukenete_user WITH PASSWORD 'secure_password'
GRANT ALL PRIVILEGES ON DATABASE dukenete TO dukenete_user;
```

### 3. BACKEND STARTUP (2 minutes)
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
# Runs on http://localhost:8000
```

### 4. FRONTEND SETUP (3 minutes)
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3001
```

### 5. TEST THE SYSTEM (5 minutes)
```bash
# Check backend is running
curl http://localhost:8000/api/v2/health

# Check API docs
Open http://localhost:8000/docs in browser

# Check frontend
Open http://localhost:3001 in browser

# Try login with demo credentials:
Email: buyer@dukenete.com
Password: password
```

---

## 📚 FILE REFERENCE

### Backend Files to Create
1. **backend/main.py** 
   - Source: dukenete_backend_complete.py
   - Description: Complete FastAPI application

2. **backend/requirements.txt**
   - From: COMPLETE_SETUP_GUIDE.md section 1
   - Description: Python dependencies

3. **backend/Dockerfile**
   - From: COMPLETE_SETUP_GUIDE.md section 5
   - Description: Docker container config

4. **backend/new_labelee_model.py**
   - Source: Your new_labelee_model.py file
   - Description: Duke Labelee ML model

5. **.env**
   - From: .env.example in COMPLETE_SETUP_GUIDE.md
   - Description: Configuration variables

### Frontend Files to Create
1. **frontend/src/App.jsx**
   - From: REACT_DASHBOARD_COMPONENTS.md
   - Description: Main React component

2. **frontend/src/stores/authStore.js**
   - From: REACT_DASHBOARD_COMPONENTS.md
   - Description: Authentication state management

3. **frontend/src/stores/marketplaceStore.js**
   - From: REACT_DASHBOARD_COMPONENTS.md
   - Description: Marketplace state management

4. **frontend/src/pages/** (all page components)
   - From: REACT_DASHBOARD_COMPONENTS.md
   - Description: Dashboard pages

5. **frontend/src/components/** (all components)
   - From: REACT_DASHBOARD_COMPONENTS.md
   - Description: UI components

6. **frontend/package.json**
   - From: COMPLETE_SETUP_GUIDE.md section 2
   - Description: npm dependencies

### Configuration Files
1. **docker-compose.yml**
   - From: COMPLETE_SETUP_GUIDE.md section 4
   - Description: Docker services config

2. **.env.example**
   - From: COMPLETE_SETUP_GUIDE.md section 3
   - Description: Environment variables template

---

## 🎯 KEY CONFIGURATION

### Backend Config (in main.py)
```python
Config.DATABASE_URL = "postgresql://user:password@localhost:5432/dukenete"
Config.SECRET_KEY = "your-secret-key-change-in-production"
Config.BASE_SATOSHI_PRICE = 100_000
Config.TRAINING_TRIGGER_SAMPLES = 100  # Retrain after 100 new results
Config.TRAINING_TRIGGER_HOURS = 24  # Or every 24 hours
```

### Frontend Config (in .env.local)
```
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000
VITE_ENABLE_TRAINING_DASHBOARD=true
VITE_ENABLE_FILE_UPLOAD=true
```

---

## 🔧 HOW THE SYSTEM WORKS

### Task Lifecycle
```
1. Buyer creates task
   ↓
2. System assigns to best agent (Duke MM preferred)
   ↓
3. System calculates price: 100k sat × complexity × reputation multiplier
   ↓
4. Agent executes task using Duke model
   ↓
5. Agent submits result + confidence score
   ↓
6. Result stored in database & training pipeline
   ↓
7. Agent earnings calculated & reputation updated
   ↓
8. Every 100 results or 24 hours: Trigger model retraining
   ↓
9. New model trained on all previous + new data
   ↓
10. If better accuracy: Promote to production
```

### ML Training Flow
```
Collect Training Data (from results table)
        ↓
Prepare Batch (80% train, 20% validation)
        ↓
Train Duke Model (fine-tune on new data)
        ↓
Evaluate (measure accuracy, F1 score)
        ↓
Compare with Previous Model
        ↓
IF better: Promote to production
ELSE: Keep current model
        ↓
Store in model_versions table
        ↓
Update agent reputation multipliers
```

### Agent Reputation System
```
Track: successful_tasks / total_tasks = success_rate

Multiplier Assignment:
- success_rate >= 95% → multiplier = 2.0x (maximum)
- success_rate >= 85% → multiplier = 1.8x
- success_rate >= 70% → multiplier = 1.5x
- success_rate < 70%  → multiplier = 1.2x (minimum)

Higher multiplier = Higher earnings per task
```

---

## 📊 MONITORING & METRICS

### Admin Dashboard Shows
- Total tasks created
- Total users registered
- Total agents active
- Average system success rate
- Total satoshis transacted
- Training samples collected
- Latest model version & accuracy
- Agent leaderboard
- Model training history
- System health

### How to Access
1. Login as admin user
2. Navigate to /dashboard
3. Click "Model Training" tab
4. View all metrics in real-time

---

## 🆘 COMMON ISSUES & FIXES

### Issue: Backend won't start
```bash
# Fix: Check if port 8000 is busy
lsof -i :8000
kill -9 <PID>

# Fix: Check database connection
psql postgresql://dukenete_user:password@localhost/dukenete

# Fix: Install missing dependencies
pip install -r requirements.txt
```

### Issue: Frontend can't connect to backend
```bash
# Fix: Verify backend is running
curl http://localhost:8000/api/v2/health

# Fix: Check VITE_API_URL in .env.local
# Should be: http://localhost:8000

# Fix: Clear browser cache
# DevTools → Application → Storage → Clear Site Data
```

### Issue: Database errors
```bash
# Fix: Reset database completely
dropdb dukenete
createdb dukenete

# Restart backend - it will recreate schema
python main.py
```

### Issue: Model training not triggering
```bash
# Check if training data exists
psql dukenete
SELECT COUNT(*) FROM training_data;

# Manually trigger training
curl -X POST http://localhost:8000/api/v2/model/train \
  -H "Authorization: Bearer <admin_token>"
```

---

## 🔐 SECURITY CHECKLIST

Before production deployment:
- [ ] Change SECRET_KEY to a strong random string
- [ ] Change DATABASE_URL password
- [ ] Change POSTGRES_PASSWORD in docker-compose.yml
- [ ] Set CORS origins to your domain only
- [ ] Enable HTTPS/SSL certificates
- [ ] Set up environment variables securely
- [ ] Implement rate limiting
- [ ] Add request logging & monitoring
- [ ] Regular database backups
- [ ] Monitor for suspicious activity

---

## 📈 SCALING CHECKLIST

As you grow from prototype to production:

### Database
- [ ] Add connection pooling (pgBouncer)
- [ ] Set up read replicas
- [ ] Archive old data to S3
- [ ] Implement proper indexing
- [ ] Monitor query performance

### Backend
- [ ] Use Gunicorn + Nginx
- [ ] Add Redis for caching
- [ ] Implement async task queue (Celery)
- [ ] Add request logging
- [ ] Set up error tracking (Sentry)

### Frontend
- [ ] Build assets: npm run build
- [ ] Serve from CDN
- [ ] Add service workers
- [ ] Implement analytics
- [ ] Monitor performance

### ML
- [ ] Train on GPU cluster
- [ ] Use model quantization
- [ ] Distributed training
- [ ] A/B test models
- [ ] Monitor drift

---

## 📞 SUPPORT RESOURCES

### API Documentation
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/api/v2/health

### Logs
- Backend: dukenete_backend.log
- Frontend: Browser console (F12)
- Database: PostgreSQL logs

### External Docs
- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/
- PostgreSQL: https://www.postgresql.org/docs/
- Docker: https://docs.docker.com/

---

## ✅ VERIFICATION CHECKLIST

After setup, verify:

- [ ] Backend running on http://localhost:8000
- [ ] API docs accessible at http://localhost:8000/docs
- [ ] Frontend running on http://localhost:3001
- [ ] Can register new user
- [ ] Can login with credentials
- [ ] Buyer can create task
- [ ] Agent can see tasks
- [ ] Can upload files
- [ ] Can submit results
- [ ] Can view metrics (admin)
- [ ] Model training can be triggered
- [ ] Database has data (psql check)

---

## 🎓 LEARNING PATH

1. **Understanding** (30 min)
   - Read this file
   - Review PRODUCTION_DEPLOYMENT_GUIDE.md
   - Check API endpoints

2. **Setup** (30 min)
   - Follow Quick Start above
   - Verify all services running
   - Test with demo credentials

3. **Development** (1-2 hours)
   - Create sample tasks
   - Submit results
   - Monitor in admin dashboard
   - Watch model improve

4. **Customization** (varies)
   - Modify UI components
   - Adjust satoshi pricing
   - Integrate your own Duke model
   - Add custom features

5. **Deployment** (1-2 hours)
   - Follow security checklist
   - Deploy to production server
   - Set up monitoring
   - Configure backups

---

## 🚀 YOU'RE READY!

You now have a complete, production-ready system with:
✅ Full backend with authentication
✅ Professional React frontend
✅ PostgreSQL database
✅ ML training pipeline
✅ Duke Labelee model integration
✅ Bitcoin satoshi pricing
✅ Admin monitoring & controls
✅ Comprehensive documentation

**Start the Quick Start above and launch your marketplace! 🎉**

---

**Questions? Issues?**
- Check logs in dukenete_backend.log
- Review API docs at /docs
- Test endpoints with curl or Postman
- Consult PRODUCTION_DEPLOYMENT_GUIDE.md for detailed help

**Good luck! 🚀**
