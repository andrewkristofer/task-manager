import React from "react";
import type { Task, TaskStatus } from "../types";

interface Props {
  task: Task;
  onStatusChange: (taskId: number, newStatus: TaskStatus) => Promise<void>;
  onDelete: (taskId: number) => Promise<void>;
  onUpdate: (taskId: number, payload: { title?: string; description?: string | null }) => Promise<void>;
}

const STATUS_OPTIONS: TaskStatus[] = ["TODO", "IN_PROGRESS", "DONE"];

const STATUS_LABELS: Record<TaskStatus, string> = {
  TODO: "To Do",
  IN_PROGRESS: "In Progress",
  DONE: "Done",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export const TaskCard: React.FC<Props> = ({ task, onStatusChange, onDelete, onUpdate }) => {
  const [updating, setUpdating] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  // --- Inline editing state ---
  const [editing, setEditing] = React.useState(false);
  const [editTitle, setEditTitle] = React.useState(task.title);
  const [editDescription, setEditDescription] = React.useState(task.description ?? "");
  const [saving, setSaving] = React.useState(false);

  const handleStartEdit = () => {
    setEditTitle(task.title);
    setEditDescription(task.description ?? "");
    setEditing(true);
    setError(null);
  };

  const handleCancelEdit = () => {
    setEditing(false);
    setError(null);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = editTitle.trim();
    if (!trimmed) {
      setError("Task title cannot be empty.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onUpdate(task.id, {
        title: trimmed,
        description: editDescription.trim() || null,
      });
      setEditing(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save changes.");
    } finally {
      setSaving(false);
    }
  };

  // --- Escape key cancels edit ---
  React.useEffect(() => {
    if (!editing) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleCancelEdit();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [editing]);

  const handleStatusChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as TaskStatus;
    setUpdating(true);
    setError(null);
    try {
      await onStatusChange(task.id, newStatus);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status.");
    } finally {
      setUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Delete task "${task.title}"?`)) return;
    setDeleting(true);
    setError(null);
    try {
      await onDelete(task.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete task.");
      setDeleting(false);
    }
  };

  return (
    <article
      className={`task-card task-card--${task.status.toLowerCase().replace("_", "-")}${editing ? " task-card--editing" : ""}`}
      aria-label={`Task: ${task.title}`}
    >
      {editing ? (
        /* ---- Edit mode ---- */
        <form
          className="task-card__edit-area"
          onSubmit={handleSaveEdit}
          aria-label="Edit task"
        >
          <label htmlFor={`edit-title-${task.id}`} className="form-label">
            Title <span aria-hidden="true">*</span>
          </label>
          <input
            id={`edit-title-${task.id}`}
            type="text"
            className="input"
            value={editTitle}
            onChange={(e) => { setEditTitle(e.target.value); setError(null); }}
            disabled={saving}
            maxLength={500}
            autoFocus
            required
          />

          <label htmlFor={`edit-desc-${task.id}`} className="form-label">
            Description
          </label>
          <textarea
            id={`edit-desc-${task.id}`}
            className="input textarea"
            value={editDescription}
            onChange={(e) => setEditDescription(e.target.value)}
            disabled={saving}
            rows={2}
          />

          {error && (
            <p className="field-error" role="alert">{error}</p>
          )}

          <div className="task-card__edit-actions">
            <button
              id={`task-save-${task.id}`}
              type="submit"
              className="btn btn--primary btn--sm"
              disabled={saving}
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              id={`task-edit-cancel-${task.id}`}
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={handleCancelEdit}
              disabled={saving}
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        /* ---- View mode ---- */
        <>
          <header className="task-card__header">
            <h3 className="task-card__title">{task.title}</h3>
            <div className="task-card__actions">
              <button
                id={`task-edit-${task.id}`}
                className="task-card__edit-btn"
                onClick={handleStartEdit}
                disabled={deleting || updating}
                title="Edit task"
                aria-label={`Edit task ${task.title}`}
              >
                ✏️
              </button>
              <button
                id={`task-delete-${task.id}`}
                className="task-card__delete"
                onClick={handleDelete}
                disabled={deleting}
                aria-label={`Delete task ${task.title}`}
                title="Delete task"
              >
                {deleting ? "…" : "✕"}
              </button>
            </div>
          </header>

          {task.description && (
            <p className="task-card__description">{task.description}</p>
          )}

          <footer className="task-card__footer">
            <label
              htmlFor={`task-status-${task.id}`}
              className="visually-hidden"
            >
              Status
            </label>
            <select
              id={`task-status-${task.id}`}
              className="select task-card__status-select"
              value={task.status}
              onChange={handleStatusChange}
              disabled={updating}
              aria-label="Change task status"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>

            <time
              className="task-card__date"
              dateTime={task.created_at}
              title={`Updated: ${formatDate(task.updated_at)}`}
            >
              {formatDate(task.created_at)}
            </time>
          </footer>

          {error && (
            <p className="field-error" role="alert">{error}</p>
          )}
        </>
      )}
    </article>
  );
};
