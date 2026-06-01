from __future__ import annotations

from src.agent.state import PersonaState


def state_cleansing(state: PersonaState) -> dict:
    return {
        "feed_posts": [],
        "feed_scroll_position": None,
        "scored_posts": [],
        "pending_actions": [],
        "executed_actions": [],
        "follow_candidates": [],
        "cycle_action_counts": {},
        "error": None,
    }
