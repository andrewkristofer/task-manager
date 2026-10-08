"""
models.py — SQLAlchemy ORM models.

Design decisions:
  - boards.id / tasks.id: Integer primary keys (simple, efficient for this scope).
  - tasks.board_id: ForeignKey with ondelete="CASCADE" (R4) so PostgreSQL
    automatically removes all child tasks when a board is deleted — no
    application-level cleanup needed, no orphan rows possible.
  - Index on tasks(board_id): B-tree index for the high-frequency JOIN/filter
    when loading a board's task list (R5).
  - Index on tasks(status): B-tree index for the optional ?status= query filter
    on GET /api/boards/{boardId}/tasks (R5).
  - Timestamps: server_default=func.now() delegates default to PostgreSQL,
    ensuring accuracy independent of application server clock.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship — populated when accessing board.tasks
    tasks = relationship("Task", back_populates="board", cascade="all, delete-orphan")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(
        Integer,
        ForeignKey("boards.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="TODO", server_default="TODO")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationship back to parent board
    board = relationship("Board", back_populates="tasks")

    # Explicit B-tree indexes (R5)
    __table_args__ = (
        Index("ix_tasks_board_id", "board_id"),
        Index("ix_tasks_status", "status"),
    )
