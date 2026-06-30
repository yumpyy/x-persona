#!/usr/bin/env python3
"""Verify correct assembly and formatting of multimodal payloads (image URLs) for both decisions and content generation."""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from x_personas.agent.nodes.generate_content import generate_content
from x_personas.agent.nodes.llm_decide import llm_decide
from x_personas.models.engagement import ActionType, EngagementDecisions, PendingAction, PostDecision, GeneratedText
from x_personas.models.feed import FeedPost, PostMetrics
from x_personas.models.post import PostData, Reply


async def test_multimodal_llm_decide():
    # Setup feed post with images
    post = FeedPost(
        status_id="111",
        author_name="Original Author",
        handle="original",
        text="checking out my new Eicher tractor!",
        timestamp="2026-06-01T12:00:00Z",
        media_urls=["https://pbs.twimg.com/media/tractor1.jpg", "https://pbs.twimg.com/media/tractor2.jpg"],
    )

    state = {
        "persona_sections": {"9a": {"farming": 8.0}},
        "feed_posts": [post],
        "engaged_ids": [],
        "llm_config": {},
        "vlm_config": {"model": "gpt-4o"},
        "rate_limit_file": "",
    }

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    
    # Setup mock return decision
    mock_structured.invoke.return_value = EngagementDecisions(decisions=[
        PostDecision(action_type=["like", "reply"], target_status_id="111", target_handle="original", score=8.5, reason="cool tractor")
    ])

    with patch("x_personas.agent.nodes.llm_decide.get_llm") as mock_get_llm, \
         patch("x_personas.agent.nodes.llm_decide._load_template") as mock_load:
        mock_get_llm.return_value = mock_llm
        mock_load.return_value = "System template {persona_sections}"

        result = await llm_decide(state)
        
        # Verify LLM invoke was called
        mock_structured.invoke.assert_called_once()
        args = mock_structured.invoke.call_args[0][0]
        
        # User message content is index 1
        user_message = args[1]
        assert user_message["role"] == "user"
        content_list = user_message["content"]
        
        # Must be a content list (multimodal)
        assert isinstance(content_list, list)
        assert len(content_list) == 3  # Text block + 2 image blocks
        assert content_list[0]["type"] == "text"
        assert content_list[1]["type"] == "image_url"
        assert content_list[1]["image_url"]["url"] == "https://pbs.twimg.com/media/tractor1.jpg"
        assert content_list[2]["type"] == "image_url"
        assert content_list[2]["image_url"]["url"] == "https://pbs.twimg.com/media/tractor2.jpg"
        
        print("  ✓ llm_decide multimodal payload: successfully compiled post image URLs into user content blocks")


async def test_multimodal_generate_content():
    # Hydrated post containing media
    thread_contexts = {
        "111": PostData(
            status_id="111",
            author_name="Original Author",
            handle="original",
            text="check out my farmhouse",
            timestamp="2026-06-01T12:00:00Z",
            metrics=PostMetrics(likes=10, retweets=2, replies=5),
            media_urls=["https://pbs.twimg.com/media/farmhouse.jpg"],
            replies=[]
        )
    }

    action = PendingAction(
        action_type=ActionType.REPLY,
        target_status_id="111",
        target_handle="original",
        content=None,
        score=9.0,
        reason="looks amazing",
    )

    state = {
        "persona_sections": {},
        "pending_actions": [action],
        "source_data_files": [],
        "llm_config": {},
        "vlm_config": {"model": "gpt-4o"},
        "thread_contexts": thread_contexts,
    }

    mock_llm = MagicMock()
    mock_structured = MagicMock()
    mock_llm.with_structured_output.return_value = mock_structured
    
    mock_structured.invoke.return_value = GeneratedText(text="sundar kothi h")

    with patch("x_personas.agent.nodes.generate_content.get_llm") as mock_get_llm:
        mock_get_llm.return_value = mock_llm
        
        result = await generate_content(state)
        
        mock_structured.invoke.assert_called_once()
        args = mock_structured.invoke.call_args[0][0]
        
        user_message = args[1]
        assert user_message["role"] == "user"
        content_list = user_message["content"]
        
        assert isinstance(content_list, list)
        assert len(content_list) == 2  # Text block + 1 image block
        assert content_list[0]["type"] == "text"
        assert content_list[1]["type"] == "image_url"
        assert content_list[1]["image_url"]["url"] == "https://pbs.twimg.com/media/farmhouse.jpg"
        
        print("  ✓ generate_content multimodal payload: successfully compiled thread image URLs into generator content blocks")


if __name__ == "__main__":
    print("Testing Multimodal Media Context Suite...\n")
    asyncio.run(test_multimodal_llm_decide())
    asyncio.run(test_multimodal_generate_content())
    print("\n✓ Multimodal media tests passed successfully!")
