import pytest
from sqlalchemy.exc import IntegrityError

from sam_invoice.models.crud_customer import customer_crud
from sam_invoice.models.crud_product import product_crud

# === Tests CRUD Customer ===


def test_create_and_query_customer(in_memory_db):
    """Create a customer and verify it can be queried back via the CRUD API.

    This test ensures `create_customer` assigns an ID and `get_customers`
    returns the newly created entry (checked by email).
    """
    cust = customer_crud.create("Dupont", "1 rue du Vin", "dupont@example.com")
    assert cust.id is not None
    assert cust.name == "Dupont"
    customers = customer_crud.get_all()
    # ensure at least one customer with our email exists
    assert any(c.email == "dupont@example.com" for c in customers)


def test_search_customers(in_memory_db):
    """Verify `search_customers` finds customers by id, name, email and address.

    The test creates several customers then checks that an empty query
    returns all records and that partial and case-insensitive matches
    work for name, email and address. It also verifies exact id match.
    """
    # create several customers
    dupont = customer_crud.create("Dupont", "1 rue du Vin", "dupont@example.com")
    customer_crud.create("Martin", "2 avenue des Vignes", "martin@wine.com")
    customer_crud.create("Alice", "Chez Alice", "alice@domain.com")

    # empty query returns all customers sorted case-insensitively
    all_res = customer_crud.search("")
    names = [c.name for c in all_res]
    assert [n.lower() for n in names] == sorted([n.lower() for n in names])

    # search by exact id (string)
    res_id = customer_crud.search(str(dupont.id))
    assert any(r.id == dupont.id for r in res_id)

    # partial name (case-insensitive)
    res_name = customer_crud.search("mart")
    assert any("martin" in r.name.lower() for r in res_name)

    # partial email case-insensitive
    res_email = customer_crud.search("WINE")
    assert any("wine" in r.email.lower() for r in res_email)

    # partial address
    res_addr = customer_crud.search("rue du")
    assert any("rue du" in r.address.lower() for r in res_addr)


def test_get_customers_sorted(in_memory_db):
    """`get_customers` returns customers ordered by name case-insensitively."""
    # create several customers in arbitrary order
    customer_crud.create("dupont", "1 rue du Vin", "dupont@example.com")
    customer_crud.create("Martin", "2 avenue des Vignes", "martin@wine.com")
    customer_crud.create("Alice", "Chez Alice", "alice@domain.com")

    customers = customer_crud.get_all()
    names = [c.name for c in customers]
    expected = sorted(names, key=lambda s: s.lower())
    assert [n.lower() for n in names] == [n.lower() for n in expected]


def test_search_customers_sorted(in_memory_db):
    """`search_customers` returns ordered results for empty and partial queries."""
    # create several customers
    customer_crud.create("zeta", "Addr 1", "z@example.com")
    customer_crud.create("Alpha", "Addr 2", "a@example.com")
    customer_crud.create("beta", "Addr 3", "b@example.com")

    # empty search should return ordered by name
    res = customer_crud.search("")
    names = [c.name for c in res]
    assert [n.lower() for n in names] == sorted([n.lower() for n in names])

    # partial search (matches multiple) should also be ordered
    res2 = customer_crud.search("a")
    names2 = [c.name for c in res2]
    assert [n.lower() for n in names2] == sorted([n.lower() for n in names2])


def test_db_constraints_empty_name(in_memory_db):
    """Creating a customer with an empty name should violate DB constraints."""
    with pytest.raises(IntegrityError):
        customer_crud.create("", "Some address", "noone@example.com")


def test_db_constraints_empty_address(in_memory_db):
    """Creating a customer with an empty address should violate DB constraints."""
    with pytest.raises(IntegrityError):
        customer_crud.create("Nobody", "", "nobody@example.com")


def test_db_constraints_short_name(in_memory_db):
    """Creating a customer with a name shorter than 3 chars should fail."""
    with pytest.raises(IntegrityError):
        customer_crud.create("Al", "Some address", "al@example.com")


def test_db_constraints_short_address(in_memory_db):
    """Creating a customer with an address shorter than 3 chars should fail."""
    with pytest.raises(IntegrityError):
        customer_crud.create("Valid Name", "A1", "valid@example.com")


# === Tests CRUD Product ===


def test_create_and_query_article(in_memory_db):
    """Create a product and verify it can be queried back via the CRUD API."""
    art = product_crud.create("ART-001", "Test Article", price=25.50, stock=10, sold=5)
    assert art.id is not None
    assert art.reference == "ART-001"
    assert art.name == "Test Article"
    assert art.price == 25.50
    assert art.stock == 10
    assert art.sold == 5

    articles = product_crud.get_all()
    assert any(a.reference == "ART-001" for a in articles)


def test_search_products(in_memory_db):
    """Verify `search_products` finds products by id, ref and description."""
    # Create several products
    art1 = product_crud.create("VIN-001", "Château Margaux 2015", price=450.0, stock=24)
    product_crud.create("VIN-002", "Château Latour 2010", price=650.0, stock=18)
    product_crud.create("WINE-003", "Burgundy Special", price=85.0, stock=48)

    # Empty query returns all products
    all_res = product_crud.search("")
    assert len(all_res) >= 3

    # Search by exact id (string)
    res_id = product_crud.search(str(art1.id))
    assert any(r.id == art1.id for r in res_id)

    # Partial ref (case-insensitive)
    res_ref = product_crud.search("vin")
    assert len(res_ref) >= 2
    assert any("vin" in r.reference.lower() for r in res_ref)

    # Partial description
    res_desc = product_crud.search("château")
    assert len(res_desc) >= 2
    assert any("château" in r.name.lower() for r in res_desc)


def test_get_products_sorted(in_memory_db):
    """`get_products` returns products ordered by ref case-insensitively."""
    product_crud.create("Z-001", "Zinfandel", price=30.0)
    product_crud.create("a-002", "Alsace", price=25.0)
    product_crud.create("M-003", "Margaux", price=450.0)

    articles = product_crud.get_all()
    refs = [a.reference for a in articles]
    expected = sorted(refs, key=lambda s: s.lower())
    assert [r.lower() for r in refs] == [r.lower() for r in expected]


def test_search_products_sorted(in_memory_db):
    """`search_products` returns ordered results for empty and partial queries."""
    product_crud.create("Z-001", "Zinfandel", price=30.0)
    product_crud.create("A-002", "Alsace", price=25.0)
    product_crud.create("B-003", "Bordeaux", price=80.0)

    # Empty search should return ordered by ref
    res = product_crud.search("")
    refs = [a.reference for a in res]
    assert [r.lower() for r in refs] == sorted([r.lower() for r in refs])

    # Partial search should also be ordered
    res2 = product_crud.search("a")
    refs2 = [a.reference for a in res2]
    assert [r.lower() for r in refs2] == sorted([r.lower() for r in refs2])


def test_update_product(in_memory_db):
    """Verify updating a product modifies its fields correctly."""
    art = product_crud.create("TEST-001", "Original", price=10.0, stock=5, sold=2)
    assert art.name == "Original"

    updated = product_crud.update(art.id, name="Updated Description", price=15.0, stock=10)
    assert updated.name == "Updated Description"
    assert updated.price == 15.0
    assert updated.stock == 10
    assert updated.sold == 2  # Not updated


def test_delete_product(in_memory_db):
    """Verify deleting a product removes it from the database."""
    art = product_crud.create("DEL-001", "To Delete", price=20.0)
    art_id = art.id

    # Verify it exists
    found = product_crud.get_by_id(art_id)
    assert found is not None

    # Delete it
    product_crud.delete(art_id)

    # Verify it's gone
    found_after = product_crud.get_by_id(art_id)
    assert found_after is None
