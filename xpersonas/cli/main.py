"""xpersonas CLI: main entry point."""

from __future__ import annotations

import typer

from xpersonas.cli.commands import init, persona, agent, tenant, product, contact

app = typer.Typer(
    name="xpersonas",
    help="xpersonas: autonomous social media persona platform",
    no_args_is_help=True,
)

app.add_typer(init.app, name="init")
app.add_typer(tenant.app, name="tenant")
app.add_typer(persona.app, name="persona")
app.add_typer(agent.app, name="agent")
app.add_typer(product.app, name="product")
app.add_typer(contact.app, name="contact")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000, db: str = "xpersonas.db"):
    """Start the API server."""
    from xpersonas.api.server import create_app
    import uvicorn
    application = create_app(db)
    uvicorn.run(application, host=host, port=port)


if __name__ == "__main__":
    app()
