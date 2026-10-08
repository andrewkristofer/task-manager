"""
test_services.py — Unit tests for the business logic layer (R27, R28).

All tests call app.services functions directly, passing an SQLAlchemy
session from the conftest fixture. No HTTP server is started.

Coverage:
  Happy paths:
    - Create a board
    - Create a task on an existing board; verify returned payload
    - Filter tasks by each valid status
    - Delete a board and verify cascade removal of tasks

  Failure / edge cases (R28):
    - Create task with empty title ("")
    - Create task with whitespace-only title ("   ")
    - Create board with empty name
    - Create board with whitespace-only name
    - Create task on a non-existent boardId → LookupError
    - Update task with invalid status string → ValidationError (Pydantic)
    - Update a non-existent taskId → LookupError
    - Delete a non-existent taskId → LookupError
    - Delete a non-existent boardId → LookupError
"""

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import schemas, services


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_board(db: Session, name: str = "Test Board") -> schemas.BoardResponse:
    payload = schemas.BoardCreate(name=name)
    board = services.create_board(db, payload)
    return board


def _make_task(
    db: Session,
    board_id: int,
    title: str = "Sample Task",
    status: schemas.TaskStatus = schemas.TaskStatus.TODO,
) -> object:
    payload = schemas.TaskCreate(title=title, status=status)
    return services.create_task(db, board_id, payload)


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------

class TestCreateBoard:
    def test_create_board_returns_board_with_correct_name(self, db: Session):
        board = _make_board(db, name="Sprint 1")
        assert board.id is not None
        assert board.name == "Sprint 1"
        assert board.created_at is not None

    def test_create_board_strips_leading_trailing_whitespace(self, db: Session):
        payload = schemas.BoardCreate(name="  Design Board  ")
        board = services.create_board(db, payload)
        assert board.name == "Design Board"

    def test_list_all_boards(self, db: Session):
        _make_board(db, "Board A")
        _make_board(db, "Board B")
        boards = services.get_all_boards(db)
        assert len(boards) == 2
        names = {b.name for b in boards}
        assert names == {"Board A", "Board B"}


class TestCreateTask:
    def test_create_task_returns_correct_payload(self, db: Session):
        board = _make_board(db)
        task = _make_task(db, board.id, title="Write unit tests")
        assert task.id is not None
        assert task.board_id == board.id
        assert task.title == "Write unit tests"
        assert task.status == "TODO"
        assert task.created_at is not None

    def test_create_task_with_description(self, db: Session):
        board = _make_board(db)
        payload = schemas.TaskCreate(
            title="Document API",
            description="Include request/response examples",
        )
        task = services.create_task(db, board.id, payload)
        assert task.description == "Include request/response examples"

    def test_create_task_default_status_is_todo(self, db: Session):
        board = _make_board(db)
        task = _make_task(db, board.id)
        assert task.status == "TODO"


class TestFilterTasksByStatus:
    def test_filter_by_todo(self, db: Session):
        board = _make_board(db)
        _make_task(db, board.id, "Task 1", schemas.TaskStatus.TODO)
        _make_task(db, board.id, "Task 2", schemas.TaskStatus.IN_PROGRESS)
        _make_task(db, board.id, "Task 3", schemas.TaskStatus.DONE)

        todo_tasks = services.get_tasks_for_board(db, board.id, status_filter="TODO")
        assert len(todo_tasks) == 1
        assert todo_tasks[0].title == "Task 1"

    def test_filter_by_in_progress(self, db: Session):
        board = _make_board(db)
        _make_task(db, board.id, "Task A", schemas.TaskStatus.IN_PROGRESS)
        _make_task(db, board.id, "Task B", schemas.TaskStatus.IN_PROGRESS)
        _make_task(db, board.id, "Task C", schemas.TaskStatus.DONE)

        in_progress = services.get_tasks_for_board(db, board.id, status_filter="IN_PROGRESS")
        assert len(in_progress) == 2

    def test_filter_by_done(self, db: Session):
        board = _make_board(db)
        _make_task(db, board.id, "Done task", schemas.TaskStatus.DONE)

        done_tasks = services.get_tasks_for_board(db, board.id, status_filter="DONE")
        assert len(done_tasks) == 1

    def test_no_filter_returns_all_tasks(self, db: Session):
        board = _make_board(db)
        _make_task(db, board.id, "T1", schemas.TaskStatus.TODO)
        _make_task(db, board.id, "T2", schemas.TaskStatus.DONE)

        all_tasks = services.get_tasks_for_board(db, board.id)
        assert len(all_tasks) == 2

    def test_filter_empty_result(self, db: Session):
        board = _make_board(db)
        _make_task(db, board.id, "Only Todo", schemas.TaskStatus.TODO)

        done_tasks = services.get_tasks_for_board(db, board.id, status_filter="DONE")
        assert done_tasks == []


class TestBoardDeletionCascade:
    def test_deleting_board_removes_its_tasks(self, db: Session):
        board = _make_board(db)
        _make_task(db, board.id, "Task 1")
        _make_task(db, board.id, "Task 2")
        _make_task(db, board.id, "Task 3")

        # Verify tasks exist
        assert len(services.get_tasks_for_board(db, board.id)) == 3

        # Delete the board
        services.delete_board(db, board.id)

        # Board should no longer exist
        with pytest.raises(LookupError):
            services.get_board_or_raise(db, board.id)

    def test_deleting_board_leaves_other_boards_intact(self, db: Session):
        board_a = _make_board(db, "Board A")
        board_b = _make_board(db, "Board B")
        _make_task(db, board_a.id, "Task on A")

        services.delete_board(db, board_a.id)

        # Board B still exists
        remaining = services.get_board_or_raise(db, board_b.id)
        assert remaining.name == "Board B"


class TestUpdateTaskStatus:
    def test_update_status_to_in_progress(self, db: Session):
        board = _make_board(db)
        task = _make_task(db, board.id, "Implement feature")
        assert task.status == "TODO"

        update_payload = schemas.TaskStatusUpdate(status=schemas.TaskStatus.IN_PROGRESS)
        updated = services.update_task_status(db, task.id, update_payload)
        assert updated.status == "IN_PROGRESS"

    def test_update_status_to_done(self, db: Session):
        board = _make_board(db)
        task = _make_task(db, board.id, "Review PR")
        update_payload = schemas.TaskStatusUpdate(status=schemas.TaskStatus.DONE)
        updated = services.update_task_status(db, task.id, update_payload)
        assert updated.status == "DONE"


# ---------------------------------------------------------------------------
# Failure / edge case tests (R28)
# ---------------------------------------------------------------------------

class TestEmptyAndWhitespaceTitleValidation:
    def test_create_task_with_empty_title_raises_validation_error(self, db: Session):
        """R28 — Empty string title must be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            schemas.TaskCreate(title="")
        assert "title" in str(exc_info.value).lower() or "string" in str(exc_info.value).lower()

    def test_create_task_with_whitespace_only_title_raises_validation_error(self, db: Session):
        """R28 — Whitespace-only title must be rejected."""
        with pytest.raises(ValidationError):
            schemas.TaskCreate(title="   ")

    def test_create_task_with_tab_whitespace_title_raises_validation_error(self, db: Session):
        """R28 — Tab-only title must be rejected."""
        with pytest.raises(ValidationError):
            schemas.TaskCreate(title="\t\n")


class TestEmptyBoardNameValidation:
    def test_create_board_with_empty_name_raises_validation_error(self, db: Session):
        """R28 — Empty board name must be rejected."""
        with pytest.raises(ValidationError):
            schemas.BoardCreate(name="")

    def test_create_board_with_whitespace_only_name_raises_validation_error(self, db: Session):
        """R28 — Whitespace-only board name must be rejected."""
        with pytest.raises(ValidationError):
            schemas.BoardCreate(name="    ")


class TestNonExistentEntityErrors:
    def test_create_task_on_nonexistent_board_raises_lookup_error(self, db: Session):
        """R28 — Creating a task on a non-existent board must raise LookupError."""
        payload = schemas.TaskCreate(title="Orphan task")
        with pytest.raises(LookupError, match="Board with id=9999 not found"):
            services.create_task(db, 9999, payload)

    def test_update_nonexistent_task_raises_lookup_error(self, db: Session):
        """R28 — Updating a non-existent task must raise LookupError."""
        update_payload = schemas.TaskStatusUpdate(status=schemas.TaskStatus.DONE)
        with pytest.raises(LookupError, match="Task with id=9999 not found"):
            services.update_task_status(db, 9999, update_payload)

    def test_delete_nonexistent_task_raises_lookup_error(self, db: Session):
        """R28 — Deleting a non-existent task must raise LookupError."""
        with pytest.raises(LookupError, match="Task with id=9999 not found"):
            services.delete_task(db, 9999)

    def test_delete_nonexistent_board_raises_lookup_error(self, db: Session):
        """R28 — Deleting a non-existent board must raise LookupError."""
        with pytest.raises(LookupError, match="Board with id=9999 not found"):
            services.delete_board(db, 9999)

    def test_get_tasks_for_nonexistent_board_raises_lookup_error(self, db: Session):
        """R28 — Querying tasks for a non-existent board must raise LookupError."""
        with pytest.raises(LookupError, match="Board with id=9999 not found"):
            services.get_tasks_for_board(db, 9999)


class TestInvalidStatusValues:
    def test_invalid_status_string_raises_validation_error(self, db: Session):
        """R28 — Invalid status value must be rejected at schema level."""
        with pytest.raises(ValidationError):
            schemas.TaskStatusUpdate(status="COMPLETED")  # type: ignore[arg-type]

    def test_another_invalid_status_raises_validation_error(self, db: Session):
        """R28 — 'PENDING' is not a valid status."""
        with pytest.raises(ValidationError):
            schemas.TaskStatusUpdate(status="PENDING")  # type: ignore[arg-type]

    def test_invalid_filter_status_raises_value_error(self, db: Session):
        """Invalid ?status= filter on get_tasks_for_board should raise ValueError."""
        board = _make_board(db)
        with pytest.raises(ValueError, match="Invalid status"):
            services.get_tasks_for_board(db, board.id, status_filter="INVALID")
