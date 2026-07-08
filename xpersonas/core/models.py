"""Core data models shared across the platform."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    LIKE = "like"
    REPLY = "reply"
    REPOST = "repost"
    QUOTE = "quote"
    FOLLOW = "follow"
    UPVOTE = "upvote"
    ORIGINAL_POST = "original_post"


class PlatformPost(BaseModel):
    """Platform-agnostic post representation."""

    id: str
    platform: str
    author_id: str
    author_name: str
    author_handle: str
    text: str
    timestamp: str
    metrics: dict[str, int] = Field(default_factory=dict)
    media_urls: list[str] = Field(default_factory=list)
    is_reply: bool = False
    is_repost: bool = False
    is_quote: bool = False
    author_verified: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PlatformActionResult(BaseModel):
    """Result of a platform action."""

    success: bool
    platform_id: str | None = None
    url: str | None = None
    error: str | None = None


class PendingAction(BaseModel):
    """An action queued for execution."""

    action_type: ActionType
    target_id: str
    target_author: str
    content: str | None = None
    score: float = 0.0
    reason: str = ""
    is_promo: bool = False
    product_id: str | None = None


class ExecutedAction(BaseModel):
    """A completed action."""

    action: PendingAction
    success: bool
    error: str | None = None
    timestamp: str = ""


class PostDecision(BaseModel):
    """LLM decision for a single post."""

    action_type: list[str] = Field(description="Actions to take: like, reply, quote")
    target_status_id: str
    target_handle: str
    content: str | None = None
    score: float = Field(ge=0, le=10)
    reason: str
    is_critical_critique: bool = False


class EngagementDecisions(BaseModel):
    """LLM response containing decisions for multiple posts."""

    decisions: list[PostDecision]


class GeneratedText(BaseModel):
    """LLM-generated content."""

    text: str


class AuthConfig(BaseModel):
    """Platform authentication configuration."""

    method: str = "browser_session"
    credentials: dict[str, str] = Field(default_factory=dict)
    session_path: str | None = None
