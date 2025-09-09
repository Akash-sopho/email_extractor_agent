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

