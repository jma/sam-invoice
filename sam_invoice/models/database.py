"""SQLite database configuration for Sam Invoice."""

import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import all models to register them with Base metadata
from . import company, customer, product  # noqa: F401
from .customer import Base

# Default database path
DEFAULT_DB_PATH = Path.cwd() / "sam_invoice.db"

# Global engine and session factory
engine = None
SessionLocal = None

# Reduce SQLAlchemy logs to WARNING level
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def set_database_path(db_path: Path | str):
    """Set the database path and reinitialize the engine."""
    global engine, SessionLocal

    if isinstance(db_path, str):
        db_path = Path(db_path)

    database_url = f"sqlite:///{db_path.absolute()}"
    engine = create_engine(database_url, echo=False)
    SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Initialize the database by creating all tables."""
    if engine is None:
        set_database_path(DEFAULT_DB_PATH)
    Base.metadata.create_all(bind=engine)


# Initialize with default path on import
set_database_path(DEFAULT_DB_PATH)
