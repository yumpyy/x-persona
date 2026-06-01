from __future__ import annotations

import os
from typing import Any


def get_llm(config: dict) -> Any:
    provider = config.get("provider", "openai")
    model = config.get("model", "gpt-4o-mini")
    temperature = config.get("temperature", 0.7)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        api_key = config.get("api_key") or os.getenv("OPENAI_API_KEY")
        base_url = config.get("base_url")
        kwargs: dict[str, Any] = {"model": model, "temperature": temperature}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = config.get("api_key") or os.getenv("ANTHROPIC_API_KEY")
        kwargs = {"model": model, "temperature": temperature}
        if api_key:
            kwargs["api_key"] = api_key
        return ChatAnthropic(**kwargs)

    elif provider == "dashscope":
        from langchain_openai import ChatOpenAI
        model = config.get("model") or os.getenv("DASHSCOPE_MODEL", "deepseek-v4-flash")
        api_key = config.get("api_key") or os.getenv("DASHSCOPE_API_KEY", "")
        base_url = config.get("base_url") or os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        return ChatOpenAI(model=model, api_key=api_key, base_url=base_url, temperature=temperature)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_config(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> dict:
    cfg: dict[str, Any] = {}
    if provider:
        cfg["provider"] = provider
    if model:
        cfg["model"] = model
    if api_key:
        cfg["api_key"] = api_key
    if base_url:
        cfg["base_url"] = base_url

    if "provider" not in cfg:
        dashscope_key = os.getenv("DASHSCOPE_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        
        has_dashscope = dashscope_key and not dashscope_key.startswith("your_")
        has_openai = openai_key and not openai_key.startswith("your_")
        
        if has_dashscope and not has_openai:
            cfg["provider"] = "dashscope"
        elif os.getenv("ANTHROPIC_API_KEY") and not os.getenv("ANTHROPIC_API_KEY", "").startswith("your_") and not has_openai:
            cfg["provider"] = "anthropic"
        else:
            cfg["provider"] = "openai"
    if "model" not in cfg:
        env_key = {
            "openai": "OPENAI_MODEL",
            "anthropic": "ANTHROPIC_MODEL",
            "dashscope": "DASHSCOPE_MODEL"
        }.get(cfg.get("provider"), "")
        cfg["model"] = os.getenv(env_key, "") if env_key else ""
        if not cfg["model"]:
            cfg["model"] = {
                "openai": "gpt-4o-mini",
                "anthropic": "claude-3-5-sonnet-latest",
                "dashscope": "qwen-vl-max"
            }.get(cfg.get("provider"), "gpt-4o-mini")

    return cfg
