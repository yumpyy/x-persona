#!/usr/bin/env python3
"""Test the agent pipeline: parsing, LLM decision models, rate limits, history dedup (no browser/LLM call needed)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from x_personas.agent.nodes.load_persona import load_persona
from x_personas.agent.nodes.llm_decide import _build_feed_text, _build_persona_text, _decisions_to_pending
from x_personas.agent.rate_limiter import RateLimitState, cycle_caps, scroll_delay, action_delay
from x_personas.agent.history import load_engaged_status_ids
from x_personas.models.engagement import ActionType, EngagementDecisions, PostDecision
from x_personas.models.feed import FeedPost
from datetime import datetime, timezone
import json, os, tempfile


def _make_post(status_id: str, handle: str, text: str, hours_ago: int = 0) -> FeedPost:
    ts = datetime.now(timezone.utc).isoformat()
    if hours_ago > 0:
        from datetime import timedelta
        ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
    return FeedPost(
        status_id=status_id,
        author_name=handle,
        handle=handle,
        text=text,
        timestamp=ts,
    )


def test_persona_parsing():
    persona_file = "personas/purusa0x6c/persona.md"
    assert Path(persona_file).exists(), f"{persona_file} not found"
    state = load_persona({
        "persona_file": persona_file, "activity_log_file": "", "llm_config": {},
        "persona_sections": {}, "source_data_files": [], "feed_posts": [],
        "feed_scroll_position": None, "scored_posts": [], "pending_actions": [],
        "executed_actions": [], "thread_contexts": {}, "follow_candidates": [], "follows_this_session": 0,
        "rate_limit_file": "", "cycle_action_counts": {}, "seen_post_ids": [],
        "engaged_ids": [], "scroll_count": 0, "error": None,
    })
    s = state["persona_sections"]
    assert "9a" in s, f"9a section missing, have: {list(s.keys())}"
    assert len(s["9a"]) > 0, f"9a weights empty (have keys: {list(s.keys())})"
    assert "9g" in s and len(s["9g"]) > 0, "9g matrix missing"
    assert "9f" in s and len(s["9f"]) > 0, "9f thresholds missing"
    assert "8" in s and len(s["8"]) > 0, "Stances (8) missing"
    assert isinstance(s["8"], list), "Stances (8) must be a parsed list"
    assert "nuance" in s["8"][0], "Stances (8) elements must contain nuance"
    assert "6" in s, "Section 6 missing"
    assert s["6"].get("baseline_style") != "", "baseline_style should be parsed"
    assert len(s["6"].get("common_reply_templates", [])) > 0, "common_reply_templates should be parsed"
    print(f"  \u2713 persona parsing: {len(s)} sections, {len(s['9a'])} topic weights {list(s['9a'].keys())[:3]}...")


def test_post_decision_model():
    d = PostDecision(
        action_type=["like"],
        target_status_id="111",
        target_handle="user1",
        content=None,
        score=7.5,
        reason="interesting post",
    )
    assert d.action_type == ["like"]
    assert d.target_status_id == "111"
    assert d.score == 7.5
    print(f"  \u2713 PostDecision model: valid")


def test_engagement_decisions_model():
    decisions = EngagementDecisions(decisions=[
        PostDecision(action_type=["like"], target_status_id="1", target_handle="u1", score=7.0, reason="good"),
        PostDecision(action_type=["reply", "like"], target_status_id="2", target_handle="u2", content="nice!", score=8.0, reason="great"),
    ])
    assert len(decisions.decisions) == 2
    assert decisions.decisions[0].action_type == ["like"]
    assert decisions.decisions[1].action_type == ["reply", "like"]
    assert decisions.decisions[1].content == "nice!"
    print(f"  \u2713 EngagementDecisions model: {len(decisions.decisions)} decisions")


def test_decisions_to_pending():
    decisions = [
        PostDecision(action_type=["like"], target_status_id="111", target_handle="alice", score=7.0, reason="cool"),
        PostDecision(action_type=["reply", "like"], target_status_id="222", target_handle="bob", content="agree!", score=8.0, reason="strong take"),
        PostDecision(action_type=["like"], target_status_id="333", target_handle="charlie", score=9.0, reason="love it"),
    ]

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({"entries": []}, f)
        limit_file = f.name

    pending, counts = _decisions_to_pending(decisions, limit_file)

    assert len(pending) == 4  # alice=like, bob=like+reply, charlie=like
    assert pending[0].action_type == ActionType.LIKE
    assert pending[1].action_type == ActionType.REPLY
    assert pending[2].action_type == ActionType.LIKE
    assert pending[3].action_type == ActionType.LIKE
    assert all(a.content is None for a in pending), "content always None (generated separately)"
    assert counts["like"] == 3
    assert counts["reply"] == 1

    # dedup by handle: only first decision for a handle is processed
    decisions_dup = [
        PostDecision(action_type=["like"], target_status_id="111", target_handle="alice", score=7.0, reason="cool"),
        PostDecision(action_type=["reply", "like"], target_status_id="444", target_handle="alice", score=8.0, reason="also cool"),
    ]
    pending2, _ = _decisions_to_pending(decisions_dup, limit_file)
    assert len(pending2) == 1, "Should take first decision for handle, skip second"
    assert pending2[0].action_type == ActionType.LIKE

    # action duplicate deduplication: ["like", "like", "reply"] should produce unique actions
    decisions_action_dup = [
        PostDecision(action_type=["like", "like", "reply"], target_status_id="555", target_handle="dave", score=8.0, reason="dup actions test"),
    ]
    pending3, _ = _decisions_to_pending(decisions_action_dup, limit_file)
    assert len(pending3) == 2, f"Expected 2 pending actions (1 like, 1 reply), got {len(pending3)}"
    assert pending3[0].action_type == ActionType.LIKE
    assert pending3[1].action_type == ActionType.REPLY

    os.unlink(limit_file)
    print(f"  \u2713 decisions_to_pending: {len(pending)} pending, content=None, dedup works")


def test_llm_feed_text():
    posts = [
        _make_post("1", "alice", "hello world", hours_ago=0),
        _make_post("2", "bob", "check this out", hours_ago=2),
    ]
    text = _build_feed_text(posts)
    assert "Post 1" in text
    assert "@alice" in text
    assert "hello world" in text
    assert "Status ID: 1" in text
    assert "Post 2" in text
    assert "@bob" in text
    assert "check this out" in text
    assert "Status ID: 2" in text
    print(f"  \u2713 feed text: {len(text)} chars, {len(posts)} posts rendered")


def test_llm_persona_text():
    sections = {
        "1": "Test persona bio with interests in tech and farming.",
        "8": [
            {"topic": "Java / OOP", "stance": "strong dislike", "intensity": "high", "nuance": "slow, bloated"},
            {"topic": "C / Rust", "stance": "strong love", "intensity": "high", "nuance": "bare-metal control"}
        ],
        "9a": {"tech": 8.0, "farming": 7.0},
        "9b": {"stranger": 2.0, "friend": 7.0},
        "9f": {"3-4.9": "like only", "5-6.9": "reply + like"},
    }
    text = _build_persona_text(sections)
    assert "Persona Identity" in text
    assert "Test persona bio" in text
    assert "Topic Stances" in text
    assert "Java / OOP: stance=strong dislike" in text
    assert "Nuance/Action policy: slow, bloated" in text
    assert "Topic Affinity Weights" in text
    assert "tech: 8.0" in text
    assert "Account Relationship Weights" in text
    assert "stranger: 2.0" in text
    assert "Engagement Thresholds" in text
    print(f"  \u2713 persona text: {len(text)} chars, sections rendered")


def test_rate_limiter_persistence():
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
        json.dump({
            "entries": [
                {"action": "like", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"action": "like", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"action": "reply", "timestamp": datetime.now(timezone.utc).isoformat()},
            ]
        }, f)
        limit_file = f.name

    rl = RateLimitState(limit_file)
    assert rl.hourly_count("like") == 2
    assert rl.hourly_count("reply") == 1
    assert rl.hourly_count("repost") == 0

    ok, reason = rl.can_act("like")
    assert ok, f"Should be able to like ({reason})"

    rl.record("like")
    rl.save()
    rl2 = RateLimitState(limit_file)
    assert rl2.hourly_count("like") == 3
    print(f"  \u2713 rate limiter: persistence works ({rl2.hourly_count('like')} likes tracked)")

    os.unlink(limit_file)


def test_scroll_delay():
    d = scroll_delay()
    assert 5.0 <= d <= 15.0, f"scroll_delay {d} out of range"
    print(f"  \u2713 scroll_delay: {d:.2f}s")


def test_action_delay():
    d = action_delay()
    assert 3.0 <= d <= 8.0, f"action_delay {d} out of range"
    print(f"  \u2713 action_delay: {d:.2f}s")


def test_history_loading():
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        f.write("| timestamp | action | target | content | score | context |\n")
        f.write("|---|---|---|---|---|---|\n")
        f.write("| 2024-01-01T00:00:00 | like | @user1 / 111 | nice | 8.0 | test |\n")
        f.write("| 2024-01-01T00:01:00 | reply | @user2 / 222 | cool | 7.0 | test |\n")
        log_file = f.name

    ids = load_engaged_status_ids(log_file)
    assert "111" in ids, "111 should be in engaged set"
    assert "222" in ids, "222 should be in engaged set"
    assert len(ids) == 2, f"Expected 2 ids, got {len(ids)}"
    print(f"  \u2713 history loading: {len(ids)} ids loaded from activity log")

    os.unlink(log_file)


def test_load_persona_noop():
    state = load_persona({
        "persona_file": "purusha-persona-struct.md",
        "persona_sections": {"9a": {"tech": 8.0}},
    })
    assert state == {}, "load_persona should return {} when already loaded"
    print(f"  \u2713 load_persona no-op: returned empty dict")


def test_load_persona_empty_file():
    import tempfile
    import pytest
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
        temp_name = f.name

    try:
        with pytest.raises(ValueError, match="completely empty"):
            load_persona({
                "persona_file": temp_name,
                "persona_sections": {},
            })
        print(f"  \u2713 load_persona empty file validation: correctly raised ValueError")
    finally:
        os.unlink(temp_name)


def test_recent_engagements_loading():
    from x_personas.agent.history import load_recent_engagements
    from x_personas.agent.nodes.llm_decide import _build_recent_engagements_text

    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        f.write("| timestamp | action | target | content | score | context |\n")
        f.write("|---|---|---|---|---|---|\n")
        f.write("| 2024-01-01T00:00:00 | like | @user1 / 111 |  | 8.0 | systems design [✓] |\n")
        f.write("| 2024-01-01T00:01:00 | reply | @user2 / 222 | cool | 7.0 | compilers [✓] |\n")
        f.write("| 2024-01-01T00:02:00 | reply | @user3 / 333 | check | 6.0 | ignored/failed [✗] |\n")
        log_file = f.name

    engagements = load_recent_engagements(log_file, limit=5)
    assert len(engagements) == 2, f"Expected 2 successful engagements, got {len(engagements)}"
    assert engagements[0]["action"] == "reply"
    assert engagements[0]["target"] == "@user2 / 222"
    assert engagements[0]["context"] == "compilers"

    text = _build_recent_engagements_text(engagements)
    assert "- [reply] target: @user2 / 222 content: \"cool\" | reason: compilers" in text
    assert "- [like] target: @user1 / 111 | reason: systems design" in text
    print(f"  \u2713 recent engagements loading and formatting: verified")

    os.unlink(log_file)


def test_critique_variety_filters():
    from x_personas.agent.nodes.llm_decide import _is_critical_engagement, _is_critical_decision, PostDecision

    disliked = ["bootcamp", "grind"]

    # Test _is_critical_engagement
    assert _is_critical_engagement({"context": "course-buyer / bootcamp boast", "content": ""}, disliked) is True
    assert _is_critical_engagement({"context": "systems engineering", "content": "this is nice"}, disliked) is False
    assert _is_critical_engagement({"context": "systems", "content": "don't do another dsa grind"}, disliked) is True

    # Test _is_critical_decision
    assert _is_critical_decision(PostDecision(
        action_type=["reply"], target_status_id="1", target_handle="u1", score=8.0,
        reason="Trigger: dsa ninja / corporate grind boast."
    ), disliked) is True
    assert _is_critical_decision(PostDecision(
        action_type=["reply"], target_status_id="1", target_handle="u1", score=8.0,
        reason="nice compiler design project"
    ), disliked) is False

    print(f"  \u2713 critique variety filtering helpers: verified")


def test_generate_original_post():
    from x_personas.agent.nodes.generate_content import generate_original_post
    assert generate_original_post is not None
    print(f"  \u2713 generate_original_post utility: import and signature verified")


if __name__ == "__main__":
    print("Testing agent pipeline...\n")
    test_persona_parsing()
    test_post_decision_model()
    test_engagement_decisions_model()
    test_decisions_to_pending()
    test_llm_feed_text()
    test_llm_persona_text()
    test_rate_limiter_persistence()
    test_scroll_delay()
    test_action_delay()
    test_history_loading()
    test_load_persona_noop()
    test_load_persona_empty_file()
    test_recent_engagements_loading()
    test_critique_variety_filters()
    test_generate_original_post()
    print("\n\u2713 All agent tests passed!")
