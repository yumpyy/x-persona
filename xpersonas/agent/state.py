"""Agent state definition for LangGraph."""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from xpersonas.core.models import PlatformPost


class AgentState(TypedDict, total=False):
    # Identity
    persona_id: str
    tenant_id: str
    platform: str
    mode: str

    # Config
    persona_config: dict[str, Any]
    source_data_samples: list[str]
    llm_config: dict[str, Any]
    vlm_config: Optional[dict[str, Any]]

    # Content
    feed_posts: list[PlatformPost]
    feed_cursor: Optional[str]
    thread_contexts: dict[str, list[PlatformPost]]

    # Decisions
    pending_actions: list[dict]
    executed_actions: list[dict]
    cycle_action_counts: dict[str, int]

    # History
    engaged_ids: list[str]
    seen_ids: list[str]

    # Scheduling
    scroll_count: int
    follows_this_session: int

    # Brand mode
    promo_candidates: list[dict]
    products_mentioned_this_cycle: dict[str, int]

    # Personal mode
    relationship_updates: list[dict]

    # Escalation
    escalation_events: list[dict]

    # Error
    error: Optional[str]

    # Routing (transient, not persisted)
    _routing_target: str
