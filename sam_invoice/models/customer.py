from sqlalchemy import CheckConstraint, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        CheckConstraint("length(name) >= 3", name="ck_customers_name_minlen"),
        CheckConstraint("length(address) >= 3", name="ck_customers_address_minlen"),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    email = Column(String)
