"""CRUD operations for customers."""

from sqlalchemy import func

from .base_crud import BaseCRUD
from .customer import Customer
from .database import SessionLocal


class CustomerCRUD(BaseCRUD[Customer]):
    """CRUD operations for Customer entities."""

    def __init__(self):
        super().__init__(Customer)

    def create(self, name: str, address: str, email: str) -> Customer:
        """Create a new customer.

        Args:
            name: Customer name
            address: Customer address
            email: Customer email

        Returns:
            The created customer
        """
        with SessionLocal() as session:
            customer = Customer(name=name, address=address, email=email)
            session.add(customer)
            session.commit()
            session.refresh(customer)
            return customer

    def update(self, customer_id: int, name: str = None, address: str = None, email: str = None) -> Customer | None:
        """Update an existing customer.

        Args:
            customer_id: The customer's ID
            name: New name (optional)
            address: New address (optional)
            email: New email (optional)

        Returns:
            The updated customer if found, None otherwise
        """
        with SessionLocal() as session:
            customer = session.query(Customer).filter(Customer.id == customer_id).first()
            if customer:
                if name is not None:
                    customer.name = name
                if address is not None:
                    customer.address = address
                if email is not None:
                    customer.email = email
                session.commit()
                session.refresh(customer)
            return customer

    def _get_search_filters(self, query: str) -> list:
        """Get search filters for customers.

        Searches in: name, email, address
        """
        return [
            Customer.name.ilike(f"%{query}%"),
            Customer.email.ilike(f"%{query}%"),
            Customer.address.ilike(f"%{query}%"),
        ]

    def _get_sort_field(self):
        """Sort customers by name (case-insensitive)."""
        return func.lower(Customer.name)


# Create singleton instance
customer_crud = CustomerCRUD()
