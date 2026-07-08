"""Log executed actions to the database."""

from __future__ import annotations

from xpersonas.agent.state import AgentState
from xpersonas.storage.database import Database


def log_activity(state: AgentState, config=None) -> dict:
    """Record all executed actions to the activity log."""
    db: Database = config["configurable"]["db"]
    persona_id = state.get("persona_id", "")
    platform = state.get("platform", "x")
    executed = state.get("executed_actions", [])

    for entry in executed:
        action = entry.get("action", {})
        db.execute(
            "INSERT INTO activity_log "
            "(persona_id, timestamp, platform, action_type, target_post_id, target_author, "
            "content, score, reason, success, error, is_promo, product_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                persona_id,
                entry.get("timestamp", ""),
                platform,
                action.get("action_type", ""),
                action.get("target_id", ""),
                action.get("target_author", ""),
                action.get("content", ""),
                action.get("score", 0.0),
                action.get("reason", ""),
                int(entry.get("success", False)),
                entry.get("error", ""),
                int(action.get("is_promo", False)),
                action.get("product_id", ""),
            ),
        )

    db.commit()
    return {}
