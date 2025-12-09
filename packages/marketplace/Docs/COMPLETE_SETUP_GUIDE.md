# DukeNET Frontend - React Component & Setup
# Save this as components and setup your React project accordingly

# ============================================================================
# 1. REQUIREMENTS.TXT (Backend Dependencies)
# ============================================================================

# Core dependencies
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
python-jose==3.3.0
passlib==1.7.4
python-dotenv==1.0.0
aiofiles==23.2.1
PyJWT==2.8.1

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.23

# ML/Data Science
torch==2.1.1
numpy==1.24.3
scikit-learn==1.3.2
opencv-python==4.8.1.78
pillow==10.1.0
transformers==4.35.1
timm==0.9.8

# Email & Auth
python-multipart==0.0.6
email-validator==2.1.0

# Optional but recommended
fastapi-cors==0.0.6
gunicorn==21.2.0
redis==5.0.1

# ============================================================================
# 2. PACKAGE.JSON (Frontend Dependencies)
# ============================================================================

{
  "name": "dukenete-frontend",
  "version": "2.0.0",
  "private": true,
  "description": "DukeNET Marketplace Frontend - Bitcoin AI Agent Marketplace",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.17.0",
    "axios": "^1.6.2",
    "zustand": "^4.4.6",
    "tailwindcss": "^3.3.6",
    "recharts": "^2.10.3",
    "react-icons": "^4.12.0",
    "react-dropzone": "^14.2.3",
    "react-hook-form": "^7.48.0",
    "framer-motion": "^10.16.4",
    "date-fns": "^2.30.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "vite": "^5.0.7",
    "@vitejs/plugin-react": "^4.2.0"
  },
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "start": "vite"
  }
}

# ============================================================================
# 3. .ENV.EXAMPLE (Environment Variables)
# ============================================================================

# Backend
VITE_API_URL=http://localhost:8000
VITE_API_TIMEOUT=30000

# Features
VITE_ENABLE_TRAINING_DASHBOARD=true
VITE_ENABLE_FILE_UPLOAD=true
VITE_ENABLE_RESULTS=true

# UI
VITE_THEME=dark
VITE_LOGO_URL=/logo.svg

# ============================================================================
# 4. DOCKER-COMPOSE.YML (Full Stack Setup)
# ============================================================================

version: '3.9'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: dukenete_postgres
    environment:
      POSTGRES_DB: dukenete
      POSTGRES_USER: dukenete_user
      POSTGRES_PASSWORD: secure_password_change_this
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dukenete_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: dukenete_backend
    environment:
      DATABASE_URL: postgresql://dukenete_user:secure_password_change_this@postgres:5432/dukenete
      SECRET_KEY: change-me-in-production
      ENVIRONMENT: development
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./uploads:/app/uploads
      - ./models:/app/models
    depends_on:
      postgres:
        condition: service_healthy
    command: python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  # React Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: dukenete_frontend
    ports:
      - "3001:3001"
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      VITE_API_URL: http://backend:8000
    depends_on:
      - backend
    command: npm run dev

  # Redis (Optional - for caching)
  redis:
    image: redis:7-alpine
    container_name: dukenete_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:

# ============================================================================
# 5. DOCKER FILES
# ============================================================================

# Backend Dockerfile (save as backend/Dockerfile)

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v2/health')"

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Frontend Dockerfile (save as frontend/Dockerfile)
# ============================================================================

FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source
COPY . .

# Expose port
EXPOSE 3001

# Vite server on all interfaces
ENV VITE_HOST=0.0.0.0

# Run dev server
CMD ["npm", "run", "dev"]

# ============================================================================
# 6. SETUP INSTRUCTIONS
# ============================================================================

# Quick Start Guide:

# 1. Clone repository and setup project structure:
#    ```
#    mkdir dukenete && cd dukenete
#    mkdir backend frontend
#    ```

# 2. Backend Setup:
#    ```
#    cd backend
#    cp ../dukenete_backend_complete.py main.py
#    pip install -r requirements.txt
#    cp ../.env.example .env
#    # Edit .env with your settings
#    python main.py
#    # Backend runs on http://localhost:8000
#    ```

# 3. Frontend Setup:
#    ```
#    cd frontend
#    npm install
#    cp ../.env.example .env.local
#    npm run dev
#    # Frontend runs on http://localhost:3001
#    ```

# 4. Database Setup:
#    ```
#    # Using Docker (recommended):
#    docker-compose up -d
#    
#    # Or manually with PostgreSQL:
#    psql -U postgres
#    CREATE DATABASE dukenete;
#    CREATE USER dukenete_user WITH PASSWORD 'secure_password';
#    ALTER ROLE dukenete_user SET client_encoding TO 'utf8';
#    ALTER ROLE dukenete_user SET default_transaction_isolation TO 'read committed';
#    ALTER ROLE dukenete_user SET default_transaction_deferrable TO on;
#    ALTER ROLE dukenete_user SET timezone TO 'UTC';
#    GRANT ALL PRIVILEGES ON DATABASE dukenete TO dukenete_user;
#    ```

# 5. Test the system:
#    ```
#    # Backend health check:
#    curl http://localhost:8000/api/v2/health
#    
#    # Frontend:
#    Open http://localhost:3001 in browser
#    ```

# ============================================================================
# 7. API DOCUMENTATION
# ============================================================================

# Full API docs available at:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)

# Key Endpoints:

# Authentication
# POST   /api/v2/auth/register          - Register new user
# POST   /api/v2/auth/login             - Login user
# GET    /api/v2/auth/profile           - Get user profile

# Files
# POST   /api/v2/files/upload           - Upload file
# GET    /api/v2/files/list             - List user files
# GET    /api/v2/files/{file_id}        - Download file
# DELETE /api/v2/files/{file_id}        - Delete file

# Tasks
# POST   /api/v2/tasks/create           - Create task
# GET    /api/v2/tasks/list             - List tasks
# GET    /api/v2/tasks/{task_id}        - Get task details
# POST   /api/v2/results/submit         - Submit task result
# GET    /api/v2/results/{task_id}      - Get task results

# Model Training
# POST   /api/v2/model/train            - Start training
# GET    /api/v2/model/status           - Get model status
# GET    /api/v2/model/metrics          - Get model metrics

# Admin
# GET    /api/v2/admin/metrics          - Get system metrics
# GET    /api/v2/admin/agents           - List agents

# ============================================================================
# 8. PRODUCTION DEPLOYMENT
# ============================================================================

# For production, use:

# Backend (with Gunicorn):
# gunicorn -w 4 -b 0.0.0.0:8000 main:app

# Frontend (build first):
# npm run build
# # Serve dist/ folder with nginx

# Environment variables to change:
# - SECRET_KEY (generate strong random key)
# - DATABASE_URL (use production database)
# - CORS origins (whitelist production domains)
# - ALLOWED_FILE_TYPES (restrict if needed)
# - MAX_FILE_SIZE (adjust as needed)

# ============================================================================
# 9. ML MODEL INTEGRATION GUIDE
# ============================================================================

# Your Duke Labelee model is integrated in the backend training pipeline.
# The model learns from:

# 1. All task descriptions (input_data)
# 2. All results submitted (output_data)
# 3. Success/failure outcomes (success flag)
# 4. Agent performance (confidence_score, execution_time)

# Training is triggered automatically when:
# - 100+ new results collected (Config.TRAINING_TRIGGER_SAMPLES)
# - OR every 24 hours (Config.TRAINING_TRIGGER_HOURS)

# To integrate your custom Duke model:
# 1. Save model weights to models/ directory
# 2. Create wrapper class in backend:
#    ```python
#    from new_labelee_model import EnhancedLabeleeFoundation
#    
#    class DukeMMAgent:
#        def __init__(self):
#            self.model = EnhancedLabeleeFoundation.load('models/duke-mm-v1.pt')
#        
#        def process_task(self, task_input):
#            # Preprocess
#            # Run inference
#            # Return prediction + confidence
#            pass
#    ```
# 3. Use in MarketplaceService.select_best_agent()
# 4. Model predictions improve over time as it learns from results

# ============================================================================

print("✅ DukeNET v2.0 - Full Production System Setup Complete!")
print("")
print("📦 Backend: http://localhost:8000")
print("🎨 Frontend: http://localhost:3001")
print("📊 API Docs: http://localhost:8000/docs")
print("📁 Database: PostgreSQL on :5432")
print("")
print("🚀 Ready to launch your AI Agent Marketplace!")
