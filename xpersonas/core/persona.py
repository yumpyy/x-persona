"""Persona definition validation and loading."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class Identity(BaseModel):
    handle: str
    display_name: str
    bio: str = ""
    occupation: str = ""
    location: str = ""


class LinguisticStyle(BaseModel):
    lowercase_preference: str = "sometimes"
    punctuation: str = "mixed"
    sentence_length: str = "mixed"
    quirks: list[str] = Field(default_factory=list)


class Linguistic(BaseModel):
    primary_language: str = "en"
    vocabulary: list[dict[str, str]] = Field(default_factory=list)
    emoji_usage: list[dict[str, str]] = Field(default_factory=list)
    slang: list[dict[str, str]] = Field(default_factory=list)
    style: LinguisticStyle = Field(default_factory=LinguisticStyle)


class Personality(BaseModel):
    core_traits: list[str] = Field(default_factory=list)
    humor_style: str = ""
    overall_vibe: str = ""
    never: list[str] = Field(default_factory=list)


class ContentBucket(BaseModel):
    name: str
    frequency_pct: float = 0
    description: str = ""
    example_phrase: str = ""


class Content(BaseModel):
    buckets: list[ContentBucket] = Field(default_factory=list)
    posting_behavior: dict[str, str] = Field(default_factory=dict)


class ReplyStyle(BaseModel):
    baseline: str = ""
    length_matrix: list[dict[str, str]] = Field(default_factory=list)
    escalation_triggers: list[dict[str, str]] = Field(default_factory=list)
    templates: list[dict[str, str]] = Field(default_factory=list)
    argumentative_tendency: str = "moderate"


class TopicStance(BaseModel):
    topic: str
    stance: str = "neutral"
    intensity: float = 5.0
    nuance: str = ""


class RateLimitConfig(BaseModel):
    per_cycle: dict[str, int] = Field(default_factory=lambda: {"like": 5, "reply": 2, "repost": 2, "quote": 1})
    per_hour: dict[str, int] = Field(default_factory=lambda: {"like": 20, "reply": 8, "repost": 8, "quote": 4, "follow": 3})
    per_day: dict[str, int] = Field(default_factory=lambda: {"like": 80, "reply": 30, "repost": 30, "quote": 15, "follow": 15})


class Engagement(BaseModel):
    strategy: str = "active"
    topics: list[TopicStance] = Field(default_factory=list)
    accounts: list[dict[str, str]] = Field(default_factory=list)
    action_types: list[str] = Field(default_factory=lambda: ["like", "reply", "quote", "repost"])
    rate_limits: RateLimitConfig = Field(default_factory=RateLimitConfig)


class PromoConfig(BaseModel):
    enabled: bool = False
    product_ids: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    frequency_cap_per_week: int = 3
    min_account_age_days: int = 90
    min_non_promo_posts: int = 100
    require_disclosure: bool = True


class NetworkingConfig(BaseModel):
    target_connections: list[str] = Field(default_factory=list)
    engagement_style: str = "substantive"
    relationship_stages: dict[str, str] = Field(default_factory=dict)


class EscalationConfig(BaseModel):
    webhook_url: str = ""
    trigger_on: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class PersonaDefinition(BaseModel):
    """Full persona definition: validated on load."""

    id: str = ""
    version: str = "1.0"
    mode: str = "brand"

    identity: Identity
    linguistic: Linguistic = Field(default_factory=Linguistic)
    personality: Personality = Field(default_factory=Personality)
    content: Content = Field(default_factory=Content)
    reply_style: ReplyStyle = Field(default_factory=ReplyStyle)
    engagement: Engagement = Field(default_factory=Engagement)
    platforms: dict[str, dict[str, Any]] = Field(default_factory=dict)
    source_data: list[str] = Field(default_factory=list)
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)
    promo: PromoConfig = Field(default_factory=PromoConfig)
    networking: NetworkingConfig = Field(default_factory=NetworkingConfig)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in ("brand", "personal"):
            raise ValueError(f"mode must be 'brand' or 'personal', got '{v}'")
        return v

    @field_validator("engagement", mode="before")
    @classmethod
    def ensure_engagement(cls, v: dict | Engagement) -> Engagement:
        if isinstance(v, Engagement):
            return v
        return Engagement(**v)


def load_persona_config(data: dict[str, Any]) -> PersonaDefinition:
    """Load and validate a persona config from a dict."""
    return PersonaDefinition.model_validate(data)


def validate_persona_config(data: dict[str, Any]) -> list[str]:
    """Validate a persona config, returning list of errors (empty = valid)."""
    try:
        PersonaDefinition.model_validate(data)
        return []
    except Exception as e:
        return [str(e)]
