"""Strategy-aware LangGraph StateGraph builder."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from xpersonas.agent.state import AgentState
from xpersonas.agent.nodes import (
    fetch_content,
    generate_content,
    hydrate_context,
    llm_decide,
    load_persona,
    log_activity,
    execute_actions,
    scroll_page,
    state_cleansing,
)
from xpersonas.agent.nodes.promo_engage import promo_engage
from xpersonas.agent.nodes.relationship_track import relationship_track


def build_graph(strategy: str) -> StateGraph:
    """Build a graph tailored to the engagement strategy."""

    builder = StateGraph(AgentState)

    # Universal nodes
    builder.add_node("load_persona", load_persona)
    builder.add_node("fetch_content", fetch_content)
    builder.add_node("llm_decide", llm_decide)
    builder.add_node("log_activity", log_activity)
    builder.add_node("state_cleansing", state_cleansing)

    if strategy in ("active", "selective", "relationship_building"):
        builder.add_node("hydrate_context", hydrate_context)
        builder.add_node("generate_content", generate_content)
        builder.add_node("execute_actions", execute_actions)
        builder.add_node("scroll_page", scroll_page)
        builder.add_node("promo_engage", promo_engage)
        builder.add_node("relationship_track", relationship_track)

        builder.set_entry_point("load_persona")
        builder.add_edge("load_persona", "fetch_content")
        builder.add_edge("fetch_content", "llm_decide")
        builder.add_conditional_edges(
            "llm_decide",
            lambda s: s.get("_routing_target", "log_activity"),
            {
                "generate_content": "hydrate_context",
                "execute_actions": "execute_actions",
                "promo_engage": "promo_engage",
                "log_activity": "log_activity",
            },
        )
        builder.add_edge("hydrate_context", "generate_content")
        builder.add_edge("generate_content", "execute_actions")
        builder.add_edge("execute_actions", "log_activity")
        builder.add_edge("promo_engage", "generate_content")
        builder.add_edge("log_activity", "relationship_track")
        builder.add_edge("relationship_track", "state_cleansing")
        builder.add_edge("state_cleansing", "scroll_page")
        builder.add_edge("scroll_page", END)

    elif strategy == "curation":
        builder.add_node("generate_content", generate_content)
        builder.add_node("execute_actions", execute_actions)
        builder.add_node("scroll_page", scroll_page)

        builder.set_entry_point("load_persona")
        builder.add_edge("load_persona", "fetch_content")
        builder.add_edge("fetch_content", "llm_decide")
        builder.add_conditional_edges(
            "llm_decide",
            lambda s: s.get("_routing_target", "log_activity"),
            {
                "generate_content": "generate_content",
                "execute_actions": "execute_actions",
                "log_activity": "log_activity",
            },
        )
        builder.add_edge("generate_content", "execute_actions")
        builder.add_edge("execute_actions", "log_activity")
        builder.add_edge("log_activity", "state_cleansing")
        builder.add_edge("state_cleansing", "scroll_page")
        builder.add_edge("scroll_page", END)

    elif strategy in ("monitor_and_escalate", "competitive_intel"):
        builder.set_entry_point("load_persona")
        builder.add_edge("load_persona", "fetch_content")
        builder.add_edge("fetch_content", "llm_decide")
        builder.add_edge("llm_decide", "log_activity")
        builder.add_edge("log_activity", "state_cleansing")
        builder.add_edge("state_cleansing", END)

    elif strategy == "support":
        builder.add_node("hydrate_context", hydrate_context)
        builder.add_node("generate_content", generate_content)
        builder.add_node("execute_actions", execute_actions)

        builder.set_entry_point("load_persona")
        builder.add_edge("load_persona", "fetch_content")
        builder.add_edge("fetch_content", "llm_decide")
        builder.add_conditional_edges(
            "llm_decide",
            lambda s: s.get("_routing_target", "log_activity"),
            {
                "generate_content": "hydrate_context",
                "log_activity": "log_activity",
            },
        )
        builder.add_edge("hydrate_context", "generate_content")
        builder.add_edge("generate_content", "execute_actions")
        builder.add_edge("execute_actions", "log_activity")
        builder.add_edge("log_activity", "state_cleansing")
        builder.add_edge("state_cleansing", END)

    else:
        raise ValueError(f"Unknown engagement strategy: {strategy}")

    return builder.compile()
