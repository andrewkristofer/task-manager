"""
routers/boards.py — HTTP controllers for Board endpoints.

Responsibilities:
  - Parse/validate HTTP inputs (path params, request body).
  - Delegate all business logic to app.services.
  - Map service exceptions to the correct HTTP status codes.
  - Return the standardised error envelope on failure (R16).

Route ordering note: more-specific paths (/{board_id}/tasks/counts,
/{board_id}/tasks/import) are registered before the generic
/{board_id}/tasks route to guarantee unambiguous matching.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import schemas, services
from app.database import get_db

router = APIRouter(prefix="/api/boards", tags=["boards"])


@router.get("", response_model=list[schemas.BoardResponse])
def list_boards(db: Session = Depends(get_db)):
    """R8 — Return all boards."""
    return services.get_all_boards(db)


@router.post("", response_model=schemas.BoardResponse, status_code=status.HTTP_201_CREATED)
def create_board(payload: schemas.BoardCreate, db: Session = Depends(get_db)):
    """R9 — Create a new board. 422 on invalid/empty name."""
    return services.create_board(db, payload)


# ---------------------------------------------------------------------------
# Optional extras — must be defined BEFORE /{board_id}/tasks to avoid
# the path segments "counts" / "import" being swallowed as board IDs.
# FastAPI uses int type coercion so there is no real ambiguity here, but
# explicit ordering is clearer and future-proof.
# ---------------------------------------------------------------------------

@router.get("/{board_id}/tasks/counts", response_model=schemas.TaskCounts)
def get_task_counts(board_id: int, db: Session = Depends(get_db)):
    """Optional — Return task counts grouped by status for a board."""
    try:
        return services.get_task_status_counts(db, board_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "BOARD_NOT_FOUND", "message": str(exc)},
        )


@router.post(
    "/{board_id}/tasks/import",
    response_model=list[schemas.TaskResponse],
    status_code=status.HTTP_201_CREATED,
)
async def import_tasks_csv(
    board_id: int,
    file: UploadFile = File(
        ..., description="UTF-8 CSV with columns: title, description (opt), status (opt)"
    ),
    db: Session = Depends(get_db),
):
    """
    Optional — Bulk import tasks from a CSV file.

    CSV format (header row required):
        title,description,status
        Write docs,Add examples to README,TODO
        Deploy,Deploy to staging,IN_PROGRESS
    """
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_FILE",
                "message": "Uploaded file must have a .csv extension",
                "field": "file",
            },
        )
    try:
        content = await file.read()
        csv_text = content.decode("utf-8-sig")  # strip BOM if present
        return services.import_tasks_from_csv(db, board_id, csv_text)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "BOARD_NOT_FOUND", "message": str(exc)},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "CSV_PARSE_ERROR", "message": str(exc)},
        )
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "INVALID_FILE",
                "message": "CSV file must be UTF-8 encoded",
            },
        )


# ---------------------------------------------------------------------------
# Core task endpoints (R10, R11)
# ---------------------------------------------------------------------------

@router.get("/{board_id}/tasks", response_model=list[schemas.TaskResponse])
def list_tasks(
    board_id: int,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """R10 — List tasks for a board with optional ?status= filter. 404 if board not found."""
    try:
        return services.get_tasks_for_board(db, board_id, status_filter=status)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "BOARD_NOT_FOUND", "message": str(exc)},
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "INVALID_STATUS", "message": str(exc), "field": "status"},
        )


@router.post(
    "/{board_id}/tasks",
    response_model=schemas.TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    board_id: int,
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
):
    """R11 — Create a task on a board. 404 if board not found. 201 on success."""
    try:
        return services.create_task(db, board_id, payload)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "BOARD_NOT_FOUND", "message": str(exc)},
        )


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(board_id: int, db: Session = Depends(get_db)):
    """R14 — Delete a board and cascade-delete all its tasks. 404 if not found."""
    try:
        services.delete_board(db, board_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "BOARD_NOT_FOUND", "message": str(exc)},
        )
