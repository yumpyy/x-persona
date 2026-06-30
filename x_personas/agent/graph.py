from __future__ import annotations

from langgraph.graph import END, StateGraph

from x_personas.agent.nodes.execute_actions import execute_actions
from x_personas.agent.nodes.fetch_feed import scroll_feed
from x_personas.agent.nodes.follow_decision import follow_decision
from x_personas.agent.nodes.generate_content import generate_content
from x_personas.agent.nodes.hydrate_replies import hydrate_replies
from x_personas.agent.nodes.llm_decide import llm_decide
from x_personas.agent.nodes.load_persona import load_persona
from x_personas.agent.nodes.log_activity import log_activity
from x_personas.agent.nodes.scroll_page import scroll_page
from x_personas.agent.nodes.state_cleansing import state_cleansing
from x_personas.agent.state import PersonaState


def create_graph() -> StateGraph:
    builder = StateGraph(PersonaState)

    builder.add_node("load_persona", load_persona)
    builder.add_node("scroll_feed", scroll_feed)
    builder.add_node("llm_decide", llm_decide)
    builder.add_node("hydrate_replies", hydrate_replies)
    builder.add_node("generate_content", generate_content)
    builder.add_node("execute_actions", execute_actions)
    builder.add_node("log_activity", log_activity)
    builder.add_node("follow_decision", follow_decision)
    builder.add_node("state_cleansing", state_cleansing)
    builder.add_node("scroll_page", scroll_page)

    builder.set_entry_point("load_persona")
    builder.add_edge("load_persona", "scroll_feed")
    builder.add_edge("scroll_feed", "llm_decide")
    builder.add_conditional_edges(
        "llm_decide",
        lambda s: s.get("_routing_target", "log_activity"),
        {
            "generate_content": "hydrate_replies",
            "execute_actions": "execute_actions",
            "log_activity": "log_activity",
        }
    )
    builder.add_edge("hydrate_replies", "generate_content")
    builder.add_conditional_edges(
        "generate_content",
        lambda s: s.get("_routing_target", "execute_actions"),
    )
    builder.add_edge("execute_actions", "log_activity")
    builder.add_edge("log_activity", "follow_decision")
    builder.add_edge("follow_decision", "state_cleansing")
    builder.add_edge("state_cleansing", "scroll_page")
    builder.add_edge("scroll_page", END)

    return builder.compile()
