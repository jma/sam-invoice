"""Command line interface for Sam Invoice."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from sam_invoice.models.crud_customer import customer_crud
from sam_invoice.models.crud_product import product_crud
from sam_invoice.models.database import init_db, set_database_path

console = Console()
app = typer.Typer()

# Database commands group
db_app = typer.Typer()
app.add_typer(db_app, name="db")

# Fixtures commands group
fixtures_app = typer.Typer()
app.add_typer(fixtures_app, name="fixtures")


@db_app.command("init")
def initdb(db_path: Annotated[Path, typer.Option("--db", help="Path to database file")] = None):
    """Initialize the SQLite database."""
    if db_path:
        set_database_path(db_path)
    init_db()
    typer.echo("Database initialized.")


@fixtures_app.command("load-customers")
def load_customers(
    path: Annotated[Path, typer.Argument(help="Path to customers JSON file")] = None,
    db_path: Annotated[Path, typer.Option("--db", help="Path to database file")] = None,
    verbose: bool = True,
):
    """Load customers from a JSON fixtures file into the database.

    Default file: `fixtures/customers.json` at project root.
    """
    # Set database path if provided
    if db_path:
        set_database_path(db_path)

    # Determine fixtures file path
    if path is None:
        pkg_dir = Path(__file__).resolve().parent.parent
        path = pkg_dir / "fixtures" / "customers.json"

    if not path.exists():
        typer.echo(f"Fixtures file not found: {path}")
        raise typer.Exit(code=1)

    # Ensure DB exists
    init_db()

    # Load JSON data
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    # Import with progress bar
    created = 0
    errors = 0
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

            try:
                # Create customer (no duplicate check)
                cust = customer_crud.create(name=name, address=address, email=email)
                if cust:
                    created += 1
                    progress.advance(task)
                    if verbose:
                        console.print(f"Created customer {cust.id} - {cust.name}")
                else:
                    progress.advance(task)
            except Exception as e:
                errors += 1
                progress.advance(task)
                console.print(f"[yellow]Warning: Failed to create customer '{name}': {e}[/yellow]")

    if errors > 0:
        console.print(f"Loaded {created} customers from {path} ({errors} errors)", style="yellow")
    else:
        console.print(f"Loaded {created} customers from {path}", style="green")


@fixtures_app.command("load-products")
def load_products(
    path: Annotated[Path, typer.Argument(help="Path to products JSON file")] = None,
    db_path: Annotated[Path, typer.Option("--db", help="Path to database file")] = None,
    verbose: bool = True,
):
    """Load products from a JSON fixtures file into the database.

    Default file: `fixtures/products.json` at project root.
    """
    # Set database path if provided
    if db_path:
        set_database_path(db_path)

    # Determine fixtures file path
    if path is None:
        pkg_dir = Path(__file__).resolve().parent.parent
        path = pkg_dir / "fixtures" / "products.json"

    if not path.exists():
        typer.echo(f"Fixtures file not found: {path}")
        raise typer.Exit(code=1)

    # Ensure DB exists
    init_db()

    # Load JSON data
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    # Import with progress bar
    created = 0
    errors = 0
    with Progress(
        TextColumn("{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Importing products", total=len(data))

        for item in data:
            reference = item.get("reference")
            name = item.get("name")
            price = item.get("price", 0.0)
            stock = item.get("stock", 0)
            sold = item.get("sold", 0)

            try:
                # Create product (no duplicate check)
                product = product_crud.create(reference=reference, name=name, price=price, stock=stock, sold=sold)
                if product:
                    created += 1
                    progress.advance(task)
                    if verbose:
                        console.print(f"Created product {product.id} - {product.reference}")
                else:
                    progress.advance(task)
            except Exception as e:
                errors += 1
                progress.advance(task)
                console.print(f"[yellow]Warning: Failed to create product '{reference}': {e}[/yellow]")

    if errors > 0:
        console.print(f"Loaded {created} products from {path} ({errors} errors)", style="yellow")
    else:
        console.print(f"Loaded {created} products from {path}", style="green")


def main():
    app()


if __name__ == "__main__":
    main()
