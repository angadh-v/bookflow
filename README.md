# Library Management System

Corrected and implemented full-stack technical assessment project.

## What was corrected

- Fixed FastAPI route ordering so `/api/books/search` is not shadowed by `/{book_id}`.
- Replaced invalid client-side token retrieval pattern with a Next.js BFF proxy route.
- Stabilized AI response shape to always return schema-compatible `books`.
- Added pagination caps, uniqueness handling, and transactional checkout/checkin logic.
- Added backend tests for core CRUD/search/checkout flows.

## Repository Layout

- `backend/`: FastAPI + SQLAlchemy API
- `frontend/`: Next.js App Router UI + Auth0 routes + backend proxy
- `TECHNICAL_DESIGN.md`: corrected architecture/design document

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`.

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Frontend runs on `http://localhost:3000`.

## Backend Test Run

```bash
cd backend
pytest -q
```

## Move Local Data To Aiven

Use this one-time script to copy your local SQLite data (`backend/library.db`) into Aiven MySQL.

```bash
cd backend

# 1) Preview without writing
TARGET_DATABASE_URL="mysql+pymysql://USER:PASS@HOST:PORT/DB?ssl=true" \
  .venv/bin/python scripts/migrate_local_to_aiven.py --dry-run

# 2) Run for real
TARGET_DATABASE_URL="mysql+pymysql://USER:PASS@HOST:PORT/DB?ssl=true" \
  .venv/bin/python scripts/migrate_local_to_aiven.py
```

The script upserts:
- `users` by `auth0_id`
- `books` by `isbn` (fallback: `title + author`)

It keeps your local DB unchanged and can be re-run safely.

## Important Environment Variables

### Backend

- `DATABASE_URL`
- `CORS_ORIGINS`
- `AUTH_DISABLED` (set `true` locally if needed)
- `AUTH0_DOMAIN`
- `AUTH0_AUDIENCE`
- `AI_ENABLED`
- `OPENAI_API_KEY`

### Frontend

- `BACKEND_API_URL`
- `APP_BASE_URL`
- `AUTH0_SECRET`
- `AUTH0_DOMAIN`
- `AUTH0_CLIENT_ID`
- `AUTH0_CLIENT_SECRET`
- `AUTH0_AUDIENCE`
