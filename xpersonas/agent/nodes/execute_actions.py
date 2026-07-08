"""Execute pending actions via the platform adapter."""

from __future__ import annotations

import asyncio
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone

from xpersonas.agent.state import AgentState
from xpersonas.core.models import PlatformActionResult
from xpersonas.platforms.base import PlatformAdapter


def _ask_confirm(action: dict) -> bool:
    """Prompt user to confirm an action interactively."""
    action_type = action["action_type"]
    target = action.get("target_handle", action.get("target_id", "?"))
    content = action.get("content", "")

    label = f"  {action_type.upper()} @{target}"
    if content:
        text = content[:80] + ("..." if len(content) > 80 else "")
        label += f'  "{text}"'

    try:
        response = input(f"{label}  [Y/n/s] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    if response == "s":
        print("  Skipped.")
        return False
    return response != "n"


async def execute_actions(state: AgentState, config=None) -> dict:
    """Execute all pending actions through the platform adapter."""
    adapter: PlatformAdapter = config["configurable"]["adapter"]
    ask_mode: bool = config["configurable"].get("ask", False)
    pending = state.get("pending_actions", [])
    executed: list[dict] = []

    if not pending:
        return {"executed_actions": []}

    # Group by target post
    groups: dict[str, list[dict]] = defaultdict(list)
    for action in pending:
        groups[action["target_id"]].append(action)

    for post_id, actions in groups.items():
        for action in actions:
            action_type = action["action_type"]
            content = action.get("content")

            if ask_mode and not _ask_confirm(action):
                executed.append({
                    "action": action,
                    "success": False,
                    "error": "Skipped by user",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                continue

            result = PlatformActionResult(success=False, error="Unknown action type")

            try:
                if action_type == "like":
                    result = await adapter.like(post_id)
                elif action_type == "reply" and content:
                    result = await adapter.reply(post_id, content)
                elif action_type == "quote" and content:
                    result = await adapter.quote(post_id, content)
                elif action_type == "repost":
                    result = await adapter.repost(post_id)
                elif action_type == "follow":
                    result = await adapter.follow(action.get("target_author", ""))
                else:
                    result = PlatformActionResult(success=False, error=f"Skipped: {action_type}")
            except Exception as e:
                result = PlatformActionResult(success=False, error=str(e))

            executed.append({
                "action": action,
                "success": result.success,
                "error": result.error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Random delay between actions
            await asyncio.sleep(random.uniform(3.0, 8.0))

    return {"executed_actions": executed, "pending_actions": []}
