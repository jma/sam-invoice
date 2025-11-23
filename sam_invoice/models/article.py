"""Data model for articles."""

from sqlalchemy import Column, Float, Integer, String

from .customer import Base


class Article(Base):
    """Article model with reference, name, price, stock and sold quantity."""

    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    reference = Column(String, nullable=False)  # Unique article reference
    name = Column(String)  # Article name/description
    price = Column(Float)  # Unit price
    stock = Column(Integer)  # Quantity in stock
    sold = Column(Integer)  # Quantity sold
