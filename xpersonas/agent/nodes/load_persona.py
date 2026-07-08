"""Load persona config from state."""

from __future__ import annotations

from xpersonas.agent.state import AgentState


def load_persona(state: AgentState, config=None) -> dict:
    """Load persona config. Already populated in state by runner."""
    if state.get("persona_config"):
        return {}
    return {"error": "No persona_config in state"}
