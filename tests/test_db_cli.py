from typer.testing import CliRunner

import sam_invoice.cli as cli_module

runner = CliRunner()


def test_db_init_calls_initdb(monkeypatch):
    called = {"count": 0}

    def fake_init_db():
        called["count"] += 1

    # monkeypatch the init_db function used by the CLI
    monkeypatch.setattr(cli_module, "init_db", fake_init_db)

    result = runner.invoke(cli_module.app, ["db", "init"], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    assert called["count"] == 1
