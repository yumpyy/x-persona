from __future__ import annotations
from typing import Self
from pydantic import BaseModel, Field
from .feed import PostMetrics


class Reply(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str
    likes: int = 0
    replies: list[Reply] = Field(default_factory=list) # recursive nested replies


class PostData(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str
    metrics: PostMetrics
    replies: list[Reply] = Field(default_factory=list)
    media_urls: list[str] = Field(default_factory=list)


class ActionResult(BaseModel):
    success: bool
    error: str | None = None
    timestamp: str | None = None

    def __bool__(self) -> bool:
        return self.success


class PostResponse(ActionResult):
    url: str | None = None
    status_id: str | None = None

    def __str__(self) -> str:
        return self.status_id or ""
