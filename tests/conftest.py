from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient

from app.db import engine, get_session
from app.main import app
from app.models import Apartment


@pytest.fixture
def session() -> Iterator[Session]:
    """A session whose changes are rolled back after each test.

    Every test runs inside an outer transaction that is never committed,
    so the database is left exactly as it was before the test.
    """
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def apartment(session: Session) -> Apartment:
    apartment = Apartment(name="Depto", address="Calle Falsa 123", max_guests=4)
    session.add(apartment)
    # commit only releases a savepoint (see `session`), so the outer rollback still
    # undoes it. It must be a commit and not a flush: when an endpoint rolls back
    # after an error, a flushed-only apartment would be rolled back with it.
    session.commit()
    return apartment


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """HTTP client whose requests use the test session, so they get rolled back too."""
    app.dependency_overrides[get_session] = lambda: session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
