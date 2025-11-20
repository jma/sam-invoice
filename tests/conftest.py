import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sam_invoice.models.database as database
from sam_invoice.models.customer import Base


@pytest.fixture
def in_memory_db(monkeypatch):
    """Provide an in-memory SQLite database for tests.

    This fixture creates a temporary in-memory SQLite engine, creates all
    tables from the ORM `Base`, then monkeypatches the project's
    `database.SessionLocal` to use a session bound to this engine.

    The fixture yields control to the test and performs teardown by
    dropping all tables and disposing the engine.
    """

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "SessionLocal", Session)
    try:
        yield
    finally:
        # teardown: drop all tables and dispose engine
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
