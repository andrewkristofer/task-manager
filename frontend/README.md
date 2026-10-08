# Frontend — React + Vite + TypeScript

Single-page application implementing the Task Manager UI, communicating with the FastAPI backend over HTTP REST.

---

## Prerequisites

| Requirement | Version |
|-------------|---------|
| Node.js | 20+ |
| npm | 9+ |

---

## Setup & Run

```bash
cd frontend

# Install dependencies
npm install

# Start development server (port 3000)
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

> **Note**: The backend must be running at `http://localhost:8000` before opening the frontend. If it is not reachable, the app displays a clear error screen with exact instructions — no blank pages.

---

## Environment Variables

Copy `.env.example` to `.env.local` to override the backend URL:

```bash
cp .env.example .env.local
```

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |

---

## Component Structure

```
src/
├── App.tsx                  Root component — all state, all API calls
├── api.ts                   Typed HTTP client (fetch wrapper)
├── types.ts                 Shared TypeScript types
└── components/
    ├── BoardSidebar.tsx     Board list, selection, create board form
    ├── TaskBoard.tsx        Task list, filter, counts, CSV import, empty states
    ├── TaskCard.tsx         Individual task — inline editing, status, delete
    └── TaskCreateForm.tsx   Collapsible new-task form
```

### State Management

All application state lives in `App.tsx` (no external store library). React hooks (`useState`, `useEffect`) are used exclusively. The component tree is:

```
App
├── BoardSidebar  (boards list + create form)
└── TaskBoard     (tasks for selected board)
    ├── TaskCard  (each task, repeated)
    └── TaskCreateForm
```

---

## Non-Happy-Path Handling

| Scenario | Behaviour |
|----------|-----------|
| Backend unreachable / network error | Full-page error card with exact backend URL, retry button |
| Boards loading | Spinner text: "Loading boards..." |
| Tasks loading | Spinner text: "Loading tasks..." |
| No boards exist | Sidebar: "No boards yet. Create one below." |
| No tasks on board | Board area: dashed box with contextual empty message |
| No tasks match filter | "No tasks with status 'DONE'." |
| API validation error (e.g., empty title) | Inline error below the relevant field (create or edit) |
| Task status/edit update fails | Error displayed inline on that specific TaskCard |
| CSV import fails | Error displayed directly next to the Import button |
| Board deletion confirms | window.confirm() dialog before sending DELETE |

---

## Building for Production

```bash
npm run build
```

Output: `frontend/dist/` — static files ready for any web server.
