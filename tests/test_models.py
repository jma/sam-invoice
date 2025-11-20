import pytest
from sqlalchemy.exc import IntegrityError

import sam_invoice.models.crud_customer as crud


def test_create_and_query_customer(in_memory_db):
    """Create a customer and verify it can be queried back via the CRUD API.

    This test ensures `create_customer` assigns an ID and `get_customers`
    returns the newly created entry (checked by email).
    """
    cust = crud.create_customer("Dupont", "1 rue du Vin", "dupont@example.com")
    assert cust.id is not None
    assert cust.name == "Dupont"
    customers = crud.get_customers()
    # ensure at least one customer with our email exists
    assert any(c.email == "dupont@example.com" for c in customers)


def test_search_customers(in_memory_db):
    """Verify `search_customers` finds customers by id, name, email and address.

    The test creates several customers then checks that an empty query
    returns all records and that partial and case-insensitive matches
    work for name, email and address. It also verifies exact id match.
    """
    # create several customers
    dupont = crud.create_customer("Dupont", "1 rue du Vin", "dupont@example.com")
    crud.create_customer("Martin", "2 avenue des Vignes", "martin@wine.com")
    crud.create_customer("Alice", "Chez Alice", "alice@domain.com")

    # empty query returns all customers sorted case-insensitively
    all_res = crud.search_customers("")
    names = [c.name for c in all_res]
    assert [n.lower() for n in names] == sorted([n.lower() for n in names])

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


def test_get_customers_sorted(in_memory_db):
    """`get_customers` returns customers ordered by name case-insensitively."""
    # create several customers in arbitrary order
    crud.create_customer("dupont", "1 rue du Vin", "dupont@example.com")
    crud.create_customer("Martin", "2 avenue des Vignes", "martin@wine.com")
    crud.create_customer("Alice", "Chez Alice", "alice@domain.com")

    customers = crud.get_customers()
    names = [c.name for c in customers]
    expected = sorted(names, key=lambda s: s.lower())
    assert [n.lower() for n in names] == [n.lower() for n in expected]


def test_search_customers_sorted(in_memory_db):
    """`search_customers` returns ordered results for empty and partial queries."""
    # create several customers
    crud.create_customer("zeta", "Addr 1", "z@example.com")
    crud.create_customer("Alpha", "Addr 2", "a@example.com")
    crud.create_customer("beta", "Addr 3", "b@example.com")

    # empty search should return ordered by name
    res = crud.search_customers("")
    names = [c.name for c in res]
    assert [n.lower() for n in names] == sorted([n.lower() for n in names])

    # partial search (matches multiple) should also be ordered
    res2 = crud.search_customers("a")
    names2 = [c.name for c in res2]
    assert [n.lower() for n in names2] == sorted([n.lower() for n in names2])


def test_db_constraints_empty_name(in_memory_db):
    """Creating a customer with an empty name should violate DB constraints."""
    with pytest.raises(IntegrityError):
        crud.create_customer("", "Some address", "noone@example.com")


def test_db_constraints_empty_address(in_memory_db):
    """Creating a customer with an empty address should violate DB constraints."""
    with pytest.raises(IntegrityError):
        crud.create_customer("Nobody", "", "nobody@example.com")


def test_db_constraints_short_name(in_memory_db):
    """Creating a customer with a name shorter than 3 chars should fail."""
    with pytest.raises(IntegrityError):
        crud.create_customer("Al", "Some address", "al@example.com")


def test_db_constraints_short_address(in_memory_db):
    """Creating a customer with an address shorter than 3 chars should fail."""
    with pytest.raises(IntegrityError):
        crud.create_customer("Valid Name", "A1", "valid@example.com")
