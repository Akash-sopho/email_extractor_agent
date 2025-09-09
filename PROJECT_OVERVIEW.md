# Email Elchemy — Project Overview (for Code Generation)

## 0) One-liner

Ingest Gmail threads, detect and extract all quote versions from vendor emails, normalize the data, and persist structured records to Postgres. Expose clean APIs for downstream usage. Focus only on accurate extraction + storage (no review UI, monitoring, or backfill—for now).

---

## 1) Goals & Non-Goals

**Goals**

* Connect to Gmail (user’s Google account) and pull relevant threads by labels/queries.
* For each thread, segment messages, detect “quote” emails, extract all versions (not just the latest), and normalize fields (vendor, items, quantities, unit price, currency, totals, dates, terms, validity, attachments).
* Deduplicate and version quotes; persist to Postgres with a tidy schema and lineage to source email/message.
* Provide idempotent, resumable workers so re-processing a thread is safe.
* Offer a small set of stable APIs to read extracted data.

**Non-Goals (Phase-1)**

* Human review dashboard, monitoring, analytics, retry/backfill services.
* Complex role-based auth or multi-tenant UI.
* Non-Gmail providers.

---

## 2) Key Constraints & Assumptions

* **Runtime:** Local dev on VS Code; Postgres running locally.
* **Gmail:** Use Gmail API (OAuth user consent), read-only scopes; store `historyId`/`messageId` for incremental sync.
* **LLM:** Use OpenAI API (Pro subscription) for robust parsing/normalization. Keep prompt templates versioned.
* **Privacy:** Store only what’s needed; keep raw bodies hashed; store minimal plaintext where needed for re-runs.
* **Throughput:** Single-user, single-inbox to start; safe to scale to a few thousand messages with a worker queue.

---

## 3) Tech Stack

* **Backend:** Python 3.11 + FastAPI
* **Workers/Queue:** RQ (Redis Queue) or Celery (choose RQ for lighter setup) + Redis
* **DB:** Postgres (SQLAlchemy + Alembic)
* **Auth:** Simple API key (header) for local APIs
* **Gmail SDK:** `google-api-python-client` + `google-auth-oauthlib`
* **HTTP:** `httpx` (async) or `requests` (sync)
* **LLM:** OpenAI `Responses` or `Chat Completions` API
* **Testing:** `pytest`
* **Tooling:** `ruff`, `black`, `pre-commit`, `mypy` (optional)

---

## 4) High-Level Architecture

```
[Gmail API] -> [Ingestion Service]
                  | fetch threads/messages (label/query)
                  v
            [RawStore] (emails, headers, parts, attachments)
                  |
                  | enqueue jobs per message/thread
                  v
             [Extractor Worker] --(LLM)--> parse quotes & versions
                  |
                  v
         [Normalizer + Deduper] --> [Postgres]
                  |
                  v
               [REST API]
```

---

## 5) Data Model (Postgres)

### Entities

* **emails**: a single Gmail message snapshot (normalized headers/meta)
* **email\_bodies**: raw/plaintext/HTML parts (optionally hashed)
* **attachments**: filename, mime, size, (optional local path)
* **quotes**: one quote “document” (can have many versions; belongs to thread/vendor)
* **quote\_versions**: structured extraction result per detected version in a message
* **quote\_items**: line items per version
* **vendors**: canonical vendor entity (name, email domain)
* **threads**: logical Gmail thread grouping

### Minimal Schema (DDL sketch)

```sql
create table threads (
  id bigserial primary key,
  gmail_thread_id text unique not null,
  last_history_id text,
  first_seen_at timestamptz default now(),
  last_synced_at timestamptz
);

create table emails (
  id bigserial primary key,
  thread_id bigint references threads(id),
  gmail_message_id text unique not null,
  from_addr text,
  to_addrs text[],
  cc_addrs text[],
  subject text,
  sent_at timestamptz,
  snippet text,
  raw_hash text,     -- sha256 of raw
  created_at timestamptz default now()
);

create table email_bodies (
  id bigserial primary key,
  email_id bigint references emails(id),
  mime_type text,
  charset text,
  body_text text,     -- may store sanitized/plaintext
  body_html text,
  body_hash text
);

create table attachments (
  id bigserial primary key,
  email_id bigint references emails(id),
  filename text,
  mime_type text,
  size_bytes int,
  local_path text
);

create table vendors (
  id bigserial primary key,
  name text,
  domain text
);

create table quotes (
  id bigserial primary key,
  thread_id bigint references threads(id),
  vendor_id bigint references vendors(id),
  anchor_email_id bigint references emails(id), -- first detected quote email
  status text, -- e.g. 'active','superseded','cancelled'
  created_at timestamptz default now()
);

create table quote_versions (
  id bigserial primary key,
  quote_id bigint references quotes(id),
  source_email_id bigint references emails(id),
  version_label text,        -- e.g., "v1", "revised", email date tag
  currency text,
  subtotal numeric,
  tax numeric,
  shipping numeric,
  total numeric,
  valid_till date,
  terms text,
  extracted_json jsonb,      -- full LLM parse for traceability
  created_at timestamptz default now(),
  unique(quote_id, source_email_id)
);

create table quote_items (
  id bigserial primary key,
  quote_version_id bigint references quote_versions(id),
  sku text,
  description text,
  quantity numeric,
  unit_price numeric,
  discount numeric,
  line_total numeric
);
```

---

## 6) Core Workflows

### 6.1 Incremental Gmail Sync

1. `POST /ingest/run` → starts a sync job (optionally takes `label`, `query`, `after`, `before`).
2. Ingestion lists threads/messages using Gmail API.
3. For each new/updated message:

   * Persist thread + email meta + bodies + attachments.
   * Enqueue `extract_quotes_for_email(message_id)`.

### 6.2 Quote Extraction (Per Email)

1. Detect if email likely contains a quote (rule-based prefilter: keywords + attachment heuristics).
2. Build structured extraction prompt with:

   * Subject, header metadata
   * Plaintext body (sanitized)
   * Attachment text (optional: OCR/PDF parse — Phase-2)
3. Ask LLM to return a **strict JSON schema** (see §8) with:

   * `vendor`, `versions[]`, `items[]`, monetary fields, currency, terms, validity.
4. Validate JSON → Normalize currencies, totals; compute `line_total`.
5. Link/Upsert `vendor`, `quote`, `quote_versions`, `quote_items` using (thread,vendor) heuristics.
6. Idempotency: use `(quote_id, source_email_id)` to avoid dup versions.

---

## 7) REST API (FastAPI)

### Auth

* Header `x-api-key: <key>` on all endpoints.

### Endpoints

* `POST /ingest/run` — body: `{ label?: string, query?: string, after?: string, before?: string }`
* `GET /threads` — list known threads (paginated)
* `GET /quotes` — filters: `vendor`, `date_from`, `date_to`, `has_latest_only`
* `GET /quotes/{id}` — returns quote + versions + items
* `GET /vendors` — simple vendor index
* `POST /reprocess/email/{email_id}` — re-run extraction
* `GET /health` — liveness

Provide OpenAPI via FastAPI decorators; Codex should autogenerate docs.

---

## 8) LLM Contract (Strict JSON)

**Model:** gpt-4.1-mini (or current equivalent); temperature 0.1.

**System prompt (summary):**

> You are an information extraction engine. Given a vendor quote email, output strictly valid JSON adhering to the provided JSON Schema. Never include prose.

**JSON Schema (TypeBox-style, for reference)**

```json
{
  "type":"object",
  "required":["vendor","versions"],
  "properties":{
    "vendor":{"type":"object","required":["name"],"properties":{"name":{"type":"string"},"domain":{"type":"string"}}},
    "versions":{
      "type":"array",
      "items":{
        "type":"object",
        "required":["version_label","currency","items","total"],
        "properties":{
          "version_label":{"type":"string"},
          "valid_till":{"type":["string","null"],"format":"date"},
          "currency":{"type":"string"},
          "subtotal":{"type":["number","null"]},
          "tax":{"type":["number","null"]},
          "shipping":{"type":["number","null"]},
          "total":{"type":"number"},
          "terms":{"type":["string","null"]},
          "items":{
            "type":"array",
            "items":{
              "type":"object",
              "required":["description","quantity","unit_price"],
              "properties":{
                "sku":{"type":["string","null"]},
                "description":{"type":"string"},
                "quantity":{"type":"number"},
                "unit_price":{"type":"number"},
                "discount":{"type":["number","null"]},
                "line_total":{"type":["number","null"]}
              }
            }
          }
        }
      }
    }
  }
}
```

**Post-parse validator:** recompute `line_total` and totals; allow small epsilon differences.

---

## 9) Directory Layout

```
email-elchemy/
  app/
    api/               # FastAPI routers
      __init__.py
      ingest.py
      quotes.py
      vendors.py
      health.py
    core/
      config.py        # env, settings
      logging.py
      security.py      # API key auth
    db/
      base.py          # SQLAlchemy base
      session.py
      models.py
      crud/            # repository functions
        quotes.py
        emails.py
        vendors.py
    gmail/
      client.py        # Gmail SDK wrapper
      ingest.py        # thread & message fetchers
      parsers.py       # MIME parts → text
    extract/
      prefilter.py     # is_quote heuristic
      prompts.py       # prompt templates
      llm.py           # OpenAI calls + schema validator
      normalize.py     # currency/number fixes
      pipeline.py      # email→quote orchestration
    workers/
      queue.py         # RQ setup
      jobs.py          # task defs
    schemas/
      dto.py           # Pydantic response/request models
    main.py            # FastAPI app factory
  migrations/
    versions/          # Alembic
  scripts/
    bootstrap_db.py
    run_worker.py
  tests/
    unit/
    integration/
  .env.example
  alembic.ini
  pyproject.toml
  README.md
  PROJECT_OVERVIEW.md
  Makefile
```

---

## 10) Environment & Secrets

`.env.example`

```
# Postgres
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/email_elchemy

# Redis
REDIS_URL=redis://localhost:6379/0

# Gmail OAuth (local)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_TOKEN_PATH=.tokens/gmail.json

# OpenAI
OPENAI_API_KEY=...

# API
API_KEY=dev-local-key
PORT=8000
```

---

## 11) Make Targets (Dev Quality-of-life)

```
make setup        # venv, pip install, pre-commit
make db-up        # start local postgres (optional via docker) + alembic upgrade
make run          # uvicorn app.main:app --reload
make worker       # python scripts/run_worker.py
make ingest       # curl -X POST localhost:8000/ingest/run
make test         # pytest -q
make fmt          # ruff check --fix && black .
```

---

## 12) Extraction Heuristics (Prefilter)

* **Subject contains:** “quote”, “quotation”, “proposal”, “estimate”, “pricing”, “proforma”, “invoice (if treated as quote)”.
* **Body contains:** currency symbols, tabular patterns (multiple lines with qty/price).
* **Attachments:** `.pdf`, `.xls[x]`, `.doc[x]` with pricing hints (Phase-2: parse).
* Confidence score → if above threshold, send to LLM; else skip.

---

## 13) Idempotency & Dedup

* Unique email keyed by `gmail_message_id`.
* Unique version keyed by `(quote_id, source_email_id)`.
* Upsert vendor by domain/name fuzzy match.
* Use DB transactions; workers retry on transient errors.

---

## 14) Testing Strategy

* **Unit:** prompt builder, JSON validators, normalizer math, CRUD upserts.
* **Integration:** mocked Gmail messages; fixture emails (HTML/text variants); golden JSON outputs.
* **E2E (local):** seed mailbox export (MBOX → mocked service) to simulate Gmail.

---

## 15) First-Week Deliverables (Sprint-1)

1. Project scaffold (FastAPI, SQLAlchemy, Alembic, RQ, Redis, Makefile, tooling).
2. DB models + migrations.
3. Gmail client (OAuth + minimal `threads.list`, `messages.get`).
4. Ingestion pipeline persisting emails/bodies/attachments.
5. LLM extraction contract (prompt + schema validator) with 3 synthetic test emails.
6. Quote persistence flow (quote, versions, items) with idempotency.
7. APIs: `/health`, `/ingest/run`, `/quotes`, `/quotes/{id}`.
8. Basic tests for 4–7.

---

## 16) “Codex, please generate…” (Starter Tasks)

Use these as **task cards/prompts** inside your codegen tool:

* **Task A — Scaffold**

  * Create a Python 3.11 FastAPI project with the directory layout in §9, tooling in §11, and configs in §10.

* **Task B — DB Layer**

  * Implement SQLAlchemy models & Alembic migrations for all tables in §5.

* **Task C — Gmail Ingestion**

  * Implement OAuth flow (local), list threads by label/query, fetch message bodies & attachments, persist per §6.1.

* **Task D — Extraction Pipeline**

  * Implement prefilter + LLM call using schema in §8, normalization in §6.2, and DB upserts. Ensure idempotency.

* **Task E — APIs**

  * Implement endpoints in §7 with Pydantic DTOs. Protect with API key header.

* **Task F — Worker**

  * Add RQ worker, `extract_quotes_for_email(email_id)` job, and a `POST /reprocess/email/{email_id}` endpoint.

* **Task G — Tests**

  * Add unit + integration tests described in §14 with fixtures for sample emails.

---

## 17) Example DTOs (Pydantic)

```python
class QuoteItem(BaseModel):
    sku: str | None = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount: Decimal | None = None
    line_total: Decimal | None = None

class QuoteVersion(BaseModel):
    id: int
    version_label: str
    currency: str
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    shipping: Decimal | None = None
    total: Decimal
    valid_till: date | None = None
    terms: str | None = None
    items: list[QuoteItem]

class QuoteResponse(BaseModel):
    id: int
    vendor: str | None = None
    thread_id: int
    versions: list[QuoteVersion]
```

---

## 18) Prompts (LLM)

**User prompt template (variables: `subject`, `from`, `to`, `date`, `body_text`):**

```
Extract ALL quote versions present in the following email.
Return STRICT JSON conforming to the provided schema.
If information is missing, use null rather than guessing.

Email:
Subject: {{subject}}
From: {{from}}
To: {{to}}
Date: {{date}}

Body (plaintext):
{{body_text}}
```

---

## 19) Future Phases (Not in scope now)

* Attachments parsing (PDF tables, XLSX)
* Review UI + diff view across versions
* Monitoring, retries, dead-letter queue
* Multi-tenant + OAuth user management
* Backfill (historyId) and webhooks (Gmail push)

---

**Acceptance Criteria (Sprint-1)**

* Running `make run` + `make worker` + `POST /ingest/run` on a label pulls emails, extracts quotes (from test set), and `GET /quotes` returns normalized data with at least 3 sample threads containing multi-version quotes.
