"""FastAPI application server."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager

from xpersonas.api.deps import init_db, get_db
from xpersonas.api.routers import tenants, personas, agents, activity, health, products, contacts, escalations


def create_app(db_path: str = "xpersonas.db") -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        db = init_db(db_path)
        from xpersonas.agent.runner import AgentRunner
        runner = AgentRunner(db)
        from xpersonas.api.routers.agents import set_runner
        set_runner(runner)
        yield
        await runner.stop_all()

    app = FastAPI(
        title="xpersonas",
        description="Autonomous social media persona platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(tenants.router, prefix="/api/v1")
    app.include_router(personas.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(activity.router, prefix="/api/v1")
    app.include_router(products.router, prefix="/api/v1")
    app.include_router(contacts.router, prefix="/api/v1")
    app.include_router(escalations.router, prefix="/api/v1")

    return app


app = create_app()


def run(host: str = "0.0.0.0", port: int = 8000):
    uvicorn.run(app, host=host, port=port)
