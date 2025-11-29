#!/bin/bash
set -e

echo "🔧 Initializing AINS database..."
python << 'PYTHON'
from ains.db import create_tables, engine, Base
print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("✅ Database initialized")
PYTHON

echo "🚀 Starting AINS API..."
python -m uvicorn ains.api:app --host 0.0.0.0 --port 8000
