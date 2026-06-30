from __future__ import annotations

from pathlib import Path
from typing import Any
from langchain_core.runnables import RunnableConfig

from x_personas.agent.config import get_llm
from x_personas.agent.log import log
from x_personas.agent.rate_limiter import RateLimitState, cycle_caps
from x_personas.agent.state import PersonaState
from x_personas.models.engagement import ActionType, EngagementDecisions, PendingAction, PostDecision

_PROMPT_DIR = Path(__file__).parent.parent.parent / "prompts"


def _load_template(name: str) -> str:
    """Load a markdown template file from the prompts directory with exception handling."""
    path = _PROMPT_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Required prompt template '{name}' does not exist at: {path}")
    return path.read_text(encoding="utf-8")


def _build_persona_text(sections: dict[str, Any]) -> str:
    """Compile sections of a structured persona profile into a markdown string for prompt injection."""
    blocks: list[str] = []

    sec1 = sections.get("1", {})
    if isinstance(sec1, str) and sec1.strip():
        blocks.append("## Persona Identity\n" + sec1.strip())
    elif isinstance(sec1, dict):
        lines = [f"{k}: {v.replace('<br>', '\n')}" for k, v in sec1.items() if v and isinstance(v, str)]
        if lines:
            blocks.append("## Persona Identity\n" + "\n".join(lines))

    ling = sections.get("2", {})
    if isinstance(ling, dict):
        parts: list[str] = []
        if ling.get("vocabulary"):
            words = [f"- {v.get('word','')}: {v.get('meaning','')} ({v.get('context','')})" for v in ling["vocabulary"]]
            parts.append("Vocabulary:\n" + "\n".join(words))
        if ling.get("emoji_usage"):
            emoji = [f"- {e.get('emoji','')}: {e.get('meaning','')} (freq: {e.get('frequency','')})" for e in ling["emoji_usage"]]
            parts.append("Emoji usage:\n" + "\n".join(emoji))
        if ling.get("slang"):
            slang = [f"- {s.get('slang','')}: {s.get('meaning','')} ({s.get('when','')})" for s in ling["slang"]]
            parts.append("Slang:\n" + "\n".join(slang))
        for key in ("spelling_quirks", "quirks", "grammar"):
            val = ling.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(f"Quirks: {val.strip()}")
            elif isinstance(val, list):
                parts.append("Quirks:\n" + "\n".join(f"- {q}" for q in val if q))
        if parts:
            blocks.append("## Linguistic Style\n" + "\n\n".join(parts))

    sec3 = sections.get("3", {})
    if isinstance(sec3, dict) and sec3:
        lines = [f"{k}: {v}" for k, v in sec3.items() if v]
        if lines:
            blocks.append("## Personality & Vibe\n" + "\n".join(lines))

    sec4 = sections.get("4", {})
    if isinstance(sec4, dict) and sec4:
        blocks.append("## Content Buckets\n" + "\n".join(f"- {k}: {v}" for k, v in sec4.items()))

    sec5 = sections.get("5")
    if isinstance(sec5, str) and sec5.strip():
        blocks.append("## Posting Behavior\n" + sec5.strip())

    replies = sections.get("6", {})
    if isinstance(replies, dict):
        lines = []
        baseline = replies.get("baseline_style")
        if isinstance(baseline, str) and baseline.strip():
            lines.append(f"Baseline style: {baseline.strip()}")
        for row in replies.get("length_matrix", []):
            lines.append(f"- Situation: {row.get('situation','')} \u2192 Length: {row.get('length','')}, Tone: {row.get('tone','')}")
        for row in replies.get("escalation_triggers", []):
            lines.append(f"- Trigger: {row.get('trigger','')} \u2192 Shift: {row.get('shift','')}")
        for row in replies.get("common_reply_templates", []):
            lines.append(f"- Template/Inspiration for {row.get('trigger','')}: e.g. \"{row.get('response','')}\"")
        tendency = replies.get("argumentative_tendency")
        if isinstance(tendency, str) and tendency.strip():
            lines.append(f"Argumentative tendency: {tendency.strip()}")
        if lines:
            blocks.append("## Reply Behavior\n" + "\n".join(lines))

    sec7 = sections.get("7", {})
    if isinstance(sec7, dict) and sec7:
        lines = []
        for topic in sec7.get("topics", []):
            if isinstance(topic, dict):
                lines.append(f"- {topic.get('topic','')}: affinity={topic.get('affinity','')}, why={topic.get('why','')}")
        for acct in sec7.get("accounts", []):
            if isinstance(acct, dict):
                lines.append(f"- @{acct.get('account','')}: {acct.get('relationship','')} \u2192 {acct.get('engagement_type','')}")
        lines.append("Formats:")
        for fmt in sec7.get("formats", []):
            if isinstance(fmt, dict):
                lines.append(f"  - {fmt.get('format','')}: {fmt.get('engagement_likelihood','')}")
        if lines:
            blocks.append("## Engagement Triggers\n" + "\n".join(lines))

    sec8 = sections.get("8", [])
    if sec8:
        if isinstance(sec8, list):
            lines = []
            for s in sec8:
                if isinstance(s, dict):
                    topic = s.get("topic", "")
                    stance = s.get("stance", "")
                    intensity = s.get("intensity", "")
                    nuance = s.get("nuance", "")
                    lines.append(f"- {topic}: stance={stance} (intensity: {intensity}). Nuance/Action policy: {nuance}")
            if lines:
                blocks.append("## Topic Stances\n" + "\n".join(lines))
        elif isinstance(sec8, dict):
            blocks.append("## Topic Stances\n" + "\n".join(f"- {k}: stance={v}" for k, v in sec8.items()))

    topics = sections.get("9a", {})
    if isinstance(topics, dict) and topics:
        blocks.append("## Topic Affinity Weights\n" + "\n".join(f"- {k}: {v}" for k, v in topics.items()))

    accounts = sections.get("9b", {})
    if isinstance(accounts, dict) and accounts:
        blocks.append("## Account Relationship Weights\n" + "\n".join(f"- {k}: {v}" for k, v in accounts.items()))

    formats = sections.get("9c", {})
    if isinstance(formats, dict) and formats:
        blocks.append("## Format Affinity Weights\n" + "\n".join(f"- {k}: {v}" for k, v in formats.items()))

    recency = sections.get("9d", {})
    if isinstance(recency, dict) and recency:
        blocks.append("## Recency Bonus\n" + "\n".join(f"- {k}: {v}" for k, v in recency.items()))

    thresholds = sections.get("9f", {})
    if isinstance(thresholds, dict) and thresholds:
        blocks.append("## Engagement Thresholds\n" + "\n".join(f"- Score {k}: {v}" for k, v in thresholds.items()))

    matrix = sections.get("9g", [])
    if isinstance(matrix, list) and matrix:
        lines = []
        for m in matrix:
            c = m.get("condition", "")
            e = m.get("engagement_type", "")
            if c and e and c != "condition":
                lines.append(f"- Condition: {c} \u2192 Action: {e}")
        if lines:
            blocks.append("## Engagement Type Matrix\n" + "\n".join(lines))

    guidelines = sections.get("9h", [])
    if isinstance(guidelines, list) and guidelines:
        blocks.append("## Reply Guidelines\n" + "\n".join(f"- {g}" for g in guidelines if g))

    follow = sections.get("9i", {})
    if isinstance(follow, dict) and follow:
        blocks.append("## Follow Criteria\n" + "\n".join(f"- {k}: {v}" for k, v in follow.items()))

    sec13 = sections.get("13", {})
    if isinstance(sec13, dict) and sec13.get("source_files"):
        files = sec13["source_files"]
        if isinstance(files, list) and files:
            blocks.append("## Source Data\nSource files: " + ", ".join(str(f) for f in files))

    tone = sections.get("12", [])
    if isinstance(tone, list) and tone:
        blocks.append("## Tone Rules\n" + "\n".join(f"- {t}" for t in tone if t))

    return "\n\n".join(blocks)


def _build_feed_text(posts: list[Any]) -> str:
    """Render structured feed posts list into a descriptive text context for LLM decision ingestion."""
    lines: list[str] = []
    for i, p in enumerate(posts, 1):
        lines.append(f"Post {i}:")
        verified_suffix = " (VERIFIED/PREMIUM ACCOUNT - High priority for organic impressions)" if getattr(p, "author_verified", False) else ""
        lines.append(f"  Author: @{p.handle or 'unknown'}{verified_suffix}")
        lines.append(f"  Text: {p.text or '(no text)'}")
        if p.metrics:
            likes = getattr(p.metrics, 'likes', 0)
            retweets = getattr(p.metrics, 'retweets', 0)
            replies = getattr(p.metrics, 'replies', 0)
            lines.append(f"  Metrics: {likes} likes, {retweets} reposts, {replies} replies")
        lines.append(f"  Status ID: {p.status_id}")
        include = []
        if p.media_urls:
            include.append(f"{len(p.media_urls)} images")
        if p.is_quote:
            include.append("quote tweet")
        if p.is_reply:
            include.append("reply")
        if include:
            lines.append(f"  Flags: {', '.join(include)}")
        lines.append("")
    return "\n".join(lines)


def _build_recent_engagements_text(engagements: list[dict]) -> str:
    if not engagements:
        return "No recent engagements logged."
    lines = []
    for e in engagements:
        content_str = f" content: \"{e['content']}\"" if e['content'] else ""
        lines.append(f"- [{e['action']}] target: {e['target']}{content_str} | reason: {e['context']}")
    return "\n".join(lines)


def _decisions_to_pending(
    decisions: list[PostDecision],
    state_rate_limit_file: str,
) -> tuple[list[PendingAction], dict[str, int]]:
    """Convert raw LLM decisions into pending actions queue while enforcing local rate limits and caps."""
    rl = RateLimitState(state_rate_limit_file)
    caps = cycle_caps()
    cycle_counts: dict[str, int] = {}
    already_targeted: set[str] = set()
    pending: list[PendingAction] = []

    ACTION_MAP = {"like": ActionType.LIKE, "reply": ActionType.REPLY, "quote": ActionType.QUOTE}

    for d in decisions:
        handle = d.target_handle
        if handle in already_targeted:
            continue

        action_types: list[ActionType] = []
        unique_action_types = list(dict.fromkeys(d.action_type))
        for at_str in unique_action_types:
            at_str = at_str.lower()
            if at_str not in ACTION_MAP:
                continue
            at = ACTION_MAP[at_str]
            cap = caps.get(at_str, 5)
            if cycle_counts.get(at_str, 0) >= cap:
                continue
            ok, _ = rl.can_act(at_str)
            if not ok:
                continue
            action_types.append(at)
            cycle_counts[at_str] = cycle_counts.get(at_str, 0) + 1

        if not action_types:
            continue

        already_targeted.add(handle)

        for at in action_types:
            pending.append(PendingAction(
                action_type=at,
                target_status_id=d.target_status_id,
                target_handle=handle,
                content=None,
                score=d.score,
                reason=d.reason,
            ))

    return pending, cycle_counts


def _get_disliked_topics(sections: dict) -> list[str]:
    """Dynamically get the list of topics with 'dislike' or 'strong dislike' stance from the persona sections."""
    disliked = []
    stances = sections.get("8", [])
    if isinstance(stances, list):
        for s in stances:
            if isinstance(s, dict):
                stance_val = s.get("stance", "").lower()
                topic_val = s.get("topic", "")
                if "dislike" in stance_val:
                    disliked.append(topic_val)
    return disliked


def _is_critical_engagement(action_dict: dict, disliked_topics: list[str]) -> bool:
    """Helper to detect if a historical action was a critical critique based on content or reason context."""
    context_lower = action_dict.get("context", "").lower()
    content_lower = action_dict.get("content", "").lower()
    
    # Generic keywords indicating a critique/disagreement/negative response
    general_keywords = {"critique", "dislike", "sarcasm", "slander", "bloat", "hype", "anti-"}
    if any(kw in context_lower for kw in general_keywords):
        return True
    if any(kw in content_lower for kw in general_keywords):
        return True
        
    for topic in disliked_topics:
        words = [w.strip(" /,.-") for w in topic.lower().split() if len(w.strip(" /,.-")) > 1]
        for w in words:
            if w in context_lower or w in content_lower:
                return True
                
    return False


def _is_critical_decision(d: PostDecision, disliked_topics: list[str]) -> bool:
    """Fallback detector to check if a new LLM decision is critical based on its reason or content."""
    reason_lower = d.reason.lower()
    content_lower = (d.content or "").lower()
    
    general_keywords = {"critique", "dislike", "sarcasm", "slander", "bloat", "hype", "anti-"}
    if any(kw in reason_lower for kw in general_keywords):
        return True
    if any(kw in content_lower for kw in general_keywords):
        return True
        
    for topic in disliked_topics:
        words = [w.strip(" /,.-") for w in topic.lower().split() if len(w.strip(" /,.-")) > 1]
        for w in words:
            if w in reason_lower or w in content_lower:
                return True
                
    return False


async def llm_decide(state: PersonaState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Execute LLM decision engine to decide which feed posts are worth engaging.

    Analyzes full persona profile rules, extracts post parameters, compiles multimodal
    image blocks inside the payload for live visual reasoning, and returns structured PostDecisions.
    """
    sections = state.get("persona_sections", {})
    posts = state.get("feed_posts", [])
    engaged_ids = set(state.get("engaged_ids", []))
    llm_config = state.get("llm_config", {})
    vlm_config = state.get("vlm_config")

    if not posts:
        log("llm_decide: no feed posts to evaluate")
        return {"pending_actions": [], "cycle_action_counts": {}, "_routing_target": "log_activity"}

    new_posts = [p for p in posts if p.status_id not in engaged_ids]
    if not new_posts:
        log("llm_decide: all feed posts already engaged")
        return {"pending_actions": [], "cycle_action_counts": {}, "_routing_target": "log_activity"}

    log(f"llm_decide: evaluating {len(new_posts)} post(s) via LLM")

    recent_engagements = []
    log_file = state.get("activity_log_file", "")
    if log_file:
        from x_personas.agent.history import load_recent_engagements
        recent_engagements = load_recent_engagements(log_file, limit=10)
    recent_engagements_text = _build_recent_engagements_text(recent_engagements)

    persona_text = _build_persona_text(sections)
    feed_text = _build_feed_text(new_posts)

    try:
        system_template = _load_template("llm_decide_system.md")
        user_template = _load_template("llm_decide_user.md")
    except FileNotFoundError as err:
        log(f"llm_decide: Critical prompt error: {err}")
        return {"pending_actions": [], "cycle_action_counts": {}, "_routing_target": "log_activity"}

    system_prompt = system_template.replace("{persona_sections}", persona_text).replace("{recent_engagements}", recent_engagements_text)
    user_prompt = user_template.replace("{feed_posts}", feed_text)

    log(f"llm_decide: system prompt ({len(system_prompt)} chars)")
    log(f"llm_decide: user prompt ({len(user_prompt)} chars)")

    decide_cfg = vlm_config if vlm_config else dict(llm_config)
    decide_cfg = dict(decide_cfg)
    decide_cfg["temperature"] = 0.0  # Precise and deterministic decisions
    llm = get_llm(decide_cfg)
    structured = llm.with_structured_output(EngagementDecisions)

    try:
        user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
        
        # Append up to 4 image URLs (only if VLM is configured)
        if vlm_config:
            image_count = 0
            for p in new_posts:
                if p.media_urls:
                    for url in p.media_urls:
                        if image_count >= 4:
                            break
                        user_content.append({
                            "type": "image_url",
                            "image_url": {"url": url}
                        })
                        image_count += 1

        result: EngagementDecisions = structured.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ])
        decisions = result.decisions
        decisions = [d for d in decisions if d.target_handle]
        log(f"llm_decide: LLM returned {len(decisions)} decision(s)")

        # Enforce strict critique variety policy in Python to prevent LLM soft-matching bypass
        disliked_topics = _get_disliked_topics(sections)
        has_recent_critique = any(_is_critical_engagement(e, disliked_topics) for e in recent_engagements)
        log(f"llm_decide: recent history has critique = {has_recent_critique}")

        filtered_decisions = []
        critical_count_this_cycle = 0

        # Sort decisions by score descending to prioritize high-quality options
        sorted_decisions = sorted(decisions, key=lambda x: x.score, reverse=True)

        for d in sorted_decisions:
            is_crit = d.is_critical_critique or _is_critical_decision(d, disliked_topics)
            if is_crit:
                if has_recent_critique:
                    log(f"  [VARIETY FILTER] Discarding critique decision targeting @{d.target_handle} because a critical engagement occurred recently in history.")
                    continue
                if critical_count_this_cycle >= 1:
                    log(f"  [VARIETY FILTER] Discarding critique decision targeting @{d.target_handle} to enforce limit of at most ONE critical engagement per cycle.")
                    continue
                critical_count_this_cycle += 1
                filtered_decisions.append(d)
            else:
                filtered_decisions.append(d)

        decisions = filtered_decisions

        for d in decisions:
            actions = [a for a in d.action_type if a.lower() in ("like", "reply", "quote")]
            if actions:
                log(f"  {','.join(actions):>8} @{d.target_handle:<20} score={d.score:.1f} reason=\"{d.reason[:60]}\"")
            else:
                log(f"  (ignored) @{d.target_handle:<20} score={d.score:.1f} reason=\"{d.reason[:60]}\"")
    except Exception as e:
        log(f"llm_decide: LLM invocation failed: {e}")
        return {"pending_actions": [], "cycle_action_counts": {}, "_routing_target": "log_activity"}

    if not decisions:
        log("llm_decide: no posts worth engaging with")
        return {"pending_actions": [], "cycle_action_counts": {}, "_routing_target": "log_activity"}

    pending, cycle_counts = _decisions_to_pending(decisions, state.get("rate_limit_file", ""))

    if not pending:
        log("llm_decide: no pending actions remaining after rate limit enforcement")
        return {"pending_actions": [], "cycle_action_counts": cycle_counts, "_routing_target": "log_activity"}

    has_text = any(a.action_type in (ActionType.REPLY, ActionType.QUOTE) for a in pending)
    if has_text:
        target = "generate_content"
    else:
        target = "execute_actions"

    log(f"llm_decide: {len(pending)} action(s) across {len({a.target_handle for a in pending})} post(s) -> {target}")
    for a in pending:
        log(f"  llm_decide: [{a.action_type.value:>6}] @{a.target_handle:<20} id={a.target_status_id} score={a.score:.1f}")

    return {
        "pending_actions": pending,
        "cycle_action_counts": cycle_counts,
        "_routing_target": target,
    }
