"""Product management commands (brand mode)."""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(help="Manage products for UGC seeding")


@app.command()
def create(
    name: str,
    description: str = "",
    pain_points: str = "",
    db: str = "xpersonas.db",
):
    """Add a product to the knowledge base."""
    from xpersonas.storage.database import Database

    with Database(db) as db_obj:
        db_obj.initialize()
        tenants = db_obj.fetchall("SELECT id FROM tenants WHERE is_active = 1 LIMIT 1")
        if not tenants:
            typer.echo("No tenant found.")
            raise typer.Exit(1)

        import uuid
        product_id = f"prod_{uuid.uuid4().hex[:12]}"
        pp = [p.strip() for p in pain_points.split(",") if p.strip()] if pain_points else []

        db_obj.execute(
            "INSERT INTO products (id, tenant_id, name, description, pain_points, created_at) "
            "VALUES (?, ?, ?, ?, ?, datetime('now'))",
            (product_id, tenants[0]["id"], name, description, json.dumps(pp)),
        )
        db_obj.commit()
        typer.echo(f"Created product: {name} ({product_id})")
        if pp:
            typer.echo(f"Pain points: {', '.join(pp)}")


@app.command()
def list(db: str = "xpersonas.db"):
    """List all products."""
    from xpersonas.storage.database import Database

    with Database(db) as db_obj:
        db_obj.initialize()
        rows = db_obj.fetchall("SELECT * FROM products WHERE is_active = 1")
        if not rows:
            typer.echo("No products found.")
            return
        for r in rows:
            pp = json.loads(r["pain_points"]) if r["pain_points"] else []
            typer.echo(f"  {r['id']}  {r['name']}  pain_points={pp}")
