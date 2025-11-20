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
