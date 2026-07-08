"""Tenant management commands."""

from __future__ import annotations

import json

import typer

app = typer.Typer(help="Manage tenants")


@app.command()
def create(name: str, mode: str = "brand", db: str = "xpersonas.db"):
    """Create a new tenant."""
    from xpersonas.storage.database import Database
    from xpersonas.storage.repositories.tenant_repo import TenantRepo

    with Database(db) as db_obj:
        db_obj.initialize()
        repo = TenantRepo(db_obj)
        tenant = repo.create(name, mode)
        typer.echo(f"Created tenant: {tenant['name']} ({tenant['id']})")


@app.command()
def list(db: str = "xpersonas.db"):
    """List all tenants."""
    from xpersonas.storage.database import Database
    from xpersonas.storage.repositories.tenant_repo import TenantRepo

    with Database(db) as db_obj:
        db_obj.initialize()
        repo = TenantRepo(db_obj)
        tenants = repo.list_all()
        if not tenants:
            typer.echo("No tenants found.")
            return
        for t in tenants:
            typer.echo(f"  {t['id']}  {t['name']}  mode={t['mode']}")
