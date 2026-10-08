/**
 * api.ts — All HTTP communication with the backend.
 *
 * The base URL is read from VITE_API_BASE_URL (defaults to http://localhost:8000).
 * All functions throw an Error on non-2xx responses, with the message taken from
 * the backend's unified error envelope when available.
 */

import type { Board, Task, TaskStatus, TaskCounts } from "./types";

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    // Covers: backend is down, CORS preflight failure, DNS failure, etc.
    throw new Error(
      `Cannot connect to backend service at ${BASE_URL}. ` +
        "Please verify the API is running."
    );
  }

  if (response.status === 204) {
    return undefined as unknown as T;
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    // Parse unified error envelope — backend now always returns root-level {error, message}
    const envelope = data as { error?: string; message?: string } | null;
    throw new Error(
      envelope?.message ?? `Request failed with status ${response.status}`
    );
  }

  return data as T;
}

// ---------------------------------------------------------------------------
// Board API
// ---------------------------------------------------------------------------

export function fetchBoards(): Promise<Board[]> {
  return request<Board[]>("/api/boards");
}

export function createBoard(name: string): Promise<Board> {
  return request<Board>("/api/boards", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function deleteBoard(boardId: number): Promise<void> {
  return request<void>(`/api/boards/${boardId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Task API
// ---------------------------------------------------------------------------

export function fetchTasks(
  boardId: number,
  statusFilter?: TaskStatus
): Promise<Task[]> {
  const qs = statusFilter ? `?status=${statusFilter}` : "";
  return request<Task[]>(`/api/boards/${boardId}/tasks${qs}`);
}

export function createTask(
  boardId: number,
  payload: { title: string; description?: string; status?: TaskStatus }
): Promise<Task> {
  return request<Task>(`/api/boards/${boardId}/tasks`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Update any combination of title, description, or status on a task.
 * Only provided (non-undefined) keys are sent; backend applies only those.
 * Replaces the previous updateTaskStatus helper — a strict superset.
 */
export function updateTask(
  taskId: number,
  payload: { title?: string; description?: string | null; status?: TaskStatus }
): Promise<Task> {
  return request<Task>(`/api/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteTask(taskId: number): Promise<void> {
  return request<void>(`/api/tasks/${taskId}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Status Counts API (optional extra)
// ---------------------------------------------------------------------------

export function fetchTaskCounts(boardId: number): Promise<TaskCounts> {
  return request<TaskCounts>(`/api/boards/${boardId}/tasks/counts`);
}

// ---------------------------------------------------------------------------
// CSV Import API (optional extra)
// ---------------------------------------------------------------------------

/**
 * Upload a CSV file to bulk-import tasks into a board.
 * Uses a raw fetch (no Content-Type header) so the browser sets
 * multipart/form-data with the correct boundary automatically.
 */
export async function importTasksCsv(boardId: number, file: File): Promise<Task[]> {
  const formData = new FormData();
  formData.append("file", file);

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}/api/boards/${boardId}/tasks/import`, {
      method: "POST",
      body: formData,
      // NOTE: Do NOT set Content-Type — browser sets it with the correct boundary
    });
  } catch {
    throw new Error(
      `Cannot connect to backend service at ${BASE_URL}. ` +
        "Please verify the API is running."
    );
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const envelope = data as { error?: string; message?: string } | null;
    throw new Error(
      envelope?.message ?? `CSV import failed with status ${response.status}`
    );
  }

  return data as Task[];
}

export { BASE_URL };
