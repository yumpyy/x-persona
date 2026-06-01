from pydantic import BaseModel
from src.models.feed import FeedPost


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
