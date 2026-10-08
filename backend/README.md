# Backend — FastAPI + PostgreSQL

Python 3.11 REST API service implementing all task management business logic.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.11+ |
| pip | latest |
| Docker | 20+ (for PostgreSQL) |

---

## Setup & Run

```bash
# 1. Start PostgreSQL (from the project root)
docker compose up -d

# 2. Enter the backend directory
cd backend

# 3. Copy the environment file
cp .env.example .env

# 4. Install Python dependencies
pip install -r requirements.txt

# 5. Start the development server
uvicorn app.main:app --reload --port 8000
```

The server auto-creates all database tables on first startup (no manual migration needed).

- **API base**: `http://localhost:8000`
- **Interactive docs**: `http://localhost:8000/docs`
- **Health check**: `http://localhost:8000/health`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:password123@localhost:5432/taskmanager` | SQLAlchemy connection string |

---

## Database Schema

### `boards`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `INTEGER` | Primary Key, auto-increment |
| `name` | `VARCHAR(255)` | NOT NULL |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, server default `NOW()` |

### `tasks`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | `INTEGER` | Primary Key, auto-increment |
| `board_id` | `INTEGER` | NOT NULL, FK → `boards.id` `ON DELETE CASCADE` |
| `title` | `VARCHAR(500)` | NOT NULL |
| `description` | `TEXT` | Nullable |
| `status` | `VARCHAR(20)` | NOT NULL, default `'TODO'` |
| `created_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, server default `NOW()` |
| `updated_at` | `TIMESTAMP WITH TIME ZONE` | NOT NULL, server default `NOW()`, updated on PATCH |

### Indexes

| Index name | Columns | Type | Rationale |
|------------|---------|------|-----------|
| `ix_tasks_board_id` | `tasks(board_id)` | B-tree | High-frequency lookup: every board view fetches tasks by board_id. Without this index, PostgreSQL performs a sequential scan across the entire tasks table. |
| `ix_tasks_status` | `tasks(status)` | B-tree | Supports `GET /api/boards/{id}/tasks?status=` filter queries. Eliminates sequential scans when filtering by a single status value. |

### Why `ON DELETE CASCADE`?

When a board is deleted, all associated tasks must be removed. Enforcing this at the **database engine level** (rather than in application code) guarantees:
1. **Atomicity** — board and tasks are deleted in a single transaction.
2. **Integrity** — no orphan task rows can exist, even if the application crashes mid-operation.
3. **Simplicity** — the service layer calls `db.delete(board)` and commits; no looping or secondary DELETE queries.

**Alternative considered**: `ON DELETE RESTRICT` — would require the API to return a 409 Conflict if the board has tasks, forcing the client to delete tasks individually first. This was rejected as it creates unnecessary friction for the end-user workflow.

---

## Running Tests

```bash
cd backend
pytest
```

Tests use **SQLite in-memory** — no Docker or running PostgreSQL required.

```bash
# Verbose output
pytest -v

# With coverage report
pytest --tb=short
```

### What is tested

| Category | Cases |
|----------|-------|
| Happy paths | Create board, create task, list tasks, filter by status, cascade delete |
| Empty/whitespace validation | Empty title `""`, whitespace title `"   "`, tab title |
| Empty board name | Empty `""` and whitespace-only name |
| Non-existent entities | Create task on non-existent boardId, update/delete non-existent taskId, delete non-existent boardId |
| Invalid status values | `"COMPLETED"`, `"PENDING"` — both must raise `ValidationError` |
| Invalid filter | `?status=INVALID` raises `ValueError` at service layer |

---

## API Contract

### Error Envelope (all non-2xx responses)

```json
{
  "error": "BOARD_NOT_FOUND",
  "message": "Board with id=42 not found",
  "field": null
}
```

### Endpoints

#### `GET /api/boards`
Returns all boards.
```json
[{ "id": 1, "name": "Sprint 1", "created_at": "2024-01-15T08:00:00Z" }]
```

#### `POST /api/boards`
```json
// Request
{ "name": "My Board" }

// 201 Response
{ "id": 2, "name": "My Board", "created_at": "2024-01-15T08:01:00Z" }

// 422 — empty/whitespace name
{ "error": "VALIDATION_ERROR", "message": "Board name must not be blank or whitespace only", "field": "name" }
```

#### `GET /api/boards/{boardId}/tasks?status=TODO`
```json
// 200
[{ "id": 1, "board_id": 1, "title": "Write tests", "description": null, "status": "TODO", "created_at": "...", "updated_at": "..." }]

// 404
{ "error": "BOARD_NOT_FOUND", "message": "Board with id=99 not found" }
```

#### `GET /api/boards/{boardId}/tasks/counts` (Optional Extra)
Returns the count of tasks grouped by status for a specific board.
```json
{ "TODO": 2, "IN_PROGRESS": 1, "DONE": 0 }
```

#### `POST /api/boards/{boardId}/tasks/import` (Optional Extra)
Bulk imports tasks from a `.csv` file upload.
```
Content-Type: multipart/form-data
file: <tasks.csv>
```

#### `POST /api/boards/{boardId}/tasks`
```json
// Request
{ "title": "Implement feature", "description": "Optional detail", "status": "TODO" }

// 201
{ "id": 5, "board_id": 1, "title": "Implement feature", "description": "Optional detail", "status": "TODO", "created_at": "...", "updated_at": "..." }
```

#### `PATCH /api/tasks/{taskId}`
```json
// Request (all fields optional)
{ "title": "Updated title", "description": "New description", "status": "IN_PROGRESS" }

// 200
{ "id": 5, ..., "status": "IN_PROGRESS", "updated_at": "..." }

// 422 — invalid status
{ "error": "VALIDATION_ERROR", "message": "Input should be 'TODO', 'IN_PROGRESS' or 'DONE'", "field": "status" }
```

#### `DELETE /api/tasks/{taskId}`
```
204 No Content  (success)
404             (task not found)
```

#### `DELETE /api/boards/{boardId}`
```
204 No Content  (success, all tasks cascade-deleted)
404             (board not found)
```
