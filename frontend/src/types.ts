// types.ts — Shared TypeScript types mirroring backend schemas exactly.

export type TaskStatus = "TODO" | "IN_PROGRESS" | "DONE";

export interface Board {
  id: number;
  name: string;
  created_at: string; // ISO 8601 string from backend
}

export interface Task {
  id: number;
  board_id: number;
  title: string;
  description: string | null;
  status: TaskStatus;
  created_at: string;
  updated_at: string;
}

// API error envelope matching the backend's unified error response (R16)
export interface ApiError {
  error: string;
  message: string;
  field?: string;
}

export type StatusFilter = "ALL" | TaskStatus;

/** Task counts per status — returned by GET /api/boards/{id}/tasks/counts */
export interface TaskCounts {
  TODO: number;
  IN_PROGRESS: number;
  DONE: number;
}
