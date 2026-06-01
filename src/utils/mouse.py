"""Sleek, Human-Like Mouse Movements & High-Fidelity Showcase Cursor Overlay.

Simulates natural human-hand cursor movements in Playwright using cubic Bezier
curves, Fitts's Law deceleration easing, muscle micro-jitter, and target
overshooting for longer distances. Also injects a beautiful, Figma-style
indigo cursor with a glowing halo and expanding concentric touch-ripples
on clicks for premium headed showcases.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
from typing import Any

from playwright.async_api import Locator, Page

logger = logging.getLogger("x_persona")

# Module-level variable tracking the current coordinate of the virtual mouse
_CURRENT_POSITION = [0.0, 0.0]


async def ensure_cursor_overlay(page: Page) -> None:
    """Inject a pixel-perfect, hyper-realistic Obsidian cursor into the page DOM.

    Ensures the cursor is visible in headed showcases and is automatically
    re-injected if the DOM reloads or is modified.
    """
    try:
        if page.is_closed():
            return

        exists = await page.evaluate("() => !!document.getElementById('fake-cursor')")
        if not exists:
            # Styled using modern, pixel-perfect obsidian cursor design matching premium OS pointers
            script = """
            (() => {
                if (document.getElementById('fake-cursor')) return;
                const cursor = document.createElement('div');
                cursor.id = 'fake-cursor';
                cursor.style.position = 'fixed';
                cursor.style.width = '24px';
                cursor.style.height = '24px';
                cursor.style.pointerEvents = 'none';
                cursor.style.zIndex = '999999999';
                cursor.style.transform = 'translate(0px, 0px)'; // exact tip alignment
                cursor.style.left = '0px';
                cursor.style.top = '0px';

                // High-fidelity Obsidian/Carbon cursor design (sleek dark body, white outline, premium shadow)
                cursor.innerHTML = `
                    <svg id="cursor-svg" width="22" height="22" viewBox="0 0 24 24" fill="none" style="
                        position: absolute;
                        top: 0;
                        left: 0;
                        filter: drop-shadow(0px 2.5px 4.5px rgba(0, 0, 0, 0.42));
                        transition: transform 0.12s cubic-bezier(0.16, 1, 0.3, 1);
                        transform-origin: 0 0;
                    ">
                        <path d="M4.5 3V20.62L9.62 15.5H18.75L4.5 3Z" fill="#1E1E1E" stroke="white" stroke-width="1.8" stroke-linejoin="round"/>
                    </svg>
                `;
                document.body.appendChild(cursor);
            })()
            """
            await page.evaluate(script)
    except Exception:
        # Gracefully handle detached frames or navigation races
        pass


async def trigger_click_effect(page: Page) -> None:
    """Inject and animate an expanding concentric touch-ripple centered on the cursor.

    Gives a highly polished visual indicator in headed recordings.
    """
    try:
        if page.is_closed():
            return

        script = """
        (() => {
            const cursor = document.getElementById('fake-cursor');
            if (!cursor) return;

            // Tactile scale animation on the cursor SVG itself
            const svg = document.getElementById('cursor-svg');
            if (svg) {
                svg.style.transform = 'scale(0.82)';
                setTimeout(() => {
                    svg.style.transform = 'scale(1)';
                }, 120);
            }

            // Dual high-fidelity concentric ripples centered exactly at the pointer tip (0, 0)
            const ripple1 = document.createElement('div');
            ripple1.style.position = 'absolute';
            ripple1.style.left = '0px';
            ripple1.style.top = '0px';
            ripple1.style.width = '8px';
            ripple1.style.height = '8px';
            ripple1.style.borderRadius = '50%';
            ripple1.style.border = '1.8px solid rgba(79, 70, 229, 0.4)';
            ripple1.style.background = 'rgba(79, 70, 229, 0.04)';
            ripple1.style.transform = 'translate(-50%, -50%) scale(0.5)';
            ripple1.style.opacity = '1';
            ripple1.style.pointerEvents = 'none';
            ripple1.style.transition = 'transform 0.38s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.38s';
            cursor.appendChild(ripple1);

            const ripple2 = document.createElement('div');
            ripple2.style.position = 'absolute';
            ripple2.style.left = '0px';
            ripple2.style.top = '0px';
            ripple2.style.width = '8px';
            ripple2.style.height = '8px';
            ripple2.style.borderRadius = '50%';
            ripple2.style.border = '1px solid rgba(15, 23, 42, 0.18)';
            ripple2.style.background = 'transparent';
            ripple2.style.transform = 'translate(-50%, -50%) scale(0.5)';
            ripple2.style.opacity = '1';
            ripple2.style.pointerEvents = 'none';
            ripple2.style.transition = 'transform 0.48s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.48s';
            
            // Stagger the second ripple slightly for a premium, multi-layered fluid appearance
            setTimeout(() => {
                if (cursor.contains(ripple2)) {
                    ripple2.style.transform = 'translate(-50%, -50%) scale(3.5)';
                    ripple2.style.opacity = '0';
                }
            }, 50);

            cursor.appendChild(ripple2);

            // Animate ripple1 on the next tick
            setTimeout(() => {
                ripple1.style.transform = 'translate(-50%, -50%) scale(5.5)';
                ripple1.style.opacity = '0';
            }, 10);

            // Cleanup after animation completes
            setTimeout(() => {
                ripple1.remove();
                ripple2.remove();
            }, 600);
        })()
        """
        await page.evaluate(script)
    except Exception:
        pass


def calculate_bezier_path(
    start: tuple[float, float],
    end: tuple[float, float],
    steps: int = 18,
) -> list[tuple[float, float]]:
    """Calculate intermediate coordinates along a cubic Bezier curve.

    Incorporates randomized perpendular control points to generate natural arm
    swing arcs and applies Fitts's Law deceleration easing.
    """
    x0, y0 = start
    x3, y3 = end

    dx = x3 - x0
    dy = y3 - y0
    distance = math.sqrt(dx**2 + dy**2)

    if distance < 5:
        return [end]

    # Natural offset scaled dynamically to travel distance
    offset_scale = min(distance * 0.15, 75.0)

    # Perpendicular vector to the straight line
    px, py = -dy, dx
    p_len = math.sqrt(px**2 + py**2)
    if p_len > 0:
        px, py = px / p_len, py / p_len
    else:
        px, py = 0.0, 0.0

    offset1 = random.uniform(-offset_scale, offset_scale)
    offset2 = random.uniform(-offset_scale, offset_scale)

    # Control points placed 1/3 and 2/3 along the straight line, offset perpendicularly
    x1 = x0 + dx * 0.33 + px * offset1
    y1 = y0 + dy * 0.33 + py * offset1

    x2 = x0 + dx * 0.66 + px * offset2
    y2 = y0 + dy * 0.66 + py * offset2

    path = []
    for i in range(steps + 1):
        t = i / steps
        # Deceleration curve (Fitts's Law easing)
        t_eased = t * t * (3 - 2 * t)

        # Cubic Bezier interpolation
        x = (1 - t_eased)**3 * x0 + 3 * (1 - t_eased)**2 * t_eased * x1 + 3 * (1 - t_eased) * t_eased**2 * x2 + t_eased**3 * x3
        y = (1 - t_eased)**3 * y0 + 3 * (1 - t_eased)**2 * t_eased * y1 + 3 * (1 - t_eased) * t_eased**2 * y2 + t_eased**3 * y3
        path.append((x, y))

    return path


def generate_human_trajectory(
    start: tuple[float, float],
    end: tuple[float, float],
) -> list[tuple[float, float]]:
    """Generate a highly authentic human trajectory, incorporating overshooting for longer distances."""
    x0, y0 = start
    x3, y3 = end

    dx = x3 - x0
    dy = y3 - y0
    distance = math.sqrt(dx**2 + dy**2)

    # Determine steps based on distance
    steps = max(12, min(30, int(distance / 15)))

    # Fitts's Law target overshooting for longer motions (>180px)
    # Humans naturally slightly overshoot rapid movements and correct back
    if distance > 180.0 and random.random() < 0.7:
        # Calculate overshoot coordinate (2-4% past the destination)
        overshoot_factor = random.uniform(1.02, 1.05)
        xo = x0 + dx * overshoot_factor
        yo = y0 + dy * overshoot_factor

        # Main fast path to the overshoot coordinate
        fast_steps = int(steps * 0.8)
        main_path = calculate_bezier_path(start, (xo, yo), fast_steps)

        # Delicate correction path back onto the exact target
        correction_steps = max(4, steps - fast_steps)
        correction_path = calculate_bezier_path((xo, yo), end, correction_steps)

        return main_path + correction_path[1:]

    return calculate_bezier_path(start, end, steps)


async def smooth_move(page: Page, target_x: float, target_y: float) -> None:
    """Glide the cursor smoothly from its current coordinate to (target_x, target_y).

    Applies muscle micro-jitter and updates the visual fake cursor elements.
    """
    if page.is_closed():
        return

    start_x, start_y = _CURRENT_POSITION[0], _CURRENT_POSITION[1]

    # Safe initial snap to prevent unrealistic visual sweeps from (0,0)
    if start_x == 0.0 and start_y == 0.0:
        start_x = max(0.0, target_x - random.uniform(100, 180))
        start_y = max(0.0, target_y - random.uniform(100, 180))
        try:
            await page.mouse.move(start_x, start_y)
        except Exception:
            return
        _CURRENT_POSITION[0] = start_x
        _CURRENT_POSITION[1] = start_y

    await ensure_cursor_overlay(page)

    path = generate_human_trajectory((start_x, start_y), (target_x, target_y))

    for x, y in path:
        if page.is_closed():
            break

        # Subtle micro-jitter to simulate muscle movement
        x_jitter = x + random.uniform(-0.8, 0.8)
        y_jitter = y + random.uniform(-0.8, 0.8)

        try:
            await page.mouse.move(x_jitter, y_jitter)
            
            # Position the visual fake cursor
            await page.evaluate(
                f"((x, y) => {{ const cursor = document.getElementById('fake-cursor'); if (cursor) {{ cursor.style.left = x + 'px'; cursor.style.top = y + 'px'; }} }})({x_jitter}, {y_jitter})"
            )
        except Exception:
            # Handle page navigations during movement loops
            pass

        # Human neuromuscular latency interval
        await asyncio.sleep(random.uniform(0.007, 0.015))

    _CURRENT_POSITION[0] = target_x
    _CURRENT_POSITION[1] = target_y


async def smooth_click(page: Page, element_or_selector: str | Locator) -> None:
    """Glide the cursor to the element center, trigger touch-ripples, and perform a physical click."""
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
            # Fallback to direct clicking if bounding box not in DOM
            await locator.click()
            return

        # Calculate coordinate center
        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2

        # Execute smooth human glide
        await smooth_move(page, target_x, target_y)

        # Variable human hover delay before clicking
        await asyncio.sleep(random.uniform(0.18, 0.38))

        # Visual click ripple animation
        await trigger_click_effect(page)
        await asyncio.sleep(0.04)

        # Trigger actual click event
        if not page.is_closed():
            await page.mouse.click(target_x, target_y)
        await asyncio.sleep(0.08)
        
    except Exception as e:
        logger.debug("Failed during smooth click: %s", e)
        try:
            # Final fallback to standard locator click
            await locator.click()
        except Exception:
            pass


async def smooth_hover(page: Page, element_or_selector: str | Locator) -> None:
    """Glide the cursor smoothly to hover over the element center."""
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
            await locator.hover()
            return

        target_x = box["x"] + box["width"] / 2
        target_y = box["y"] + box["height"] / 2

        await smooth_move(page, target_x, target_y)
        await asyncio.sleep(0.15)
        
    except Exception as e:
        logger.debug("Failed during smooth hover: %s", e)
        try:
            await locator.hover()
        except Exception:
            pass
