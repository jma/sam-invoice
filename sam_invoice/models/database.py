import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .customer import Base

DATABASE_URL = "sqlite:///sam_invoice.db"

# disable SQL echoing and reduce SQLAlchemy engine logging noise
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

# Set SQLAlchemy engine logger to WARNING to avoid INFO noise in output
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def init_db():
    Base.metadata.create_all(bind=engine)
