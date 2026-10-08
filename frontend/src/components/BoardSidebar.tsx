import React from "react";
import type { Board } from "../types";

interface Props {
  boards: Board[];
  selectedBoardId: number | null;
  onSelect: (id: number) => void;
  onDelete: (id: number) => void;
  onCreateBoard: (name: string) => Promise<void>;
  loading: boolean;
  error: string | null;
}

export const BoardSidebar: React.FC<Props> = ({
  boards,
  selectedBoardId,
  onSelect,
  onDelete,
  onCreateBoard,
  loading,
  error,
}) => {
  const [newBoardName, setNewBoardName] = React.useState("");
  const [creating, setCreating] = React.useState(false);
  const [createError, setCreateError] = React.useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = newBoardName.trim();
    if (!trimmed) {
      setCreateError("Board name cannot be empty.");
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      await onCreateBoard(trimmed);
      setNewBoardName("");
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "Failed to create board.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2 className="sidebar-title">Boards</h2>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading-text">Loading boards…</div>
      ) : boards.length === 0 ? (
        <p className="empty-state">No boards yet. Create one below.</p>
      ) : (
        <ul className="board-list" role="listbox" aria-label="Available boards">
          {boards.map((board) => (
            <li
              key={board.id}
              className={`board-item ${selectedBoardId === board.id ? "board-item--active" : ""}`}
              role="option"
              aria-selected={selectedBoardId === board.id}
            >
              <button
                id={`board-select-${board.id}`}
                className="board-item__name"
                onClick={() => onSelect(board.id)}
                title={board.name}
              >
                {board.name}
              </button>
              <button
                id={`board-delete-${board.id}`}
                className="board-item__delete"
                onClick={(e) => {
                  e.stopPropagation();
                  if (
                    window.confirm(
                      `Delete board "${board.name}"? All tasks will be permanently removed.`
                    )
                  ) {
                    onDelete(board.id);
                  }
                }}
                title="Delete board"
                aria-label={`Delete board ${board.name}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}

      <form className="create-board-form" onSubmit={handleCreate} aria-label="Create new board">
        <label htmlFor="new-board-name" className="visually-hidden">
          New board name
        </label>
        <input
          id="new-board-name"
          type="text"
          className="input"
          placeholder="New board name…"
          value={newBoardName}
          onChange={(e) => {
            setNewBoardName(e.target.value);
            setCreateError(null);
          }}
          disabled={creating}
          maxLength={255}
        />
        {createError && (
          <p className="field-error" role="alert">
            {createError}
          </p>
        )}
        <button
          id="create-board-btn"
          type="submit"
          className="btn btn--primary btn--full"
          disabled={creating}
        >
          {creating ? "Creating…" : "+ Create Board"}
        </button>
      </form>
    </aside>
  );
};
