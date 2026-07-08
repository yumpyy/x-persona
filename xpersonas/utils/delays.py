"""Shared delay utilities."""

from __future__ import annotations

import asyncio
import random


async def random_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    """Sleep for a random duration."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def short_delay() -> None:
    """Short pause (0.5-1.5s)."""
    await random_delay(0.5, 1.5)


async def medium_delay() -> None:
    """Medium pause (1.5-4s)."""
    await random_delay(1.5, 4.0)


async def long_delay() -> None:
    """Long pause (5-15s)."""
    await random_delay(5.0, 15.0)


def jitter(value: float, pct: float = 0.2) -> float:
    """Add jitter to a value. Returns value +/- pct."""
    delta = value * pct
    return value + random.uniform(-delta, delta)
