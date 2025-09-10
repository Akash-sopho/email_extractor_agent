Email Elchemy — FastAPI Scaffold

This repository contains the initial scaffold for the Email Elchemy project per PROJECT_OVERVIEW.md.

- Python 3.11 + FastAPI
- SQLAlchemy + Alembic
- Redis + RQ workers
- Tooling: ruff, black, pytest

Getting started

1. Create a virtual environment and install dependencies:
   - python -m venv .venv
   - .venv/Scripts/activate  (Windows) or source .venv/bin/activate (Unix)
   - pip install -e .
2. Copy `.env.example` to `.env` and fill values.
3. Run the app:
   - uvicorn app.main:app --reload

See PROJECT_OVERVIEW.md for full specification and next tasks.

Dev tools

- Dev ingest (no Gmail/Redis):
  - Ensure DB schema exists: `alembic upgrade head`
  - Run: `python scripts/dev_ingest.py`
  - Seeds a fake email, monkeypatches the LLM call with a deterministic response, and executes the extraction pipeline. Prints the result.

- Postman collection:
  - Import `postman/Email_Elchemy.postman_collection.json`
  - Update collection variables `baseUrl` and `apiKey` to match your environment.

Local EML ingest

- Ingest `.eml` files from `sample/` (no Gmail):
  - Ensure DB schema exists: `alembic upgrade head`
  - Option 1 — Script: `python scripts/local_ingest.py` (or specify dir/pattern)
  - Option 2 — API: `POST /ingest/local` with body `{ "directory": "sample", "pattern": "*.eml", "enqueue": true }`
    - Example: `curl -s -X POST http://localhost:8000/ingest/local -H "x-api-key: dev-local-key" -H "Content-Type: application/json" -d '{"directory":"sample","pattern":"*.eml"}'`
  - A worker should be running to process queued extraction: `python scripts/run_worker.py`
