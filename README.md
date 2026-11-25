# Smart Token-Based Queue & Booking Management System

A real, database-backed queue management system for physical service centers:
a customer takes a token at a kiosk, staff call and serve tokens from
counters, and a public TV display reflects the queue live. Three interfaces,
one backend, one source of truth.

- **Kiosk** (`/kiosk`) — touchscreen registration and token issuance
- **Staff Dashboard** (`/staff`) — login, overview, queue table, counter controls
- **Public Display** (`/display`) — full-screen "now serving" board, no PII

See [`docs/PLAN.md`](docs/PLAN.md) *(or ask the assistant)* for the full
architecture write-up. This file covers how to run it.

## Stack

FastAPI (async SQLAlchemy 2.0, Alembic) + PostgreSQL 16 + React/TypeScript/Vite
+ Tailwind, with a standalone mock prediction microservice as the seam for a
future TimesFM integration. Everything is wired through Docker Compose.

## Quick start (Docker Compose)

```bash
cp .env.example .env   # edit JWT_SECRET, SEED_ADMIN_PASSWORD, etc.
docker compose up -d --build
```

This builds and starts four containers: `db` (Postgres), `backend` (runs
Alembic migrations + seed on startup, then FastAPI on :8000), `prediction`
(mock wait-time service on :8001), and `frontend` (Vite dev server).

- Kiosk: http://localhost:5174/kiosk
- Staff Dashboard: http://localhost:5174/staff (seeded admin: `admin` /
  password from `SEED_ADMIN_PASSWORD`, default `admin123`; also a
  non-admin `staff1` / `staff123`)
- Public Display: http://localhost:5174/display
- Backend API docs: http://localhost:8000/docs

**Why port 5174, not 5173:** the frontend container listens on 5173
internally, but is mapped to the host at **5174** because 5173 is the Vite
default and is very often already taken by another local project. If you
free up 5173 you can change the mapping back in `docker-compose.yml`.

## Running without Docker

Backend:

```bash
cd backend
uv venv && uv pip install -e . --group dev
# Postgres must be reachable at DATABASE_URL (see .env.example)
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000
```

Prediction service:

```bash
cd prediction-service
uv venv && uv pip install -e .
uv run uvicorn app.main:app --reload --port 8001
```

Frontend:

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 by default
```

## Tests

The concurrency guarantees (`FOR UPDATE SKIP LOCKED` on Call Next, the atomic
token-sequence upsert) are Postgres-specific, so tests run against a real
Postgres database, not SQLite.

```bash
# one-time: createdb queue_test on the same Postgres instance
cd backend
DATABASE_URL="postgresql+asyncpg://queue:queue@localhost:5432/queue_test" uv run pytest -q
```

22 tests cover: registration persistence, daily token-number sequencing,
the full waiting→called→serving→completed lifecycle and its event trail,
recall/skip/absent/requeue, role-based access (masked vs. unmasked phone
numbers), the public display's zero-PII guarantee, SMS enqueue/retry/failure
handling, prediction-service-down resilience, and -- the one that matters
most -- two counters racing `call-next` against a single waiting token,
which must never both win it.

## Architecture notes

- **Single source of truth.** No interface keeps its own queue state. Every
  client loads a REST snapshot, then applies WebSocket events
  (`app/services/realtime.py` / `useQueueSocket.ts`); on reconnect it
  re-fetches rather than trusting a gap-filled event stream.
- **The WebSocket broadcaster is in-process** (`InMemoryBroadcaster`). Correct
  with the single uvicorn worker this project pins to in
  `docker-compose.yml`; scaling to multiple backend workers/replicas would
  need the `Broadcaster` protocol backed by Redis pub/sub instead -- the
  seam is already there.
- **Call Next concurrency.** `app/services/queue.py::call_next` locks the
  oldest eligible waiting token with `SELECT ... FOR UPDATE SKIP LOCKED`, so
  a second counter pressing the button at the same instant steps over a row
  already claimed rather than blocking or double-assigning it. See
  `tests/test_concurrency.py`.
- **Token numbering.** `app/services/tokens.py::_allocate_token_number` is a
  single `INSERT ... ON CONFLICT DO UPDATE ... RETURNING` against
  `token_sequences`, keyed by `(service_date, prefix)` -- no read-then-write
  race window.
- **PII handling.** Phone numbers are masked in every staff list response
  (`******1234`), unmasked only via the admin-only token detail endpoint, and
  never appear in the public display or WebSocket payloads.
- **SMS is asynchronous and provider-agnostic.** Registration/Call-Next write
  a `pending` row and return immediately; a background worker
  (`app/services/sms/worker.py`) sends with retry/backoff. Swap providers via
  `SMS_PROVIDER=console|twilio`.
- **TimesFM readiness.** `prediction-service/` is a standalone FastAPI app
  with no database of its own; the backend calls it with a timeout and never
  fails a registration if it's unreachable
  (`app/services/prediction.py`). Phase 1-3 return a transparent heuristic
  (`model_version="mock-heuristic-v1"`); swapping in TimesFM means replacing
  that one function's body. `wait_predictions` and the
  `/api/analytics/timeseries` export are the historical dataset a real model
  would train/predict from.

## Current phase

Phases 1-3 are implemented end-to-end: registration, queue management, the
public display, SMS notifications (console driver active; Twilio driver
written and ready for credentials), and the analytics/timeseries endpoints.
Phase 4 (actual TimesFM inference + the proactive "your turn is coming up"
notification scheduler) is intentionally not implemented yet -- the mock
prediction service, `wait_predictions` table, and `estimated_wait_time` field
are the prepared seam for it.
