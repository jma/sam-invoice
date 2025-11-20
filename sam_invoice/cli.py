import json
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

import sam_invoice.models.crud_customer as crud
from sam_invoice.models.database import init_db

console = Console()

app = typer.Typer()

# group for DB related commands
db_app = typer.Typer()
app.add_typer(db_app, name="db")


@db_app.command("init")
def initdb():
    """Initialize the SQLite database."""
    init_db()
    typer.echo("Database initialized.")


@db_app.command("load-fixtures")
def load_fixtures(path: Path = None, verbose: bool = True):
    """Load customers from a JSON fixtures file into the database.

    Default fixtures file is `fixtures/customers.json` at the project root.
    """
    if path is None:
        # resolve project root relative to this file (sam_invoice package)
        pkg_dir = Path(__file__).resolve().parent.parent
        path = pkg_dir / "fixtures" / "customers.json"

    if not path.exists():
        typer.echo(f"Fixtures file not found: {path}")
        raise typer.Exit(code=1)

    # ensure DB exists
    init_db()

    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    created = 0
    # use a progress bar
    with Progress(
        TextColumn("{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Importing customers", total=len(data))
        for item in data:
            name = item.get("name")
            address = item.get("address")
            email = item.get("email")
            # naive create - no duplicate check
            cust = crud.create_customer(name=name, address=address, email=email)
            if cust:
                created += 1
                progress.advance(task)
                if verbose:
                    console.print(f"Created customer {cust.id} - {cust.name}")

    console.print(f"Loaded {created} customers from {path}", style="green")


def main():
    app()


if __name__ == "__main__":
    main()
