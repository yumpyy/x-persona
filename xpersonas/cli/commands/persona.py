"""Persona management commands."""

from __future__ import annotations

import json
from pathlib import Path

import typer

app = typer.Typer(help="Manage personas")


@app.command()
def create(
    handle: str,
    display_name: str = "",
    platform: str = "x",
    strategy: str = "active",
    db: str = "xpersonas.db",
):
    """Create a persona interactively."""
    from xpersonas.storage.database import Database
    from xpersonas.storage.repositories.persona_repo import PersonaRepo

    if not display_name:
        display_name = handle

    config = {
        "identity": {"handle": handle, "display_name": display_name},
        "engagement": {"strategy": strategy},
    }

    with Database(db) as db_obj:
        db_obj.initialize()
        tenants = db_obj.fetchall("SELECT id FROM tenants WHERE is_active = 1 LIMIT 1")
        if not tenants:
            typer.echo("No tenant found. Run: xpersonas init setup")
            raise typer.Exit(1)

        repo = PersonaRepo(db_obj)
        persona = repo.create(tenants[0]["id"], platform, handle, display_name, config)
        typer.echo(f"Created persona: @{handle} ({persona['id']})")
        typer.echo(f"Strategy: {strategy}")


@app.command()
def list(db: str = "xpersonas.db"):
    """List all personas."""
    from xpersonas.storage.database import Database
    from xpersonas.storage.repositories.persona_repo import PersonaRepo

    with Database(db) as db_obj:
        db_obj.initialize()
        tenants = db_obj.fetchall("SELECT id FROM tenants WHERE is_active = 1")
        repo = PersonaRepo(db_obj)
        for t in tenants:
            for p in repo.list_for_tenant(t["id"]):
                strategy = p.get("persona_config", {}).get("engagement", {}).get("strategy", "?")
                typer.echo(f"  {p['id']}  @{p['handle']}  platform={p['platform']}  strategy={strategy}")


@app.command()
def import_config(file: str, db: str = "xpersonas.db"):
    """Import a persona from a JSON file."""
    from xpersonas.core.persona import validate_persona_config
    from xpersonas.storage.database import Database
    from xpersonas.storage.repositories.persona_repo import PersonaRepo

    data = json.loads(Path(file).read_text())
    errors = validate_persona_config(data)
    if errors:
        typer.echo(f"Validation errors:\n{errors[0]}")
        raise typer.Exit(1)

    with Database(db) as db_obj:
        db_obj.initialize()
        tenants = db_obj.fetchall("SELECT id FROM tenants WHERE is_active = 1 LIMIT 1")
        if not tenants:
            typer.echo("No tenant found. Run: xpersonas init setup")
            raise typer.Exit(1)

        identity = data.get("identity", {})
        repo = PersonaRepo(db_obj)
        persona = repo.create(
            tenants[0]["id"],
            data.get("platforms", {}).keys().__iter__().__next__() if data.get("platforms") else "x",
            identity.get("handle", "unknown"),
            identity.get("display_name", ""),
            data,
        )
        typer.echo(f"Imported persona: @{identity.get('handle')} ({persona['id']})")


@app.command()
def export(persona_id: str, output: str = "", db: str = "xpersonas.db"):
    """Export a persona as JSON."""
    from xpersonas.storage.database import Database
    from xpersonas.storage.repositories.persona_repo import PersonaRepo

    with Database(db) as db_obj:
        db_obj.initialize()
        repo = PersonaRepo(db_obj)
        persona = repo.get(persona_id)
        if not persona:
            typer.echo("Persona not found.")
            raise typer.Exit(1)

        out = output or f"{persona['handle']}-export.json"
        Path(out).write_text(json.dumps(persona["persona_config"], indent=2))
        typer.echo(f"Exported to {out}")
