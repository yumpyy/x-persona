from __future__ import annotations

from x_personas.agent.state import PersonaState


def _score_follow_candidate(post, criteria: dict) -> float:
    if not criteria:
        return 0.0
    score = 0.0
    topic_weight = criteria.get("topic overlap with persona's interests", 0.4)
    mutual_weight = criteria.get("mutual connections (followed by mutuals)", 0.3)
    quality_weight = criteria.get("posting frequency & quality", 0.2)
    bio_weight = criteria.get("bio similarity to persona's reference accounts", 0.1)

    return (
        topic_weight * 5.0
        + mutual_weight * 3.0
        + quality_weight * 5.0
        + bio_weight * 2.0
    )


def _check_follow_limits(follows_this_session: int) -> tuple[bool, str]:
    if follows_this_session >= 3:
        return False, "Session follow limit reached (max 3/hour)"
    return True, ""


def follow_decision(state: PersonaState) -> dict:
    sections = state.get("persona_sections", {})
    feed_posts = state.get("feed_posts", [])
    follows_this_session = state.get("follows_this_session", 0)
    follow_criteria = sections.get("9i", {})

    can_follow, limit_reason = _check_follow_limits(follows_this_session)

    candidates: list[dict] = []
    for post in feed_posts:
        score = _score_follow_candidate(post, follow_criteria)

        if score >= 7 and can_follow:
            candidates.append({
                "handle": post.handle,
                "status_id": post.status_id,
                "score": score,
                "action": "follow",
            })
            follows_this_session += 1
            can_follow, _ = _check_follow_limits(follows_this_session)
        elif score >= 5:
            candidates.append({
                "handle": post.handle,
                "status_id": post.status_id,
                "score": score,
                "action": "observe",
            })

    return {
        "follow_candidates": candidates,
        "follows_this_session": follows_this_session,
    }
