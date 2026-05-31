from pydantic import BaseModel, Field


class PostMetrics(BaseModel):
    likes: int = Field(default=0)
    retweets: int = Field(default=0)
    replies: int = Field(default=0)
    views: int | None = Field(default=None)
    bookmarks: int = Field(default=0)


class QuotedPost(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str | None = None
    metrics: PostMetrics | None = None


class FeedPost(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str
    is_retweet: bool = False
    is_quote: bool = False
    is_reply: bool = False
    is_pinned: bool = False
    is_sponsored: bool = False
    metrics: PostMetrics = Field(default_factory=PostMetrics)
    quoted_post: QuotedPost | None = None
    media_urls: list[str] = Field(default_factory=list)
    author_avatar_url: str | None = None


class FeedResponse(BaseModel):
    posts: list[FeedPost]
    scroll_position: str | None = None
