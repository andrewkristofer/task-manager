import React from "react";
import type { TaskStatus } from "../types";

interface Props {
  boardId: number;
  onCreateTask: (
    boardId: number,
    payload: { title: string; description?: string; status?: TaskStatus }
  ) => Promise<void>;
}

export const TaskCreateForm: React.FC<Props> = ({ boardId, onCreateTask }) => {
  const [title, setTitle] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [status, setStatus] = React.useState<TaskStatus>("TODO");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [expanded, setExpanded] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError("Task title cannot be empty.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onCreateTask(boardId, {
        title: trimmedTitle,
        description: description.trim() || undefined,
        status,
      });
      setTitle("");
      setDescription("");
      setStatus("TODO");
      setExpanded(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!expanded) {
    return (
      <button
        id="add-task-btn"
        className="btn btn--ghost btn--full"
        onClick={() => setExpanded(true)}
      >
        + Add Task
      </button>
    );
  }

  return (
    <form
      className="task-create-form"
      onSubmit={handleSubmit}
      aria-label="Create new task"
    >
      <h4 className="task-create-form__title">New Task</h4>

      <label htmlFor="task-title-input" className="form-label">
        Title <span aria-hidden="true">*</span>
      </label>
      <input
        id="task-title-input"
        type="text"
        className="input"
        placeholder="Task title…"
        value={title}
        onChange={(e) => {
          setTitle(e.target.value);
          setError(null);
        }}
        disabled={submitting}
        maxLength={500}
        autoFocus
        required
      />

      <label htmlFor="task-desc-input" className="form-label">
        Description
      </label>
      <textarea
        id="task-desc-input"
        className="input textarea"
        placeholder="Optional description…"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        disabled={submitting}
        rows={3}
      />

      <label htmlFor="task-status-new" className="form-label">
        Initial Status
      </label>
      <select
        id="task-status-new"
        className="select"
        value={status}
        onChange={(e) => setStatus(e.target.value as TaskStatus)}
        disabled={submitting}
      >
        <option value="TODO">To Do</option>
        <option value="IN_PROGRESS">In Progress</option>
        <option value="DONE">Done</option>
      </select>

      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}

      <div className="task-create-form__actions">
        <button
          id="task-submit-btn"
          type="submit"
          className="btn btn--primary"
          disabled={submitting}
        >
          {submitting ? "Creating…" : "Create Task"}
        </button>
        <button
          id="task-cancel-btn"
          type="button"
          className="btn btn--secondary"
          onClick={() => {
            setExpanded(false);
            setError(null);
            setTitle("");
            setDescription("");
          }}
          disabled={submitting}
        >
          Cancel
        </button>
      </div>
    </form>
  );
};
