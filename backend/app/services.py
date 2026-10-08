"""
services.py — Business logic and data-access layer.

All functions accept an SQLAlchemy Session as their first argument.
This makes the service layer independently testable without launching
a web server (R27): tests instantiate a real session against an in-memory
or test database and call these functions directly.

Raises:
  ValueError   — business-rule violations (empty title, invalid status, etc.)
  LookupError  — entity not found (board or task does not exist)
"""

import csv
import io
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models, schemas


# ---------------------------------------------------------------------------
# Board services
# ---------------------------------------------------------------------------

def get_all_boards(db: Session) -> list[models.Board]:
    """Return every board ordered by creation time (most recent last)."""
    return db.query(models.Board).order_by(models.Board.created_at).all()


def create_board(db: Session, data: schemas.BoardCreate) -> models.Board:
    """
    Persist a new Board.
    Validation is already enforced by BoardCreate; this layer adds no
    further rules but is the canonical place for future business logic.
    """
    board = models.Board(name=data.name)
    db.add(board)
    db.commit()
    db.refresh(board)
    return board


def get_board_or_raise(db: Session, board_id: int) -> models.Board:
    """Return the board with the given id, or raise LookupError."""
    board = db.query(models.Board).filter(models.Board.id == board_id).first()
    if board is None:
        raise LookupError(f"Board with id={board_id} not found")
    return board


def delete_board(db: Session, board_id: int) -> None:
    """
    Delete a board by id.
    PostgreSQL CASCADE (defined on the FK) removes all associated tasks
    automatically — no application-level loop needed (R4).
    Raises LookupError if the board does not exist.
    """
    board = get_board_or_raise(db, board_id)
    db.delete(board)
    db.commit()


# ---------------------------------------------------------------------------
# Task services
# ---------------------------------------------------------------------------

VALID_STATUSES = {s.value for s in schemas.TaskStatus}


def get_tasks_for_board(
    db: Session,
    board_id: int,
    status_filter: Optional[str] = None,
) -> list[models.Task]:
    """
    Return tasks for a given board, optionally filtered by status.
    Raises LookupError if the board does not exist.
    Raises ValueError if an invalid status string is provided.
    """
    # Verify board exists (R10 — 404 if not found)
    get_board_or_raise(db, board_id)

    if status_filter is not None:
        if status_filter not in VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{status_filter}'. "
                f"Valid values are: {', '.join(sorted(VALID_STATUSES))}"
            )
        return (
            db.query(models.Task)
            .filter(
                models.Task.board_id == board_id,
                models.Task.status == status_filter,
            )
            .order_by(models.Task.created_at)
            .all()
        )

    return (
        db.query(models.Task)
        .filter(models.Task.board_id == board_id)
        .order_by(models.Task.created_at)
        .all()
    )


def create_task(
    db: Session,
    board_id: int,
    data: schemas.TaskCreate,
) -> models.Task:
    """
    Create a task on the specified board.
    Raises LookupError if the board does not exist (R11 — 404).
    Title and status validation is handled by the TaskCreate schema.
    """
    # Verify board exists
    get_board_or_raise(db, board_id)

    task = models.Task(
        board_id=board_id,
        title=data.title,
        description=data.description,
        status=data.status.value,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task_or_raise(db: Session, task_id: int) -> models.Task:
    """Return the task with the given id, or raise LookupError."""
    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task is None:
        raise LookupError(f"Task with id={task_id} not found")
    return task


def update_task_status(
    db: Session,
    task_id: int,
    data: schemas.TaskStatusUpdate,
) -> models.Task:
    """
    Update the status of an existing task.
    Raises LookupError if the task does not exist (R12 — 404).
    Status validation is handled by TaskStatusUpdate schema.
    """
    task = get_task_or_raise(db, task_id)
    task.status = data.status.value
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: int) -> None:
    """
    Delete a task by id.
    Raises LookupError if the task does not exist (R13 — 404).
    """
    task = get_task_or_raise(db, task_id)
    db.delete(task)
    db.commit()


# ---------------------------------------------------------------------------
# Optional extras
# ---------------------------------------------------------------------------

def update_task(
    db: Session,
    task_id: int,
    data: schemas.TaskUpdate,
) -> models.Task:
    """
    Update any combination of title, description, and/or status on a task.
    Only fields that are not None in `data` are applied.
    Raises LookupError if the task does not exist.
    """
    task = get_task_or_raise(db, task_id)

    if data.title is not None:
        task.title = data.title
    if data.description is not None:
        task.description = data.description
    if data.status is not None:
        task.status = data.status.value

    db.commit()
    db.refresh(task)
    return task


def get_task_status_counts(db: Session, board_id: int) -> dict[str, int]:
    """
    Return the count of tasks in each status bucket for the given board.
    Raises LookupError if the board does not exist.
    """
    get_board_or_raise(db, board_id)

    rows = (
        db.query(models.Task.status, func.count(models.Task.id))
        .filter(models.Task.board_id == board_id)
        .group_by(models.Task.status)
        .all()
    )

    counts: dict[str, int] = {"TODO": 0, "IN_PROGRESS": 0, "DONE": 0}
    for status_val, count in rows:
        if status_val in counts:
            counts[status_val] = count

    return counts


def import_tasks_from_csv(
    db: Session,
    board_id: int,
    csv_content: str,
) -> list[models.Task]:
    """
    Parse a UTF-8 CSV string and bulk-create tasks on the given board.

    Expected CSV columns:
      - title       (required, non-empty)
      - description (optional, may be empty)
      - status      (optional, defaults to TODO; must be a valid TaskStatus)

    Raises LookupError if the board does not exist.
    Raises ValueError on malformed CSV or invalid data.
    """
    get_board_or_raise(db, board_id)

    reader = csv.DictReader(io.StringIO(csv_content))

    if reader.fieldnames is None:
        raise ValueError("CSV file is empty or has no header row")

    # Normalise header names so casing/whitespace is forgiving
    fieldnames_lower = [f.strip().lower() for f in reader.fieldnames]
    if "title" not in fieldnames_lower:
        raise ValueError("CSV must contain a 'title' column header")

    created: list[models.Task] = []

    for row_num, row in enumerate(reader, start=2):
        # Normalise all keys and values
        normalized = {k.strip().lower(): (v or "").strip() for k, v in row.items()}

        title = normalized.get("title", "")
        if not title:
            raise ValueError(f"Row {row_num}: 'title' must not be empty")

        description_raw = normalized.get("description", "")
        description = description_raw if description_raw else None

        status_raw = normalized.get("status", "TODO").upper()
        if status_raw not in VALID_STATUSES:
            raise ValueError(
                f"Row {row_num}: invalid status '{status_raw}'. "
                f"Valid values are: {', '.join(sorted(VALID_STATUSES))}"
            )

        task = models.Task(
            board_id=board_id,
            title=title,
            description=description,
            status=status_raw,
        )
        db.add(task)
        created.append(task)

    if not created:
        raise ValueError("CSV file contains no data rows")

    db.commit()
    for task in created:
        db.refresh(task)

    return created
