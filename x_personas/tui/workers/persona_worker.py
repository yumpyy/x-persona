from __future__ import annotations

import asyncio
import os
import random
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class PersonaWorker:
    """Wraps a LangGraph agent lifecycle for one persona.

    Mirrors the logic in runner.py:run_perpetual() but channels logs
    into asyncio.Queues for the TUI to consume, and reports progress
    back through a callback.
    """

    def __init__(
        self,
        persona_info,
        settings,
        on_status,
        on_stats,
        on_error,
        on_ask=None,
    ) -> None:
        self.info = persona_info
        self.settings = settings
        self._on_status = on_status
        self._on_stats = on_stats
        self._on_error = on_error
        self._on_ask = on_ask

        self._running = False
        self._graph = None
        self._browser = None
        self._state: dict = {}
        self._command_queue: asyncio.Queue = asyncio.Queue()

        self._ask_response: bool = False
        self._ask_event: asyncio.Event = asyncio.Event()

    def _push_log(self, msg: str) -> None:
        self.info.log_queue.put_nowait(msg)

    def _push_error(self, msg: str) -> None:
        self.info.error_queue.put_nowait(msg)

    def _sink(self, msg: str) -> None:
        self._push_log(msg)

    def _error_sink(self, msg: str) -> None:
        self._push_error(msg)

    async def run(self) -> None:
        from x_personas.agent.graph import create_graph
        from x_personas.agent.log import add_sink, remove_sink, log
        from x_personas.agent.history import (
            load_engaged_status_ids,
            load_engagements_since_last_post,
        )
        from x_personas.agent.config import get_llm_config, get_vlm_config
        from x_personas.agent.nodes.load_persona import load_persona
        from x_personas.utils.browser import BrowserSession
        from x_personas.utils.feed import navigate_home

        add_sink(self._sink)

        self._running = True
        self._on_status("starting")

        try:
            llm_config = get_llm_config()
            vlm_config = get_vlm_config()

            auth_file = self.settings.auth_file
            if not auth_file:
                default_auth = str(self.info.persona_path.parent / "auth.json")
                if Path(default_auth).exists():
                    auth_file = default_auth
                elif Path("auth.json").exists():
                    auth_file = "auth.json"
                else:
                    auth_file = default_auth

            engaged_ids = list(load_engaged_status_ids(self.info.activity_log_file))
            log(f"Found {len(engaged_ids)} previously engaged posts")

            async with BrowserSession(
                headless=self.info.headless,
                executable_path=self.settings.browser_path,
                auth_state_path=auth_file,
            ) as ctx:
                home_page = ctx.pages[0] if ctx.pages else await ctx.new_page()
                await navigate_home(home_page)
                log(f"Navigated to x.com/home (headless={self.info.headless}, ask={self.info.ask})")

                graph = create_graph()
                config = {
                    "configurable": {
                        "thread_id": self.info.name,
                        "browser_context": ctx,
                        "home_page": home_page,
                        "llm_config": llm_config,
                        "vlm_config": vlm_config,
                        "ask": self.info.ask,
                    }
                }

                self._state = {
                    "persona_file": str(self.info.persona_path),
                    "activity_log_file": self.info.activity_log_file,
                    "rate_limit_file": self.info.rate_limit_file,
                    "llm_config": llm_config,
                    "vlm_config": vlm_config,
                    "thread_contexts": {},
                    "seen_post_ids": [],
                    "engaged_ids": engaged_ids,
                    "scroll_count": 0,
                }

                session_engagements = load_engagements_since_last_post(self.info.activity_log_file)
                target_original_post_count = random.randint(10, 20)
                log(f"Original post scheduler: {session_engagements} engagements since last post, target={target_original_post_count}")

                self._on_status("running")

                cycle = 0
                while self._running:
                    # Handle pending commands
                    while not self._command_queue.empty():
                        cmd = self._command_queue.get_nowait()
                        await self._handle_command(cmd, ctx, llm_config)
                    cycle += 1
                    self.info.cycle_count = cycle
                    log(f"cycle {cycle}")
                    result = await graph.ainvoke(self._state, config)
                    self._state.update(result)

                    sc = self._state.get("scroll_count", 0)
                    new_posts = result.get("feed_posts", [])
                    pending = result.get("pending_actions", [])
                    executed = result.get("executed_actions", [])
                    log(f"cycle {cycle}: scrolls={sc} new_posts={len(new_posts)} pending={len(pending)} executed={len(executed)}")

                    self.info.current_scroll = sc

                    successful = [a for a in executed if a.success]
                    if successful:
                        self.info.total_engagements += len(successful)
                        self.info.engagements_today += len(successful)
                        last = successful[-1]
                        self.info.last_action = f"{last.action.action_type.value} @{last.action.target_handle}"
                        self.info.last_action_time = last.timestamp or ""

                        session_engagements += len(successful)

                    # original post scheduler
                    if session_engagements >= target_original_post_count:
                        await self._try_original_post(ctx, llm_config)
                        session_engagements = 0
                        target_original_post_count = random.randint(10, 20)
                        log(f"Next original post target: {target_original_post_count}")

                    self._on_stats(self.info)

                    # break logic
                    scroll_limit = self.settings.scroll_limit
                    if scroll_limit > 0 and sc >= scroll_limit:
                        break_duration = random.randint(
                            max(60, self.settings.break_min),
                            max(120, self.settings.break_max),
                        )
                        log(f"Scroll limit ({scroll_limit}) reached. Break {break_duration}s...")
                        self._on_status("break")
                        await asyncio.sleep(break_duration)
                        await navigate_home(home_page)
                        log("Re-navigated to x.com/home")
                        self._state["scroll_count"] = 0
                        from x_personas.agent.history import load_engaged_status_ids
                        self._state["engaged_ids"] = list(load_engaged_status_ids(self.info.activity_log_file))
                        self._state["seen_post_ids"] = []
                        self._on_status("running")

        except asyncio.CancelledError:
            log("Worker cancelled")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self._on_error(f"{e}\n{tb}")
            self._on_status("error")
        finally:
            self._running = False
            remove_sink(self._sink)
            self._on_status("stopped")

    async def _try_original_post(self, ctx, llm_config) -> None:
        from x_personas.agent.nodes.generate_content import generate_original_post
        from x_personas.agent.history import load_recent_original_posts
        from x_personas.agent.log import log
        from x_personas.utils.post import post
        from datetime import datetime, timezone

        log("Composing original post...")
        try:
            hour = datetime.now().hour
            if 5 <= hour < 12:
                time_of_day = "Morning"
            elif 12 <= hour < 20:
                time_of_day = "Afternoon/Evening"
            else:
                time_of_day = "Late Night"

            recent_posts = load_recent_original_posts(self.info.activity_log_file, limit=5)

            tweet_text = await generate_original_post(
                self._state.get("persona_sections", {}),
                llm_config,
                time_of_day,
                recent_posts,
            )
            log(f"Generated: \"{tweet_text}\"")

            if tweet_text:
                if self.info.ask:
                    ok = await self._request_approval(f"Publish original post?\n\"{tweet_text[:80]}...\"")
                    if not ok:
                        log("Original post skipped (denied)")
                        return

                resp = await post(ctx, tweet_text)
                if resp.success:
                    log("Original post published!")
                    ts_str = datetime.now(timezone.utc).isoformat()
                    entry = f"| {ts_str} | original_post | self | {tweet_text} | 10.0 | Standalone original post [{time_of_day}]. |"
                    with open(self.info.activity_log_file, "a", encoding="utf-8") as f:
                        f.write(entry + "\n")
                    self.info.original_posts += 1
                else:
                    log(f"Failed to publish: {resp.error}")
        except Exception as e:
            log(f"Error in original post scheduler: {e}")

    def send_command(self, cmd_type: str) -> None:
        self._command_queue.put_nowait({"type": cmd_type})

    async def _request_approval(self, description: str) -> bool:
        """Block until the TUI user confirms or denies an action. Returns True to proceed."""
        if not self.info.ask or self._on_ask is None:
            return True
        self._ask_response = False
        self._ask_event.clear()
        self._on_ask(self, description)
        await self._ask_event.wait()
        return self._ask_response

    def resolve_ask(self, approved: bool) -> None:
        """Called by the TUI when user presses Y or N."""
        self._ask_response = approved
        self._ask_event.set()

    async def _handle_command(self, cmd: dict, ctx, llm_config) -> None:
        from x_personas.agent.log import log

        if cmd["type"] == "original_post":
            log("Manual intervene: force original post")
            await self._try_original_post(ctx, llm_config)
        elif cmd["type"] == "reset_scroll":
            log("Manual intervene: reset scroll & re-navigate home")
            self._state["scroll_count"] = 0
            self.info.current_scroll = 0
            from x_personas.utils.feed import navigate_home
            from x_personas.agent.history import load_engaged_status_ids
            home_page = ctx.pages[0] if ctx.pages else await ctx.new_page()
            await navigate_home(home_page)
            self._state["engaged_ids"] = list(load_engaged_status_ids(self.info.activity_log_file))
            self._state["seen_post_ids"] = []
            log("Scroll reset, re-navigated home, reloaded engaged IDs")

    def stop(self) -> None:
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running
