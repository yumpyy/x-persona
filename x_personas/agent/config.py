from __future__ import annotations

import os
from typing import Any

from langchain_openai import ChatOpenAI


def get_llm(config: dict) -> ChatOpenAI:
    model = config.get("model") or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY", "")
    base_url = config.get("base_url") or os.getenv("OPENAI_BASE_URL", "")
    temperature = config.get("temperature", 0.7)

    kwargs: dict[str, Any] = {"model": model, "temperature": temperature}
    if api_key:
        kwargs["api_key"] = api_key
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def get_llm_config() -> dict:
    cfg: dict[str, Any] = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    }
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        cfg["api_key"] = api_key
    base_url = os.getenv("OPENAI_BASE_URL", "")
    if base_url:
        cfg["base_url"] = base_url
    return cfg


def get_vlm_config() -> dict | None:
    model = os.getenv("VLM_MODEL")
    if not model:
        return None
    cfg: dict[str, Any] = {"model": model}
    api_key = os.getenv("VLM_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    if api_key:
        cfg["api_key"] = api_key
    base_url = os.getenv("VLM_BASE_URL") or os.getenv("OPENAI_BASE_URL", "")
    if base_url:
        cfg["base_url"] = base_url
    return cfg
