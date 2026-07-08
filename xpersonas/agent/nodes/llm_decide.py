"""LLM decision engine: decides which posts to engage with."""

from __future__ import annotations

import json
from typing import Any

from xpersonas.agent.state import AgentState
from xpersonas.core.models import ActionType, EngagementDecisions, PendingAction


def _compile_persona_text(config: dict[str, Any]) -> str:
    """Compile persona config into a text block for the LLM prompt."""
    parts = []

    identity = config.get("identity", {})
    parts.append(f"Identity: {identity.get('display_name', '')} (@{identity.get('handle', '')})")
    if identity.get("bio"):
        parts.append(f"Bio: {identity['bio']}")
    if identity.get("occupation"):
        parts.append(f"Occupation: {identity['occupation']}")

    personality = config.get("personality", {})
    if personality.get("core_traits"):
        parts.append(f"Traits: {', '.join(personality['core_traits'])}")
    if personality.get("overall_vibe"):
        parts.append(f"Vibe: {personality['overall_vibe']}")
    if personality.get("humor_style"):
        parts.append(f"Humor: {personality['humor_style']}")
    if personality.get("never"):
        parts.append(f"Never do: {', '.join(personality['never'])}")

    reply_style = config.get("reply_style", {})
    if reply_style.get("baseline"):
        parts.append(f"Reply style: {reply_style['baseline']}")
    if reply_style.get("argumentative_tendency"):
        parts.append(f"Argumentative: {reply_style['argumentative_tendency']}")

    engagement = config.get("engagement", {})
    topics = engagement.get("topics", [])
    if topics:
        parts.append("Topics you care about:")
        for t in topics:
            parts.append(f"  - {t['topic']}: {t.get('stance', 'neutral')} (intensity {t.get('intensity', 5)})")

    buckets = config.get("content", {}).get("buckets", [])
    if buckets:
        parts.append("Content you post about:")
        for b in buckets:
            parts.append(f"  - {b['name']}: {b.get('description', '')}")

    return "\n".join(parts)


def _compile_feed_text(posts: list) -> str:
    """Compile feed posts into a text block for the LLM prompt."""
    parts = []
    for i, post in enumerate(posts, 1):
        flags = []
        if post.is_reply:
            flags.append("reply")
        if post.is_repost:
            flags.append("repost")
        if post.is_quote:
            flags.append("quote")
        if post.author_verified:
            flags.append("VERIFIED")

        metrics_str = ", ".join(f"{k}: {v}" for k, v in post.metrics.items() if v)
        flag_str = f" [{', '.join(flags)}]" if flags else ""

        parts.append(
            f"Post {i}:\n"
            f"  Author: {post.author_name} (@{post.author_handle}){flag_str}\n"
            f"  Text: {post.text[:500]}\n"
            f"  Metrics: {metrics_str}\n"
            f"  ID: {post.id}"
        )

    return "\n\n".join(parts)


async def llm_decide(state: AgentState, config=None) -> dict:
    """Use LLM to decide which posts to engage with."""
    from xpersonas.core.config import resolve_llm_config

    persona = state.get("persona_config", {})
    posts = state.get("feed_posts", [])

    if not posts:
        return {"pending_actions": [], "_routing_target": "log_activity"}

    llm_config = resolve_llm_config(persona)
    persona_text = _compile_persona_text(persona)
    feed_text = _compile_feed_text(posts)

    system_prompt = (
        "You are an AI social media agent. Based on the persona profile below, "
        "decide which posts to engage with and how.\n\n"
        "PERSONA PROFILE:\n"
        f"{persona_text}\n\n"
        "RULES:\n"
        "- Only engage with posts that genuinely match the persona's interests\n"
        "- Score each post 0-10 based on relevance\n"
        "- At most 1 critical/negative engagement per cycle\n"
        "- Deduplicate: one decision per author per cycle\n"
        "- Return empty decisions list if nothing is worth engaging with\n"
    )

    user_prompt = (
        "Below are the posts currently visible in the feed. "
        "Decide which ones to engage with.\n\n"
        f"{feed_text}"
    )

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=llm_config.model,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url or None,
            temperature=0.0,
        )
        structured_llm = llm.with_structured_output(EngagementDecisions)
        response = await structured_llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
    except Exception as e:
        return {"error": str(e), "pending_actions": [], "_routing_target": "log_activity"}

    # Convert decisions to pending actions
    pending: list[dict] = []
    seen_handles: set[str] = set()
    cycle_counts: dict[str, int] = {a: 0 for a in ["like", "reply", "quote", "repost"]}
    rate_limits = persona.get("engagement", {}).get("rate_limits", {})
    cycle_caps = rate_limits.get("per_cycle", {"like": 5, "reply": 2, "repost": 2, "quote": 1})

    for decision in sorted(response.decisions, key=lambda d: d.score, reverse=True):
        if decision.target_handle in seen_handles:
            continue
        seen_handles.add(decision.target_handle)

        for action_str in decision.action_type:
            if action_str not in cycle_caps:
                continue
            if cycle_counts.get(action_str, 0) >= cycle_caps[action_str]:
                continue

            pending.append({
                "action_type": action_str,
                "target_id": decision.target_status_id,
                "target_author": decision.target_handle,
                "content": decision.content,
                "score": decision.score,
                "reason": decision.reason,
            })
            cycle_counts[action_str] = cycle_counts.get(action_str, 0) + 1

    # Determine routing
    has_text = any(a.get("content") for a in pending)
    has_actions = len(pending) > 0

    if has_text:
        routing = "generate_content"
    elif has_actions:
        routing = "execute_actions"
    else:
        routing = "log_activity"

    return {
        "pending_actions": pending,
        "cycle_action_counts": cycle_counts,
        "_routing_target": routing,
    }
