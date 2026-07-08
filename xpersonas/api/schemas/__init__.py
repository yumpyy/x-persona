"""API request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str
    mode: str = "brand"
    config: dict = Field(default_factory=dict)


class TenantResponse(BaseModel):
    id: str
    name: str
    mode: str
    config: dict
    is_active: bool
    created_at: str


class PersonaCreate(BaseModel):
    platform: str = "x"
    handle: str
    display_name: str = ""
    config: dict = Field(..., description="Full PersonaDefinition JSON")


class PersonaResponse(BaseModel):
    id: str
    tenant_id: str
    platform: str
    handle: str
    display_name: str
    strategy: str
    is_active: bool
    created_at: str
    updated_at: str


class AgentStartRequest(BaseModel):
    visible: bool = False
    scroll_limit: int = 2500
    ask_mode: bool = False


class AgentStatusResponse(BaseModel):
    persona_id: str
    status: str
    strategy: str
    cycles_completed: int
    started_at: str | None
    last_cycle_at: str | None
    error_message: str | None


class ActivityLogEntry(BaseModel):
    id: int
    timestamp: str
    platform: str
    action_type: str
    target_post_id: str
    target_author: str | None
    content: str | None
    score: float | None
    reason: str | None
    success: bool
    error: str | None


class ActivityStats(BaseModel):
    total_actions: int
    actions_by_type: dict[str, int]
    success_rate: float
    actions_last_24h: int


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    features: list[str] = Field(default_factory=list)
    pricing: str = ""
    buy_url: str = ""
    pain_points: list[str] = Field(default_factory=list)
    disclosure_rules: dict = Field(default_factory=dict)
    frequency_cap_per_week: int = 3
    cooldown_days: int = 90


class ProductResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str
    features: list[str]
    pricing: str
    buy_url: str
    pain_points: list[str]
    frequency_cap_per_week: int
    is_active: bool
    created_at: str


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    platforms: list[str]
