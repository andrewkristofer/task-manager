/**
 * App.tsx — Root component.
 *
 * Manages all application state (boards, tasks, selection, filters, counts).
 * All API calls are centralised here and results/errors propagated
 * to child components as props.
 *
 * Non-happy-path handling (R25):
 *   - Loading indicators on both boards and tasks while requests are in-flight.
 *   - Empty states: "No boards yet", "No tasks in this board yet".
 *   - Backend unreachable: clear human-readable error with the configured URL.
 *   - No blank screens — every error state renders a meaningful message.
 */

import React from "react";
import type { Board, Task, TaskStatus, StatusFilter, TaskCounts } from "./types";
import {
  fetchBoards,
  createBoard,
  deleteBoard,
  fetchTasks,
  createTask,
  updateTask,
  deleteTask,
  BASE_URL,
  fetchTaskCounts,
  importTasksCsv,
} from "./api";
import { BoardSidebar } from "./components/BoardSidebar";
import { TaskBoard } from "./components/TaskBoard";

export default function App() {
  // -------------------------------------------------------------------------
  // State
  // -------------------------------------------------------------------------
  const [boards, setBoards] = React.useState<Board[]>([]);
  const [boardsLoading, setBoardsLoading] = React.useState(true);
  const [boardsError, setBoardsError] = React.useState<string | null>(null);

  const [selectedBoardId, setSelectedBoardId] = React.useState<number | null>(null);

  const [tasks, setTasks] = React.useState<Task[]>([]);
  const [tasksLoading, setTasksLoading] = React.useState(false);
  const [tasksError, setTasksError] = React.useState<string | null>(null);

  const [statusFilter, setStatusFilter] = React.useState<StatusFilter>("ALL");

  const [taskCounts, setTaskCounts] = React.useState<TaskCounts | null>(null);

  // -------------------------------------------------------------------------
  // Load boards on mount
  // -------------------------------------------------------------------------
  React.useEffect(() => {
    let cancelled = false;
    setBoardsLoading(true);
    setBoardsError(null);

    fetchBoards()
      .then((data) => {
        if (cancelled) return;
        setBoards(data);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setBoardsError(err.message);
      })
      .finally(() => {
        if (!cancelled) setBoardsLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  // -------------------------------------------------------------------------
  // Load tasks + counts whenever selected board or filter changes
  // -------------------------------------------------------------------------
  React.useEffect(() => {
    if (selectedBoardId === null) {
      setTasks([]);
      setTaskCounts(null);
      return;
    }

    let cancelled = false;
    setTasksLoading(true);
    setTasksError(null);

    const filter = statusFilter === "ALL" ? undefined : (statusFilter as TaskStatus);

    Promise.all([
      fetchTasks(selectedBoardId, filter),
      fetchTaskCounts(selectedBoardId),
    ])
      .then(([tasksData, countsData]) => {
        if (cancelled) return;
        setTasks(tasksData);
        setTaskCounts(countsData);
      })
      .catch((err: Error) => {
        if (cancelled) return;
        setTasksError(err.message);
      })
      .finally(() => {
        if (!cancelled) setTasksLoading(false);
      });

    return () => { cancelled = true; };
  }, [selectedBoardId, statusFilter]);

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------
  /** Silently refresh status counters — non-critical, never surfaces an error. */
  const refreshCounts = React.useCallback((boardId: number) => {
    fetchTaskCounts(boardId)
      .then(setTaskCounts)
      .catch(() => { /* counts are non-critical */ });
  }, []);

  // -------------------------------------------------------------------------
  // Board handlers
  // -------------------------------------------------------------------------
  const handleCreateBoard = async (name: string) => {
    const newBoard = await createBoard(name);
    setBoards((prev) => [...prev, newBoard]);
    setSelectedBoardId(newBoard.id);
    setStatusFilter("ALL");
  };

  const handleDeleteBoard = async (boardId: number) => {
    await deleteBoard(boardId);
    setBoards((prev) => prev.filter((b) => b.id !== boardId));
    if (selectedBoardId === boardId) {
      setSelectedBoardId(null);
      setTasks([]);
      setTaskCounts(null);
    }
  };

  const handleSelectBoard = (boardId: number) => {
    setSelectedBoardId(boardId);
    setStatusFilter("ALL");
  };

  // -------------------------------------------------------------------------
  // Task handlers
  // -------------------------------------------------------------------------
  const handleCreateTask = async (
    boardId: number,
    payload: { title: string; description?: string; status?: TaskStatus }
  ) => {
    const newTask = await createTask(boardId, payload);
    // Only show the new task if it matches the active filter
    if (statusFilter === "ALL" || statusFilter === newTask.status) {
      setTasks((prev) => [...prev, newTask]);
    }
    refreshCounts(boardId);
  };

  const handleStatusChange = async (taskId: number, newStatus: TaskStatus) => {
    const updated = await updateTask(taskId, { status: newStatus });
    if (statusFilter === "ALL" || statusFilter === newStatus) {
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? updated : t))
      );
    } else {
      // Task no longer matches filter — remove from visible list
      setTasks((prev) => prev.filter((t) => t.id !== taskId));
    }
    if (selectedBoardId !== null) refreshCounts(selectedBoardId);
  };

  /** Inline task editing — updates title and/or description (status unchanged). */
  const handleUpdateTask = async (
    taskId: number,
    payload: { title?: string; description?: string | null }
  ) => {
    const updated = await updateTask(taskId, payload);
    setTasks((prev) => prev.map((t) => (t.id === taskId ? updated : t)));
  };

  const handleDeleteTask = async (taskId: number) => {
    await deleteTask(taskId);
    setTasks((prev) => prev.filter((t) => t.id !== taskId));
    if (selectedBoardId !== null) refreshCounts(selectedBoardId);
  };

  const handleImportCsv = async (file: File): Promise<number> => {
    if (selectedBoardId === null) throw new Error("No board selected");
    const imported = await importTasksCsv(selectedBoardId, file);
    // Reload the task list so all imported tasks appear (respecting current filter)
    const filter = statusFilter === "ALL" ? undefined : (statusFilter as TaskStatus);
    const refreshed = await fetchTasks(selectedBoardId, filter);
    setTasks(refreshed);
    refreshCounts(selectedBoardId);
    return imported.length;
  };

  // -------------------------------------------------------------------------
  // Derived state
  // -------------------------------------------------------------------------
  const selectedBoard = boards.find((b) => b.id === selectedBoardId) ?? null;
  const backendUnreachable =
    boardsError !== null &&
    boardsError.startsWith("Cannot connect to backend");

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className="app-layout">
      {/* App Header */}
      <header className="app-header">
        <span className="app-header__logo">📋</span>
        <h1 className="app-header__title">Task Manager</h1>
        <span className="app-header__sub">WPP Media — Study Case</span>
      </header>

      {/* Backend unreachable: full-page error */}
      {backendUnreachable ? (
        <div className="backend-error-screen" role="alert">
          <div className="backend-error-card">
            <h2>⚠️ Backend Unavailable</h2>
            <p>
              Cannot connect to backend service at{" "}
              <code>{BASE_URL}</code>.
            </p>
            <p>Please verify the API is running:</p>
            <pre className="code-block">
              cd backend{"\n"}
              uvicorn app.main:app --reload --port 8000
            </pre>
            <button
              id="retry-btn"
              className="btn btn--primary"
              onClick={() => window.location.reload()}
            >
              Retry
            </button>
          </div>
        </div>
      ) : (
        <div className="app-body">
          {/* Sidebar */}
          <BoardSidebar
            boards={boards}
            selectedBoardId={selectedBoardId}
            onSelect={handleSelectBoard}
            onDelete={handleDeleteBoard}
            onCreateBoard={handleCreateBoard}
            loading={boardsLoading}
            error={boardsError}
          />

          {/* Main area */}
          <div className="main-area">
            {selectedBoard === null ? (
              <div className="no-board-selected">
                <div className="no-board-selected__content">
                  <span className="no-board-selected__icon">📂</span>
                  <h2>Select or create a board</h2>
                  <p>Choose a board from the left panel to view its tasks.</p>
                </div>
              </div>
            ) : (
              <TaskBoard
                boardId={selectedBoard.id}
                boardName={selectedBoard.name}
                tasks={tasks}
                loading={tasksLoading}
                error={tasksError}
                statusFilter={statusFilter}
                onFilterChange={setStatusFilter}
                onCreateTask={handleCreateTask}
                onStatusChange={handleStatusChange}
                onUpdateTask={handleUpdateTask}
                onDeleteTask={handleDeleteTask}
                onImportCsv={handleImportCsv}
                taskCounts={taskCounts}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
