FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN grep -v -E "^(apache-airflow|pytest)" requirements.txt > /tmp/req.txt && \
    pip install --no-cache-dir -r /tmp/req.txt

# Copy application code
COPY src/ src/
COPY frontend/ frontend/
COPY alembic/ alembic/
COPY alembic.ini .

# Expose port
EXPOSE 8080

# Run with uvicorn
ENV PYTHONPATH=/app
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
