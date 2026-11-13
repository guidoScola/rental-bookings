import os
from collections.abc import Iterator

# Must be set before importing the app: settings are read at import time.
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.auth import hash_password, require_user, require_user_page  # noqa: E402
from app.db import engine, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Apartment, AppUser  # noqa: E402

TEST_PASSWORD = "correct-horse"


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
def anon_client(session: Session) -> Iterator[TestClient]:
    """HTTP client with no login, whose requests use the test session."""
    app.dependency_overrides[get_session] = lambda: session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def client(anon_client: TestClient) -> TestClient:
    """HTTP client that skips the login, for tests about everything else.

    Logging in for real would hash with bcrypt in every test (slow); the login
    itself is tested in test_auth.py.
    """
    app.dependency_overrides[require_user] = lambda: 1
    app.dependency_overrides[require_user_page] = lambda: 1
    return anon_client


@pytest.fixture
def user(session: Session) -> AppUser:
    user = AppUser(username="test-owner", password_hash=hash_password(TEST_PASSWORD))
    session.add(user)
    session.commit()
    return user
