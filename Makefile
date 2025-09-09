PY = python
PIP = pip

.PHONY: setup db-up run worker ingest test fmt

setup:
	$(PY) -m venv .venv && \
	. .venv/bin/activate 2>/dev/null || .venv\\Scripts\\activate && \
	$(PIP) install -e .[dev]

db-up:
	alembic upgrade head

run:
	uvicorn app.main:app --reload --port $${PORT-8000}

worker:
	$(PY) scripts/run_worker.py

ingest:
	curl -s -X POST http://localhost:$${PORT-8000}/ingest/run -H "x-api-key: $${API_KEY-dev-local-key}" -H "Content-Type: application/json" -d '{}'

test:
	pytest -q

fmt:
	ruff check --fix . && black .

