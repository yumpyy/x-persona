# Pydantic Models Reference

All models are in `x_personas/models/`.

---

## Engagement (`engagement.py`)

Central models for the engagement decision pipeline.

```python
class ActionType(str, Enum):
    LIKE = "like"
    REPLY = "reply"
    REPOST = "repost"
    QUOTE = "quote"

class PendingAction(BaseModel):
    action_type: ActionType
    target_status_id: str
    target_handle: str
    content: str | None = None      # Text for reply/quote, None for like/repost
    score: float                    # Relevance score 0-10
    reason: str                     # One-sentence explanation from LLM

class ExecutedAction(BaseModel):
    action: PendingAction           # The original pending action
    success: bool                   # Whether execution succeeded
    error: str | None = None        # Error message if failed
    timestamp: str                  # ISO timestamp of execution

# LLM structured output models:

class PostDecision(BaseModel):
    action_type: list[str]          # e.g. ["like"], ["reply", "like"]
    target_status_id: str
    target_handle: str
    content: str | None = None
    score: float                    # 0-10 relevance
    reason: str
    is_critical_critique: bool = False  # Flag for critique variety policy

class EngagementDecisions(BaseModel):
    decisions: list[PostDecision]

class GeneratedText(BaseModel):
    text: str                       # Generated reply/quote text in persona voice
```

**Flow:** `PostDecision[]` (LLM) → `PendingAction[]` (after rate limit enforcement) → `ExecutedAction[]` (after browser execution).

---

## Feed (`feed.py`)

Models for scraped feed posts.

```python
class PostMetrics(BaseModel):
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int | None = None
    bookmarks: int = 0

class QuotedPost(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str | None = None
    metrics: PostMetrics | None = None

class FeedPost(BaseModel):
    status_id: str                  # Numeric tweet ID
    author_name: str                # Display name
    handle: str                     # @handle
    text: str                       # Tweet text content
    timestamp: str                  # ISO datetime
    is_retweet: bool = False
    is_quote: bool = False
    is_reply: bool = False
    is_pinned: bool = False
    is_sponsored: bool = False
    metrics: PostMetrics = PostMetrics()
    quoted_post: QuotedPost | None = None
    media_urls: list[str] = []      # Image URLs
    author_avatar_url: str | None = None
    author_verified: bool = False   # X Premium/Verified

class FeedResponse(BaseModel):
    posts: list[FeedPost]
    scroll_position: str | None = None
```

---

## Post (`post.py`)

Models for individual post data and action results.

```python
class Reply(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str
    likes: int = 0
    replies: list[Reply] = []       # Nested reply chain

class PostData(BaseModel):
    status_id: str
    author_name: str
    handle: str
    text: str
    timestamp: str
    metrics: PostMetrics
    replies: list[Reply] = []       # Collected thread replies
    media_urls: list[str] = []

class ActionResult(BaseModel):
    success: bool
    error: str | None = None
    timestamp: str | None = None

class PostResponse(ActionResult):   # For new posts
    url: str | None = None
    status_id: str | None = None
```

---

## Profile (`profile.py`)

```python
class ProfileStats(BaseModel):
    handle: str
    display_name: str
    bio: str = ""
    location: str | None = None
    website: str | None = None
    followers: int = 0
    following: int = 0
    posts_count: int = 0
    joined: str = ""
    verified: bool = False

class MediaAttachment(BaseModel):
    file_path: Path
```

---

## Scored (`scored.py`)

```python
class ScoreBreakdown(BaseModel):
    topic_affinity: float
    account_relationship: float
    format_affinity: float
    recency_bonus: float
    final_score: float

class ScoredPost(BaseModel):
    post: FeedPost
    score: float
    breakdown: ScoreBreakdown
```

---

## Log (`log.py`)

```python
class ActivityLogEntry(BaseModel):
    timestamp: str
    action: str
    target: str
    content: str | None = None
    score: float
    context: str

class ActivityLog(BaseModel):
    entries: list[ActivityLogEntry]
    activity_log_file: str
```
