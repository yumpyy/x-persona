from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from src.agent.log import log
from src.agent.rate_limiter import action_delay
from src.agent.state import PersonaState
from src.models.engagement import ActionType, ExecutedAction
from src.utils.post import (
    like_on_page,
    open_post_tab,
    quote_on_page,
    reply_on_page,
    repost_on_page,
)

_ACTION_PRIORITY = {
    ActionType.REPOST: 0,
    ActionType.LIKE: 1,
    ActionType.REPLY: 2,
    ActionType.QUOTE: 3,
}


async def execute_actions(state: PersonaState, config=None) -> dict:
    pending = state.get("pending_actions", [])
    executed: list[ExecutedAction] = []

    configurable = (config or {}).get("configurable", {})
    ctx = configurable.get("browser_context")

    if ctx is None:
        for action in pending:
            timestamp = datetime.now(timezone.utc).isoformat()
            executed.append(ExecutedAction(
                action=action,
                success=False,
                error="No browser context",
                timestamp=timestamp,
            ))
        return {"executed_actions": executed, "pending_actions": []}

    groups: dict[str, list] = defaultdict(list)
    for action in pending:
        groups[action.target_status_id].append(action)

    for status_id, actions in groups.items():
        handle = actions[0].target_handle
        actions.sort(key=lambda a: _ACTION_PRIORITY.get(a.action_type, 99))
        labels = [a.action_type.value for a in actions]
        log(f"execute: {', '.join(labels)} @{handle} id={status_id}")

        ask_mode = configurable.get("ask", False)
        if ask_mode:
            print(f"\n📢 PENDING ENGAGEMENT FOR @{handle} (Post ID: {status_id}):")
            for a in actions:
                content_str = f" with text: \"{a.content}\"" if a.content else ""
                print(f"   👉 [{a.action_type.value.upper()}] {content_str}")
                print(f"      Reason: {a.reason}")
            
            choice = ""
            while choice not in ("y", "n", "s"):
                choice = input("\nExecute this engagement group? [Y/n/s] (Yes / No / Skip): ").strip().lower()
                if choice == "":
                    choice = "y"
                elif choice not in ("y", "n", "s"):
                    print("Please enter 'y' (yes), 'n' (no/reject), or 's' (skip).")
            
            if choice in ("n", "s"):
                log(f"execute: USER REJECTED/SKIPPED actions for @{handle} id={status_id}")
                for action in actions:
                    executed.append(ExecutedAction(
                        action=action,
                        success=False,
                        error="User rejected / skipped action in interactive mode",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ))
                continue

        page = None
        try:
            page = await open_post_tab(ctx, status_id)
            log(f"  tab opened for {status_id}")

            # Simulate human reading dwell time before initiating actions
            import random
            await asyncio.sleep(random.uniform(2.5, 6.0))

            for action in actions:
                action_label = action.action_type.value

                if action.action_type == ActionType.LIKE:
                    result = await like_on_page(page)
                elif action.action_type == ActionType.REPOST:
                    result = await repost_on_page(page)
                elif action.action_type == ActionType.REPLY and action.content:
                    result = await reply_on_page(page, action.content)
                elif action.action_type == ActionType.QUOTE and action.content:
                    result = await quote_on_page(page, action.content)
                else:
                    result = type('ActionResult', (), {'success': False, 'error': 'Unsupported action type or missing content'})()

                status = "✓" if result.success else "✗"
                err = f" ({result.error})" if hasattr(result, 'error') and result.error else ""
                log(f"  {status} {action_label} @{handle}{err}")

                executed.append(ExecutedAction(
                    action=action,
                    success=result.success,
                    error=getattr(result, 'error', None),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))

                if action is not actions[-1]:
                    await asyncio.sleep(action_delay())

        except Exception as e:
            log(f"  ✗ error on {status_id}: {e}")
            for action in actions:
                executed.append(ExecutedAction(
                    action=action,
                    success=False,
                    error=str(e),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ))
        finally:
            if page is not None:
                await page.close()
                log(f"  tab closed")

        await asyncio.sleep(action_delay())

    return {
        "executed_actions": executed,
        "pending_actions": [],
    }
