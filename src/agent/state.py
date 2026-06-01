from __future__ import annotations

from typing import Any, Optional, TypedDict

from src.models.engagement import ExecutedAction, PendingAction
from src.models.feed import FeedPost
from src.models.scored import ScoredPost
from src.models.post import PostData


class PersonaState(TypedDict):
    persona_file: str
    activity_log_file: str
    llm_config: dict

    persona_sections: dict
    source_data_files: list[str]

    feed_posts: list[FeedPost]
    feed_scroll_position: Optional[str]

    scored_posts: list[ScoredPost]

    pending_actions: list[PendingAction]
    executed_actions: list[ExecutedAction]

    thread_contexts: dict[str, PostData]  # Added for thread reply context

    follow_candidates: list[FeedPost]
    follows_this_session: int

    rate_limit_file: str
    cycle_action_counts: dict[str, int]

    seen_post_ids: list[str]
    engaged_ids: list[str]
    scroll_count: int

    error: Optional[str]

