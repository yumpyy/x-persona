"""Agent lifecycle commands."""

from __future__ import annotations

import asyncio
import json

import typer

app = typer.Typer(help="Control agent instances")


@app.command()
def start(persona_id: str, visible: bool = False, ask: bool = False, db: str = "xpersonas.db"):
    """Start an agent for a persona."""
    from xpersonas.storage.database import Database
    from xpersonas.agent.runner import AgentRunner

    async def _run():
        with Database(db) as db_obj:
            db_obj.initialize()
            runner = AgentRunner(db_obj)
            instance = await runner.start_persona(persona_id, visible=visible, ask=ask)
            typer.echo(f"Started agent: {instance.persona_id} (strategy={instance.strategy})")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                typer.echo("\nStopping...")
                await runner.stop_all()

    asyncio.run(_run())


@app.command()
def stop(persona_id: str, db: str = "xpersonas.db"):
    """Stop an agent for a persona via DB status update."""
    from xpersonas.storage.database import Database

    with Database(db) as db_obj:
        db_obj.initialize()
        row = db_obj.fetchone(
            "SELECT id FROM agent_runs WHERE persona_id = ? AND status = 'running' "
            "ORDER BY started_at DESC LIMIT 1",
            (persona_id,),
        )
        if not row:
            typer.echo(f"No running agent found for persona {persona_id}")
            raise typer.Exit(1)
        db_obj.execute(
            "UPDATE agent_runs SET status = 'stopped', stopped_at = datetime('now') WHERE id = ?",
            (row["id"],),
        )
        db_obj.commit()
        typer.echo(f"Marked agent as stopped for persona {persona_id}")
        typer.echo("Note: If running in API server, use POST /api/v1/agents/stop/" + persona_id)


@app.command()
def status(db: str = "xpersonas.db"):
    """Show status of running agents from DB."""
    from xpersonas.storage.database import Database

    with Database(db) as db_obj:
        db_obj.initialize()
        rows = db_obj.fetchall(
            "SELECT ar.*, p.handle, p.display_name FROM agent_runs ar "
            "JOIN personas p ON ar.persona_id = p.id "
            "WHERE ar.status = 'running' ORDER BY ar.started_at DESC"
        )
        if not rows:
            typer.echo("No running agents.")
            return
        for r in rows:
            typer.echo(f"  @{r['handle']} ({r['display_name']}): {r['status']}: {r['cycles_completed']} cycles")


@app.command()
def once(persona_id: str, dry_run: bool = False, visible: bool = False, ask: bool = False, db: str = "xpersonas.db"):
    """Run a single agent cycle."""
    from xpersonas.storage.database import Database
    from xpersonas.storage.repositories.persona_repo import PersonaRepo
    from xpersonas.agent.graph import build_graph

    with Database(db) as db_obj:
        db_obj.initialize()
        repo = PersonaRepo(db_obj)
        persona = repo.get(persona_id)
        if not persona:
            all_personas = repo.list_all()
            if all_personas:
                typer.echo("Persona not found. Available personas:")
                for p in all_personas:
                    typer.echo(f"  {p['id']}  @{p['handle']}  ({p['display_name']})")
            else:
                typer.echo("Persona not found. No personas in database.")
                typer.echo("Create one: xpersonas persona create --help")
            raise typer.Exit(1)

        config = persona.get("persona_config", {})
        strategy = config.get("engagement", {}).get("strategy", "active")

        typer.echo(f"Persona: @{persona['handle']} (strategy={strategy})")
        graph = build_graph(strategy)
        node_names = list(graph.get_graph().nodes.keys())
        typer.echo(f"Graph built: {len(node_names)} nodes: {', '.join(node_names)}")

        if dry_run:
            typer.echo("Dry run: graph validated, skipping execution.")
            return

        from xpersonas.agent.runner import AgentRunner

        async def _run():
            runner = AgentRunner(db_obj)
            instance = await runner.start_persona(persona_id, visible=visible, ask=ask)
            typer.echo(f"Running single cycle for {persona_id}...")
            # Wait for one cycle
            await asyncio.sleep(10)
            await runner.stop_persona(persona_id)
            typer.echo(f"Done. Cycles: {instance.cycles}")

        asyncio.run(_run())
