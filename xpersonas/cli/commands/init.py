"""Init command: setup database and first tenant."""

from __future__ import annotations

import typer

app = typer.Typer(help="Initialize xpersonas database")


@app.command()
def setup(db: str = "xpersonas.db", tenant_name: str = "Default"):
    """Setup database and create first tenant."""
    from xpersonas.storage.database import Database
    from xpersonas.storage.repositories.tenant_repo import TenantRepo

    db_obj = Database(db)
    db_obj.connect()
    db_obj.initialize()

    repo = TenantRepo(db_obj)
    existing = repo.list_all()
    if existing:
        typer.echo(f"Database already initialized with {len(existing)} tenant(s).")
        return

    tenant = repo.create(tenant_name, "brand")
    typer.echo(f"Created tenant: {tenant['name']} ({tenant['id']})")
    typer.echo(f"Database: {db}")
    db_obj.close()
