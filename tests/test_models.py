import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sam_invoice.models.crud_customer as crud
import sam_invoice.models.database as database
from sam_invoice.models.customer import Base


@pytest.fixture
def in_memory_db(monkeypatch):
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


def test_create_and_query_customer(in_memory_db):
    cust = crud.create_customer("Dupont", "1 rue du Vin", "dupont@example.com")
    assert cust.id is not None
    assert cust.name == "Dupont"
    customers = crud.get_customers()
    # ensure at least one customer with our email exists
    assert any(c.email == "dupont@example.com" for c in customers)


def test_search_customers(in_memory_db):
    # create several customers
    dupont = crud.create_customer("Dupont", "1 rue du Vin", "dupont@example.com")
    crud.create_customer("Martin", "2 avenue des Vignes", "martin@wine.com")
    crud.create_customer("Alice", "Chez Alice", "alice@domain.com")

    # empty query returns all
    all_res = crud.search_customers("")
    assert len(all_res) >= 3

    # search by exact id (string)
    res_id = crud.search_customers(str(dupont.id))
    assert any(r.id == dupont.id for r in res_id)

    # partial name (case-insensitive)
    res_name = crud.search_customers("mart")
    assert any("martin" in r.name.lower() for r in res_name)

    # partial email case-insensitive
    res_email = crud.search_customers("WINE")
    assert any("wine" in r.email.lower() for r in res_email)

    # partial address
    res_addr = crud.search_customers("rue du")
    assert any("rue du" in r.address.lower() for r in res_addr)
