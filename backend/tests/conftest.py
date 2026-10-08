"""
conftest.py — Pytest fixtures for the test suite.

Strategy: Use SQLite in-memory database for unit tests.
  - No Docker dependency for running tests.
  - Each test function gets a fresh, isolated database via the `db` fixture.
  - All tables are created from the SQLAlchemy models before each test
    and dropped afterwards — full isolation with no shared state.

This pattern satisfies R27: the service layer is tested directly without
launching a web server, using only a real (in-memory) database session.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base

# SQLite in-memory engine for isolated, zero-dependency unit tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture()
def db():
    """
    Yields a clean database session backed by an in-memory SQLite database.
    All tables are created before the test and dropped after.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
