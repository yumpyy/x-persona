"""Multi-persona agent runner: async task manager."""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone

from xpersonas.agent.graph import build_graph
from xpersonas.core.config import LLMConfig, load_env_config, resolve_llm_config
from xpersonas.core.models import AuthConfig
from xpersonas.platforms.base import PlatformAdapter
from xpersonas.platforms.registry import get_adapter
from xpersonas.storage.database import Database
from xpersonas.storage.repositories.activity_repo import ActivityRepo
from xpersonas.storage.repositories.persona_repo import PersonaRepo


@dataclass
class AgentInstance:
    persona_id: str
    tenant_id: str
    platform: str
    strategy: str
    status: str = "stopped"
    cycles: int = 0
    started_at: str | None = None
    last_cycle_at: str | None = None
    error_message: str | None = None


class AgentRunner:
    """Manages the lifecycle of agent instances.

    Each persona runs as an independent asyncio task.
    Browser sessions are isolated per persona.
    """

    def __init__(self, db: Database, max_concurrent: int = 5):
        self.db = db
        self.max_concurrent = max_concurrent
        self.instances: dict[str, AgentInstance] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._adapters: dict[str, PlatformAdapter] = {}

    async def start_persona(self, persona_id: str, visible: bool = False, ask: bool = False) -> AgentInstance:
        if persona_id in self._tasks and not self._tasks[persona_id].done():
            raise RuntimeError(f"Persona {persona_id} is already running")

        persona_repo = PersonaRepo(self.db)
        persona = persona_repo.get(persona_id)
        if not persona:
            # List available personas for helpful error
            all_personas = persona_repo.list_all()
            available = ", ".join(f"{p['id']} (@{p['handle']})" for p in all_personas) if all_personas else "none"
            raise ValueError(
                f"Persona '{persona_id}' not found.\n"
                f"  Available personas: {available}\n"
                f"  Create one: xpersonas persona create --help"
            )

        tenant_id = persona["tenant_id"]
        platform = persona["platform"]
        config = persona.get("persona_config", {})
        strategy = config.get("engagement", {}).get("strategy", "active")

        instance = AgentInstance(
            persona_id=persona_id,
            tenant_id=tenant_id,
            platform=platform,
            strategy=strategy,
            status="starting",
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self.instances[persona_id] = instance

        task = asyncio.create_task(
            self._run_loop(instance, persona, config, visible, ask)
        )
        self._tasks[persona_id] = task
        return instance

    async def _run_loop(
        self,
        instance: AgentInstance,
        persona: dict,
        config: dict,
        visible: bool,
        ask: bool,
    ):
        adapter = get_adapter(instance.platform)
        self._adapters[instance.persona_id] = adapter

        await self._semaphore.acquire()
        try:
            instance.status = "running"

            # Initialize adapter
            auth_config = AuthConfig(
                session_path=persona.get("auth_state_path", "auth.json"),
            )
            await adapter.initialize(auth_config, visible=visible)

            # Navigate home
            await adapter.navigate_home()

            # Build graph
            graph = build_graph(instance.strategy)

            # Load engaged IDs
            activity_repo = ActivityRepo(self.db)
            engaged_ids = activity_repo.get_engaged_ids(instance.persona_id)

            # Load writing samples
            source_samples = []
            for path in config.get("source_data", []):
                try:
                    from pathlib import Path
                    p = Path(path)
                    if p.exists():
                        source_samples.append(p.read_text()[:2000])
                except Exception:
                    pass

            # Resolve LLM config
            env_config = load_env_config()
            llm_config = {
                "model": env_config.model,
                "api_key": env_config.api_key,
                "base_url": env_config.base_url,
            }

            state = {
                "persona_id": instance.persona_id,
                "tenant_id": instance.tenant_id,
                "platform": instance.platform,
                "mode": config.get("mode", "brand"),
                "persona_config": config,
                "source_data_samples": source_samples,
                "llm_config": llm_config,
                "engaged_ids": engaged_ids,
                "seen_ids": [],
                "scroll_count": 0,
                "follows_this_session": 0,
                "pending_actions": [],
                "executed_actions": [],
                "cycle_action_counts": {},
                "thread_contexts": {},
            }

            graph_config = {
                "configurable": {
                    "adapter": adapter,
                    "db": self.db,
                    "persona_id": instance.persona_id,
                    "ask": ask,
                }
            }

            cycle = 0
            while True:
                cycle += 1
                try:
                    result = await graph.ainvoke(state, graph_config)
                    state.update(result)
                except Exception as e:
                    instance.error_message = str(e)
                    continue

                instance.cycles = cycle
                instance.last_cycle_at = datetime.now(timezone.utc).isoformat()
                instance.status = "running"

                # Break logic
                scroll_limit = config.get("scroll_limit", 2500)
                if scroll_limit > 0 and state.get("scroll_count", 0) >= scroll_limit:
                    break_duration = random.randint(600, 1800)
                    instance.status = f"on_break ({break_duration}s)"
                    await asyncio.sleep(break_duration)
                    await adapter.navigate_home()
                    state["scroll_count"] = 0
                    state["engaged_ids"] = activity_repo.get_engaged_ids(instance.persona_id)
                    state["seen_ids"] = []

                # Delay between cycles
                await asyncio.sleep(random.uniform(2.0, 5.0))

        except asyncio.CancelledError:
            instance.status = "stopped"
        except Exception as e:
            instance.status = "error"
            instance.error_message = str(e)
        finally:
            try:
                await adapter.shutdown()
            except Exception:
                pass
            self._adapters.pop(instance.persona_id, None)
            self._semaphore.release()

    async def stop_persona(self, persona_id: str) -> None:
        if persona_id in self._tasks:
            self._tasks[persona_id].cancel()
            try:
                await self._tasks[persona_id]
            except asyncio.CancelledError:
                pass
            del self._tasks[persona_id]
        if persona_id in self.instances:
            self.instances[persona_id].status = "stopped"

    async def stop_all(self) -> None:
        for pid in list(self.instances.keys()):
            await self.stop_persona(pid)
