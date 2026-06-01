from typing import Self
from pydantic import BaseModel

from .feed import PostMetrics


class Reply(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str
    likes: int = 0
    replies: list[Self] = [] # replies under replies


class PostData(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str
    metrics: PostMetrics
    replies: list[Reply] = []
    media_urls: list[str] = []


class ActionResult(BaseModel):
    success: bool
    error: str | None = None
    timestamp: str | None = None


class PostResponse(ActionResult):
    url: str | None = None
    status_id: str | None = None
