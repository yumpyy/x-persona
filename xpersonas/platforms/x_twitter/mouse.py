"""Human-like mouse movement for X/Twitter browser automation."""

from __future__ import annotations

import asyncio
import math
import os
import random

from playwright.async_api import Locator, Page

_CURRENT_POSITION = [0.0, 0.0]


def calculate_bezier_path(
    start: tuple[float, float],
    end: tuple[float, float],
    steps: int = 18,
) -> list[tuple[float, float]]:
    x0, y0 = start
    x3, y3 = end
    dx = x3 - x0
    dy = y3 - y0
    distance = math.sqrt(dx**2 + dy**2)

    if distance < 5:
        return [end]

    offset_scale = min(distance * 0.15, 75.0)
    px, py = -dy, dx
    p_len = math.sqrt(px**2 + py**2)
    if p_len > 0:
        px, py = px / p_len, py / p_len
    else:
        px, py = 0.0, 0.0

    offset1 = random.uniform(-offset_scale, offset_scale)
    offset2 = random.uniform(-offset_scale, offset_scale)

    x1 = x0 + dx * 0.33 + px * offset1
    y1 = y0 + dy * 0.33 + py * offset1
    x2 = x0 + dx * 0.66 + px * offset2
    y2 = y0 + dy * 0.66 + py * offset2

    path = []
    for i in range(steps + 1):
        t = i / steps
        t_eased = t * t * (3 - 2 * t)
        x = (1 - t_eased)**3 * x0 + 3 * (1 - t_eased)**2 * t_eased * x1 + 3 * (1 - t_eased) * t_eased**2 * x2 + t_eased**3 * x3
        y = (1 - t_eased)**3 * y0 + 3 * (1 - t_eased)**2 * t_eased * y1 + 3 * (1 - t_eased) * t_eased**2 * y2 + t_eased**3 * y3
        path.append((x, y))

    return path


def generate_human_trajectory(
    start: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    x0, y0 = start
    x3, y3 = end
    dx = x3 - x0
    dy = y3 - y0
    distance = math.sqrt(dx**2 + dy**2)
    steps = max(12, min(30, int(distance / 15)))

    if distance > 180.0 and random.random() < 0.7:
        overshoot_factor = random.uniform(1.02, 1.05)
        xo = x0 + dx * overshoot_factor
        yo = y0 + dy * overshoot_factor
        fast_steps = int(steps * 0.8)
        main_path = calculate_bezier_path(start, (xo, yo), fast_steps)
        correction_steps = max(4, steps - fast_steps)
        correction_path = calculate_bezier_path((xo, yo), end, correction_steps)
        return main_path + correction_path[1:]

    return calculate_bezier_path(start, end, steps)


async def smooth_move(page: Page, target_x: float, target_y: float) -> None:
    if page.is_closed():
        return

    start_x, start_y = _CURRENT_POSITION[0], _CURRENT_POSITION[1]

    if start_x == 0.0 and start_y == 0.0:
        start_x = max(0.0, target_x - random.uniform(100, 180))
        start_y = max(0.0, target_y - random.uniform(100, 180))
        try:
            await page.mouse.move(start_x, start_y)
        except Exception:
            return
        _CURRENT_POSITION[0] = start_x
        _CURRENT_POSITION[1] = start_y

    path = generate_human_trajectory((start_x, start_y), (target_x, target_y))

    for x, y in path:
        if page.is_closed():
            break
        x_jitter = x + random.uniform(-0.8, 0.8)
        y_jitter = y + random.uniform(-0.8, 0.8)
        try:
            await page.mouse.move(x_jitter, y_jitter)
        except Exception:
            pass
        await asyncio.sleep(random.uniform(0.007, 0.015))

    _CURRENT_POSITION[0] = target_x
    _CURRENT_POSITION[1] = target_y


async def smooth_click(page: Page, element_or_selector: str | Locator) -> None:
    if page.is_closed():
        return

    if isinstance(element_or_selector, str):
        locator = page.locator(element_or_selector).first
    else:
        locator = element_or_selector

    try:
        await locator.wait_for(state="visible", timeout=8000)
        await locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.08)

        box = await locator.bounding_box()
        if not box:
            await locator.click()
            return

        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2

        await smooth_move(page, target_x, target_y)
        await asyncio.sleep(random.uniform(0.18, 0.38))

        if not page.is_closed():
            await page.mouse.click(target_x, target_y)
        await asyncio.sleep(0.08)

    except Exception:
        try:
            await locator.click()
        except Exception:
            pass
