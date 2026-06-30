from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    LIKE = "like"
    REPLY = "reply"
    REPOST = "repost"
    QUOTE = "quote"


class PendingAction(BaseModel):
    action_type: ActionType
    target_status_id: str
    target_handle: str
    content: Optional[str] = None
    score: float
    reason: str


class ExecutedAction(BaseModel):
    action: PendingAction
    success: bool
    error: Optional[str] = None
    timestamp: str


class PostDecision(BaseModel):
    action_type: list[str] = Field(description="One or more of: like, reply, quote")
    target_status_id: str = Field(description="The post's status ID")
    target_handle: str = Field(description="The author's @handle")
    content: Optional[str] = Field(default=None, description="Text for reply/quote (null for like-only)")
    score: float = Field(description="Relevance score 0-10")
    reason: str = Field(description="One-sentence explanation")
    is_critical_critique: bool = Field(default=False, description="Set to True if this action represents a critical critique, disagreement, correction, or negative reaction targeting a disliked/unaligned topic (e.g. criticizing grinds, courses, framework hype, bloat, or bad programming practices). Otherwise False.")


class EngagementDecisions(BaseModel):
    decisions: list[PostDecision] = Field(description="Engagement decisions for this cycle")


class GeneratedText(BaseModel):
    text: str = Field(description="The reply or quote text in the persona's voice")
