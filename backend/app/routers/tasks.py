"""
routers/tasks.py — HTTP controllers for Task endpoints (PATCH & DELETE).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas, services
from app.database import get_db

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.patch("/{task_id}", response_model=schemas.TaskResponse)
def update_task(
    task_id: int,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
):
    """R12 + Optional — Update task fields (title, description, status). 404 if not found. 422 if status invalid."""
    try:
        return services.update_task(db, task_id, payload)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "TASK_NOT_FOUND", "message": str(exc)},
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """R13 — Delete a task. 204 on success. 404 if not found."""
    try:
        services.delete_task(db, task_id)
    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "TASK_NOT_FOUND", "message": str(exc)},
        )
