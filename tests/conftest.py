from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from app.db import engine
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
    session.flush()  # sends the INSERT so apartment.id gets a value
    return apartment
