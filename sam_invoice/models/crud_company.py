"""CRUD operations for company information."""

from sam_invoice.models.company import Company
from sam_invoice.models.database import SessionLocal


def get_company():
    """Get company information (returns first record or None)."""
    with SessionLocal() as session:
        return session.query(Company).first()


def create_or_update_company(name: str, address: str = None, email: str = None, phone: str = None, logo: bytes = None):
    """Create or update company information.

    Args:
        name: Company name
        address: Company address
        email: Contact email
        phone: Contact phone
        logo: Logo as binary data

    Returns:
        Company: The created or updated company record
    """
    with SessionLocal() as session:
        company = session.query(Company).first()

        if company:
            # Update existing
            company.name = name
            company.address = address
            company.email = email
            company.phone = phone
            if logo is not None:
                company.logo = logo
        else:
            # Create new
            company = Company(name=name, address=address, email=email, phone=phone, logo=logo)
            session.add(company)

        session.commit()
        session.refresh(company)
        return company


def get_company_logo():
    """Get company logo as binary data."""
    company = get_company()
    if company and company.logo:
        return company.logo
    return None
