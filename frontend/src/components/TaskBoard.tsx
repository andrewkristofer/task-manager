import React from "react";
import type { Task, TaskStatus, StatusFilter, TaskCounts } from "../types";
import { TaskCard } from "./TaskCard";
import { TaskCreateForm } from "./TaskCreateForm";

interface Props {
  boardName: string;
  tasks: Task[];
  loading: boolean;
  error: string | null;
  statusFilter: StatusFilter;
  onFilterChange: (filter: StatusFilter) => void;
  onCreateTask: (
    boardId: number,
    payload: { title: string; description?: string; status?: TaskStatus }
  ) => Promise<void>;
  onStatusChange: (taskId: number, newStatus: TaskStatus) => Promise<void>;
  onUpdateTask: (taskId: number, payload: { title?: string; description?: string | null }) => Promise<void>;
  onDeleteTask: (taskId: number) => Promise<void>;
  onImportCsv: (file: File) => Promise<number>;
  taskCounts: TaskCounts | null;
  boardId: number;
}

const FILTER_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: "ALL", label: "All" },
  { value: "TODO", label: "To Do" },
  { value: "IN_PROGRESS", label: "In Progress" },
  { value: "DONE", label: "Done" },
];

export const TaskBoard: React.FC<Props> = ({
  boardName,
  tasks,
  loading,
  error,
  statusFilter,
  onFilterChange,
  onCreateTask,
  onStatusChange,
  onUpdateTask,
  onDeleteTask,
  onImportCsv,
  taskCounts,
  boardId,
}) => {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [importState, setImportState] = React.useState<{
    type: "idle" | "loading" | "success" | "error";
    message?: string;
  }>({ type: "idle" });

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImportState({ type: "loading" });
    try {
      const count = await onImportCsv(file);
      setImportState({
        type: "success",
        message: `✓ ${count} task${count !== 1 ? "s" : ""} imported`,
      });
      e.target.value = "";
      setTimeout(() => setImportState({ type: "idle" }), 4000);
    } catch (err) {
      setImportState({
        type: "error",
        message: err instanceof Error ? err.message : "Import failed.",
      });
      e.target.value = "";
    }
  };

  return (
    <main className="task-board">
      {/* Board header + filter + CSV import */}
      <header className="task-board__header">
        <h1 className="task-board__title">{boardName}</h1>
        <div className="task-board__controls">
          <label htmlFor="status-filter" className="form-label inline-label">
            Filter:
          </label>
          <select
            id="status-filter"
            className="select"
            value={statusFilter}
            onChange={(e) => onFilterChange(e.target.value as StatusFilter)}
            aria-label="Filter tasks by status"
          >
            {FILTER_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          {/* CSV bulk import */}
          <div className="csv-import-area">
            {/* Hidden file input — triggered by the button below */}
            <input
              ref={fileInputRef}
              id="csv-file-input"
              type="file"
              accept=".csv"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <button
              id="import-csv-btn"
              className="btn btn--secondary"
              onClick={handleImportClick}
              disabled={importState.type === "loading"}
              title="Import tasks from a CSV file (columns: title, description, status)"
            >
              {importState.type === "loading" ? "Importing…" : "📥 Import CSV"}
            </button>
            {importState.type !== "idle" && importState.type !== "loading" && importState.message && (
              <span
                className={`csv-feedback csv-feedback--${importState.type}`}
                role={importState.type === "error" ? "alert" : "status"}
              >
                {importState.message}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Status counter badges */}
      {taskCounts !== null && (
        <div
          className="status-counters"
          role="status"
          aria-label="Task counts by status"
        >
          <span className="status-badge status-badge--todo">
            ● To Do: {taskCounts.TODO}
          </span>
          <span className="status-badge status-badge--in-progress">
            ● In Progress: {taskCounts.IN_PROGRESS}
          </span>
          <span className="status-badge status-badge--done">
            ✓ Done: {taskCounts.DONE}
          </span>
        </div>
      )}

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading-text">Loading tasks…</div>
      ) : tasks.length === 0 ? (
        <div className="empty-state-board">
          <p>
            {statusFilter === "ALL"
              ? "No tasks in this board yet."
              : `No tasks with status "${statusFilter.replace("_", " ")}".`}
          </p>
        </div>
      ) : (
        <ul className="task-list" aria-label={`Tasks for board ${boardName}`}>
          {tasks.map((task) => (
            <li key={task.id}>
              <TaskCard
                task={task}
                onStatusChange={onStatusChange}
                onDelete={onDeleteTask}
                onUpdate={onUpdateTask}
              />
            </li>
          ))}
        </ul>
      )}

      <div className="task-create-wrapper">
        <TaskCreateForm boardId={boardId} onCreateTask={onCreateTask} />
      </div>
    </main>
  );
};
