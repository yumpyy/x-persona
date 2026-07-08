"""Configuration loading with layered resolution."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from xpersonas.core.exceptions import ConfigError


class LLMConfig(BaseModel):
    """LLM configuration. Uses OpenAI-compatible API format.

    Set via env vars: OPENAI_API_KEY, OPENAI_MODEL, OPENAI_BASE_URL.
    Or override per-persona in the persona JSON under "llm".
    """

    model: str
    api_key: str
    base_url: str = ""
    temperature: float = 0.7


class TenantConfig(BaseModel):
    max_personas: int = 10
    max_concurrent_agents: int = 5
    llm: LLMConfig | None = None
    webhook_url: str | None = None


def load_env_config() -> LLMConfig:
    """Load LLM config from environment variables.

    Required: OPENAI_API_KEY, OPENAI_MODEL
    Optional: OPENAI_BASE_URL (for custom endpoints like Ollama, LM Studio, etc.)
    """
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "")
    model = os.getenv("OPENAI_MODEL", "")

    if not api_key or not model:
        raise ConfigError(
            "Missing LLM config. Set OPENAI_API_KEY and OPENAI_MODEL env vars.\n"
            "Example:\n"
            "  export OPENAI_API_KEY=sk-...\n"
            "  export OPENAI_MODEL=your-model\n"
            "\n"
            "For custom OpenAI-compatible endpoints (Ollama, LM Studio, etc.):\n"
            "  export OPENAI_BASE_URL=http://localhost:11434/v1"
        )

    return LLMConfig(
        model=model,
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL", ""),
    )


def resolve_llm_config(
    persona_config: dict[str, Any] | None = None,
    tenant_config: TenantConfig | None = None,
) -> LLMConfig:
    """Merge config with precedence: persona > tenant > env."""
    env = load_env_config()
    base = tenant_config.llm if tenant_config and tenant_config.llm else env

    # Persona-level overrides
    if persona_config and "llm" in persona_config:
        overrides = persona_config["llm"]
        return base.model_copy(update=overrides)

    return base


def load_config_file(path: str | Path) -> dict[str, Any]:
    """Load a JSON or YAML config file."""
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"Config file not found: {p}")
    text = p.read_text()
    if p.suffix in (".yaml", ".yml"):
        import yaml
        return yaml.safe_load(text) or {}
    return json.loads(text)
