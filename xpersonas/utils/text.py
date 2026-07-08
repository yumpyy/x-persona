"""Shared text utilities."""

from __future__ import annotations

import re


def truncate(text: str, max_len: int = 280) -> str:
    """Truncate text to max_len, respecting word boundaries."""
    if len(text) <= max_len:
        return text
    truncated = text[:max_len].rsplit(" ", 1)[0]
    return truncated + "..."


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def has_superlatives(text: str) -> bool:
    """Check if text contains promotional superlatives."""
    superlatives = [
        "best ever", "game changer", "amazing", "incredible",
        "unbelievable", "revolutionary", "groundbreaking", "mind-blowing",
        "life-changing", "must have", "can't live without",
    ]
    lower = text.lower()
    return any(sp in lower for sp in superlatives)


def extract_handles(text: str) -> list[str]:
    """Extract @handles from text."""
    return re.findall(r"@(\w+)", text)


def extract_hashtags(text: str) -> list[str]:
    """Extract #hashtags from text."""
    return re.findall(r"#(\w+)", text)
