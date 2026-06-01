#!/usr/bin/env python3
"""Verify context-aware reply hydration, mutual chaining, and semantic deduplication."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.nodes.generate_content import generate_content, _extract_mutual_handles
from src.agent.nodes.hydrate_replies import hydrate_replies
from src.models.engagement import ActionType, PendingAction, GeneratedText
from src.models.feed import PostMetrics
from src.models.post import PostData, Reply


def test_mutual_handles_extraction():
    sections = {
        "7": {
            "accounts": [
                {"account": "@iamAdityaAnjana", "relationship": "friend"},
                {"account": "@AbhinavXJ", "relationship": "friend"},
                {"account": "@NetflixIndia", "relationship": "none"},
            ]
        }
    }
    mutuals = _extract_mutual_handles(sections)
    assert "iamadityaanjana" in mutuals
    assert "abhinavxj" in mutuals
    assert "netflixindia" not in mutuals
    print("  ✓ mutual handles extraction: correct")


async def test_hydrate_replies_node():
    # Setup mock post data
    mock_post = PostData(
        status_id="111",
        author_name="Original Author",
        handle="original",
        text="checking out this luxury farmhouse",
        timestamp="2026-06-01T12:00:00Z",
        metrics=PostMetrics(likes=10, retweets=2, replies=5),
        replies=[
            Reply(
                status_id="222",
                author_name="Stranger",
                handle="stranger1",
                text="is it nice?",
                timestamp="2026-06-01T12:05:00Z",
                likes=1,
            )
        ],
        media_urls=["http://pbs.twimg.com/media/test.jpg"],
    )

    state = {
        "pending_actions": [
            PendingAction(
                action_type=ActionType.REPLY,
                target_status_id="111",
                target_handle="original",
                content=None,
                score=8.5,
                reason="farmhouse post",
            )
        ],
        "thread_contexts": {},
    }

    mock_ctx = MagicMock()
    config = {"configurable": {"browser_context": mock_ctx}}

    # Patch get_post_data to return mock_post
    with patch("src.agent.nodes.hydrate_replies.get_post_data", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_post
        result = await hydrate_replies(state, config)
        
        mock_get.assert_called_once_with(mock_ctx, "111")
        assert "111" in result["thread_contexts"]
        assert result["thread_contexts"]["111"].status_id == "111"
        assert len(result["thread_contexts"]["111"].replies) == 1
        print("  ✓ hydrate_replies node: successfully fetched and cached thread context")


async def test_generate_content_chaining_and_deduplication():
    sections = {
        "7": {
            "accounts": [
                {"account": "@iamAdityaAnjana", "relationship": "friend"},
            ]
        }
    }

    # Thread context contains a reply from our close mutual @iamAdityaAnjana
    thread_contexts = {
        "111": PostData(
            status_id="111",
            author_name="Original Author",
            handle="original",
            text="check out my farmhouse",
            timestamp="2026-06-01T12:00:00Z",
            metrics=PostMetrics(likes=10, retweets=2, replies=5),
            replies=[
                Reply(
                    status_id="222",
                    author_name="Stranger",
                    handle="stranger1",
                    text="nice house",
                    timestamp="2026-06-01T12:05:00Z",
                ),
                Reply(
                    status_id="333",
                    author_name="Aditya A.",
                    handle="iamAdityaAnjana",
                    text="sundar kothi h",
                    timestamp="2026-06-01T12:10:00Z",
                ),
            ],
        )
    }

    action1 = PendingAction(
        action_type=ActionType.REPLY,
        target_status_id="111",
        target_handle="original",
        content=None,
        score=9.0,
        reason="farmhouse post",
    )

    action2 = PendingAction(
        action_type=ActionType.REPLY,
        target_status_id="999",  # Post with no replies, should trigger standard generate
        target_handle="stranger",
        content=None,
        score=7.0,
        reason="random post",
    )

    state = {
        "persona_sections": sections,
        "pending_actions": [action1, action2],
        "source_data_files": [],
        "llm_config": {},
        "thread_contexts": thread_contexts,
    }

    # Mock the LLM structured output
    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    
    # Set mock LLM return values
    mock_structured.invoke.side_effect = [
        GeneratedText(text="crazy. eicher?"),  # Reply text for the pivoted action1
        GeneratedText(text="[SKIP]"),          # Action2 returns SKIP
    ]

    with patch("src.agent.nodes.generate_content.get_llm") as mock_get_llm:
        mock_get_llm.return_value = mock_llm
        
        result = await generate_content(state)
        
        pending_result = result["pending_actions"]
        
        # 1. Chaining Validation
        # action1 targets 111, which has mutual @iamAdityaAnjana at reply 333
        # It must pivot action1 to target 333 instead of 111!
        assert action1.target_status_id == "333"
        assert action1.target_handle == "iamAdityaAnjana"
        assert action1.content == "crazy. eicher?"
        print("  ✓ reply-to-reply chaining: successfully pivoted target to mutual's reply status ID")

        # 2. SKIP Filter Validation
        # action2 returned [SKIP], so it must be stripped from the pending actions list!
        assert action2 not in pending_result
        assert action1 in pending_result
        assert len(pending_result) == 1
        print("  ✓ deduplication skip: successfully filtered out action returned as [SKIP]")


if __name__ == "__main__":
    print("Testing LangGraph Reply Fix Node Suite...\n")
    test_mutual_handles_extraction()
    asyncio.run(test_hydrate_replies_node())
    asyncio.run(test_generate_content_chaining_and_deduplication())
    print("\n✓ All reply node tests passed successfully!")
