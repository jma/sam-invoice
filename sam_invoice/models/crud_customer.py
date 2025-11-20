from sqlalchemy import func, or_

from . import database
from .customer import Customer


def create_customer(name: str, address: str, email: str):
    session = database.SessionLocal()
    customer = Customer(name=name, address=address, email=email)
    session.add(customer)
    session.commit()
    session.refresh(customer)
    session.close()
    return customer


def get_customers():
    session = database.SessionLocal()
    # order by name case-insensitively
    customers = session.query(Customer).order_by(func.lower(Customer.name)).all()
    session.close()
    return customers


def search_customers(query: str):
    """Search customers by id (exact) or by partial match on name, address, email (case-insensitive).

    Returns a list of Customer objects.
    """
    session = database.SessionLocal()
    q = (query or "").strip()
    if not q:
        # return ordered by name
        customers = session.query(Customer).order_by(func.lower(Customer.name)).all()
        session.close()
        return customers

    # try numeric id match
    customers = []
    try:
        id_val = int(q)
        stmt = (
            session.query(Customer)
            .filter(
                or_(
                    Customer.id == id_val,
                    Customer.name.ilike(f"%{q}%"),
                    Customer.email.ilike(f"%{q}%"),
                    Customer.address.ilike(f"%{q}%"),
                )
            )
            .order_by(func.lower(Customer.name))
        )
    except ValueError:
        stmt = (
            session.query(Customer)
            .filter(
                or_(
                    Customer.name.ilike(f"%{q}%"),
                    Customer.email.ilike(f"%{q}%"),
                    Customer.address.ilike(f"%{q}%"),
                )
            )
            .order_by(func.lower(Customer.name))
        )

    customers = stmt.all()
    session.close()
    return customers


def get_customer_by_id(customer_id: int):
    session = database.SessionLocal()
    customer = session.query(Customer).filter(Customer.id == customer_id).first()
    session.close()
    return customer


def update_customer(customer_id: int, name: str = None, address: str = None, email: str = None):
    session = database.SessionLocal()
    customer = session.query(Customer).filter(Customer.id == customer_id).first()
    if customer:
        if name:
            customer.name = name
        if address:
            customer.address = address
        if email:
            customer.email = email
        session.commit()
        session.refresh(customer)
    session.close()
    return customer


def delete_customer(customer_id: int):
    session = database.SessionLocal()
    customer = session.query(Customer).filter(Customer.id == customer_id).first()
    if customer:
        session.delete(customer)
        session.commit()
    session.close()
    return customer
