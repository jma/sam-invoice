"""Data model for company information."""

from sqlalchemy import Column, Integer, LargeBinary, String

from .customer import Base


class Company(Base):
    """Company model with name, address and logo.

    Stores information about the company issuing invoices.
    Only one company record should exist in the database.
    """

    __tablename__ = "company"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # Company name
    address = Column(String)  # Company address
    email = Column(String)  # Contact email
    phone = Column(String)  # Contact phone
    logo = Column(LargeBinary)  # Company logo as binary data
