# Task Manager — WPP Media Indonesia (Study Case)

A full-stack Mini Task Management Application built as part of the **Executive Fullstack Developer** study case at WPP Media Indonesia.

## Architecture Overview

```
task-manager/
├── docker-compose.yml      ← PostgreSQL 15 (port 5432)
├── backend/                ← Python 3.11 + FastAPI
│   ├── app/
│   │   ├── main.py         ← FastAPI app, CORS, startup
│   │   ├── database.py     ← SQLAlchemy engine + session
│   │   ├── models.py       ← ORM models (Board, Task)
│   │   ├── schemas.py      ← Pydantic v2 request/response
│   │   ├── services.py     ← Business logic (testable, no HTTP)
│   │   └── routers/
│   │       ├── boards.py   ← Board HTTP controllers
│   │       └── tasks.py    ← Task HTTP controllers
│   └── tests/
│       ├── conftest.py     ← SQLite in-memory test fixture
│       └── test_services.py
└── frontend/               ← React 18 + Vite + TypeScript
    └── src/
        ├── App.tsx          ← Root state + orchestration
        ├── api.ts           ← HTTP client (typed)
        ├── types.ts         ← Shared TypeScript types
        └── components/
            ├── BoardSidebar.tsx
            ├── TaskBoard.tsx
            ├── TaskCard.tsx
            └── TaskCreateForm.tsx
```

Two separate services communicating **exclusively over HTTP REST API**. No shared code, no direct database access from the frontend.

---

## Quick Start

### Prerequisites

| Tool | Version |
|------|---------|
| Docker + Docker Compose | v20+ |
| Python | 3.11+ |
| Node.js | 20+ |

---

### Method 1: The Docker Way (Recommended)
*Starts the Database, Backend, and Frontend all together.*

```bash
docker compose up -d --build
```
- **App**: [http://localhost:3000](http://localhost:3000)
- **API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

*(Note: The database is exposed on `localhost:15432` to avoid common Windows Hyper-V port conflicts).*

---

### Method 2: Local Run (Step-by-Step)
*If you prefer to run the services directly on your host machine.*

**1. Start the database only**
```bash
docker compose up -d db
```

**2. Start the backend**
```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**3. Start the frontend**
```bash
cd frontend
npm install
npm run dev
```
Open: [http://localhost:3000](http://localhost:3000)

### Step 4 — Run the unit tests

```bash
cd backend
pytest
```

Expected: **all tests pass** (no Docker required for tests — uses SQLite in-memory).

---

## Optional Extras Implemented

All three optional extras requested in the study case have been fully implemented:

1. **Inline task editing**: Tasks can be edited directly on the board by clicking the ✏️ icon. Updates title and description seamlessly using the extended `PATCH /api/tasks/{taskId}` endpoint.
2. **Status counters**: Above the task list, a set of badges displays the current count of tasks in each status (TODO, IN_PROGRESS, DONE) for the active board, powered by the new `GET /api/boards/{boardId}/tasks/counts` endpoint.
3. **Bulk CSV import**: A button above the task list allows you to upload a CSV file (`title,description,status`) to bulk-create tasks on the active board via `POST /api/boards/{boardId}/tasks/import`.

---

## Design Decisions & Trade-offs

### Database — `ON DELETE CASCADE` (R4)

Tasks are deleted automatically at the **PostgreSQL engine level** when their parent board is deleted (`ForeignKey("boards.id", ondelete="CASCADE")`). This was chosen over:
- **Application-level loop**: Fragile, non-atomic, race-condition prone.
- **RESTRICT / manual guard**: Requires extra API surface (check-before-delete), complicates the client.

**Trade-off**: If a future requirement needs "soft delete" or audit logging of task deletions, we'd need to intercept at the service layer before the cascade fires.

### Testing — SQLite in-memory

Unit tests use SQLite (`:memory:`) rather than requiring a running PostgreSQL container. This means:
- `pytest` runs instantly, zero external dependencies.
- **Caveat**: SQLite and PostgreSQL have minor dialect differences. Any PostgreSQL-specific SQL (e.g., `NOW()`) is not exercised in tests. The service layer avoids raw SQL for this reason — all queries go through SQLAlchemy ORM.

### Status Enum — String over PostgreSQL ENUM type

Task status is stored as `VARCHAR(20)` with Pydantic/service-layer enforcement rather than a PostgreSQL native `ENUM`. Rationale: adding/removing statuses in the future requires only a code change, not a DDL migration.

### No Authentication

Out of scope per Section 10 of the study case brief.
