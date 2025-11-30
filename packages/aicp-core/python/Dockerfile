FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ONLY the Python files we need
COPY coordinator_service.py .
COPY security.py .
COPY validators.py .

CMD ["uvicorn", "coordinator_service:app", "--host", "0.0.0.0", "--port", "8000"]
