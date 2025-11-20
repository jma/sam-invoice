import sam_invoice.ui.customers_view as cv


def test_validate_empty_name():
    valid, msg = cv.validate_customer_fields("", "Some address")
    assert not valid
    assert msg is not None and "Name" in msg


def test_validate_empty_address():
    valid, msg = cv.validate_customer_fields("Bob", "")
    assert not valid
    assert msg is not None and "Address" in msg


def test_validate_ok():
    valid, msg = cv.validate_customer_fields("Bob", "1 Wine St")
    assert valid
    assert msg is None

    # New validation tests for minimum length


def test_validate_short_name():
    valid, msg = cv.validate_customer_fields("Al", "Some address")
    assert not valid
    assert msg is not None and "at least 3" in msg


def test_validate_short_address():
    valid, msg = cv.validate_customer_fields("Bob", "A1")
    assert not valid
    assert msg is not None and "at least 3" in msg
