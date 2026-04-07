.PHONY: setup run test lint migrate

# Setup
setup:
	python -m venv .venv
	.venv/bin/pip install -r requirements.txt

# Run
run:
	.venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Database
migrate:
	.venv/bin/alembic upgrade head

# Test
test:
	.venv/bin/pytest tests/ -v

# MLflow UI
mlflow:
	.venv/bin/mlflow ui --port 5000

# Docker
up:
	docker compose up -d

down:
	docker compose down
