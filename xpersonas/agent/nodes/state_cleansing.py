"""Reset transient per-cycle state fields."""

from __future__ import annotations

from xpersonas.agent.state import AgentState


def state_cleansing(state: AgentState, config=None) -> dict:
    """Clear fields that should not persist across cycles."""
    return {
        "feed_posts": [],
        "feed_cursor": None,
        "pending_actions": [],
        "executed_actions": [],
        "thread_contexts": {},
        "promo_candidates": [],
        "relationship_updates": [],
        "escalation_events": [],
        "cycle_action_counts": {},
        "error": None,
        "_routing_target": "",
    }
