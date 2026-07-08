"""Contact management commands (personal mode)."""

from __future__ import annotations

import typer

app = typer.Typer(help="Manage contacts and relationships")


@app.command()
def list(persona_id: str, stage: str = "", db: str = "xpersonas.db"):
    """List contacts for a persona."""
    from xpersonas.storage.database import Database

    with Database(db) as db_obj:
        db_obj.initialize()
        if stage:
            rows = db_obj.fetchall(
                "SELECT * FROM contacts WHERE persona_id = ? AND stage = ? ORDER BY rapport_score DESC",
                (persona_id, stage),
            )
        else:
            rows = db_obj.fetchall(
                "SELECT * FROM contacts WHERE persona_id = ? ORDER BY rapport_score DESC",
                (persona_id,),
            )
        if not rows:
            typer.echo("No contacts found.")
            return
        for r in rows:
            typer.echo(f"  @{r['handle']}  stage={r['stage']}  rapport={r['rapport_score']:.1f}  interactions={r['interaction_count']}")


@app.command()
def ready(persona_id: str, db: str = "xpersonas.db"):
    """Show contacts ready for direct connection."""
    from xpersonas.storage.database import Database

    with Database(db) as db_obj:
        db_obj.initialize()
        rows = db_obj.fetchall(
            "SELECT * FROM contacts WHERE persona_id = ? AND stage = 'connect_ready' ORDER BY rapport_score DESC",
            (persona_id,),
        )
        if not rows:
            typer.echo("No contacts ready for connection.")
            return
        for r in rows:
            typer.echo(f"  @{r['handle']}  rapport={r['rapport_score']:.1f}  interactions={r['interaction_count']}")
