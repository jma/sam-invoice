from types import SimpleNamespace

from typer.testing import CliRunner

import sam_invoice.cli as cli_module

runner = CliRunner()


def test_db_load_fixtures_monkeypatch(monkeypatch):
    """Verify `db load-fixtures` iterates the fixtures and calls create_customer.

    We monkeypatch `create_customer` to avoid touching the DB and capture calls.
    """
    calls = []

    def fake_create_customer(name: str, address: str, email: str):
        idx = len(calls) + 1
        calls.append((name, address, email))
        return SimpleNamespace(id=idx, name=name)

    # monkeypatch the create_customer used by the CLI
    monkeypatch.setattr("sam_invoice.models.crud_customer.create_customer", fake_create_customer)

    # run the CLI (uses default fixtures file in project)
    result = runner.invoke(cli_module.app, ["db", "load-fixtures"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    # ensure the final summary mentions the number loaded
    assert f"Loaded {len(calls)} customers" in result.output
    # check we loaded the expected number from fixtures (10)
    assert len(calls) == 10


def test_db_init_calls_initdb(monkeypatch):
    """Verify `db init` calls the CLI's imported `init_db` function."""
    called = {"count": 0}

    def fake_init_db():
        called["count"] += 1

    # monkeypatch the init_db function used by the CLI
    monkeypatch.setattr(cli_module, "init_db", fake_init_db)

    result = runner.invoke(cli_module.app, ["db", "init"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert called["count"] == 1
