"""
schemas.py — Pydantic v2 request/response models.

Separation of concerns:
  - Request schemas validate incoming JSON (strict field constraints).
  - Response schemas define the exact contract returned to the client.
  - ErrorResponse is the unified error envelope used across all error cases (R16).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"


# ---------------------------------------------------------------------------
# Board Schemas
# ---------------------------------------------------------------------------

class BoardCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Board name — must be non-empty")

    @field_validator("name")
    @classmethod
    def name_must_not_be_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Board name must not be blank or whitespace only")
        return stripped


class BoardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Task Schemas
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Task title — must be non-empty")
    description: Optional[str] = Field(default=None)
    status: TaskStatus = Field(default=TaskStatus.TODO)

    @field_validator("title")
    @classmethod
    def title_must_not_be_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Task title must not be blank or whitespace only")
        return stripped


class TaskStatusUpdate(BaseModel):
    status: TaskStatus = Field(..., description="New status — must be TODO, IN_PROGRESS, or DONE")


class TaskUpdate(BaseModel):
    """
    PATCH schema for inline task editing.
    All fields are optional — only provided (non-None) fields are applied.
    """
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Task title must not be blank or whitespace only")
        return stripped


class TaskCounts(BaseModel):
    """Aggregated task counts per status — returned by GET /api/boards/{id}/tasks/counts."""
    TODO: int = 0
    IN_PROGRESS: int = 0
    DONE: int = 0


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    board_id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Unified Error Envelope (R16)
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    message: str
    field: Optional[str] = None
