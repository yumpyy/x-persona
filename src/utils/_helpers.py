"""Shared low-level async helpers used across tool modules.

These are internal utilities (prefixed with ``_`` in the module name).
They handle the repetitive parts of browser automation — clicking,
filling, scrolling, parsing counts — so the public tool modules stay
focused on business logic.
"""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from src.utils.exceptions import (
    XElementNotFoundError,
    XMediaUploadError,
)
from src.utils.mouse import smooth_click

if TYPE_CHECKING:
    from playwright.async_api import ElementHandle, Locator, Page

logger = logging.getLogger("x_persona")


# ---------------------------------------------------------------------------
# Click / fill / type
# ---------------------------------------------------------------------------


async def safe_click(
    page: Page,
    selector: str,
    *,
    timeout: int = 10_000,
    delay_before: float = 0.2,
    delay_after: float = 0.3,
) -> None:
    """Wait for *selector* to be visible, scroll it into view, and click.

    Small pre/post delays improve reliability on X's heavily-animated UI.
    """
    try:
        element = page.locator(selector).first
        await element.wait_for(state="visible", timeout=timeout)
        await element.scroll_into_view_if_needed()
        await asyncio.sleep(delay_before)
        await smooth_click(page, element)
        await asyncio.sleep(delay_after)
    except Exception as exc:
        raise XElementNotFoundError(
            f"Could not click selector '{selector}': {exc}"
        ) from exc


async def safe_fill(
    page: Page,
    selector: str,
    text: str,
    *,
    timeout: int = 10_000,
    clear_first: bool = True,
) -> None:
    """Wait for an input/textarea matching *selector* and fill it."""
    try:
        element = page.locator(selector).first
        await element.wait_for(state="visible", timeout=timeout)
        if clear_first:
            await element.fill("")
        await element.fill(text)
    except Exception as exc:
        raise XElementNotFoundError(
            f"Could not fill selector '{selector}': {exc}"
        ) from exc


async def safe_type(
    page: Page,
    selector: str,
    text: str,
    *,
    timeout: int = 10_000,
    delay_per_char: float = 0.02,
) -> None:
    """Click a content-editable element and type into it keystroke-by-keystroke.

    Used for X's rich-text compose boxes which don't respond to `fill()`.
    """
    try:
        element = page.locator(selector).first
        await element.wait_for(state="visible", timeout=timeout)
        await element.click()
        await asyncio.sleep(0.2)
        await page.keyboard.type(text, delay=delay_per_char)
    except Exception as exc:
        raise XElementNotFoundError(
            f"Could not type into selector '{selector}': {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------


async def extract_text(element: ElementHandle | Locator) -> str:
    """Return the trimmed inner text of an element, or ``""`` if absent."""
    try:
        text = await element.inner_text()
        return (text or "").strip()
    except Exception:
        return ""


async def extract_text_from_page(page: Page, selector: str) -> str:
    """Convenience: wait for *selector* and extract its text."""
    try:
        loc = page.locator(selector).first
        await loc.wait_for(state="attached", timeout=5_000)
        return await extract_text(loc)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Scrolling
# ---------------------------------------------------------------------------


async def scroll_page(page: Page, *, distance: int = 800, pause: float = 1.5) -> None:
    """Scroll down by *distance* pixels and wait for content to settle."""
    await page.evaluate(f"window.scrollBy(0, {distance})")
    await asyncio.sleep(pause)


# ---------------------------------------------------------------------------
# Numeric parsing
# ---------------------------------------------------------------------------

_COUNT_RE = re.compile(r"^([\d,.]+)\s*([KMBkmb])?$")


def parse_count(raw: str) -> int:
    """Parse X-style abbreviated counts into integers.

    Examples::

        >>> parse_count("1.2K")
        1200
        >>> parse_count("3,456")
        3456
        >>> parse_count("2.5M")
        2500000
        >>> parse_count("")
        0
    """
    if not raw:
        return 0

    raw = raw.strip().replace(",", "")
    match = _COUNT_RE.match(raw)
    if not match:
        return 0

    number_str, suffix = match.groups()
    multipliers = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
    multiplier = multipliers.get((suffix or "").lower(), 1)

    try:
        return int(float(number_str) * multiplier)
    except (ValueError, OverflowError):
        return 0


# ---------------------------------------------------------------------------
# Status-ID extraction
# ---------------------------------------------------------------------------

_STATUS_URL_RE = re.compile(r"/status/(\d+)")


def extract_status_id(href: str) -> str | None:
    """Pull the numeric status ID out of a ``/status/<id>`` URL fragment."""
    match = _STATUS_URL_RE.search(href)
    return match.group(1) if match else None


# ---------------------------------------------------------------------------
# Media upload
# ---------------------------------------------------------------------------


async def attach_media(page: Page, file_paths: list[Path], *, timeout: int = 30_000) -> None:
    """Upload media files via the hidden file-input on X's compose UI.

    Waits for each upload to finish by watching for the media thumbnail
    to appear in the compose area.
    """
    if not file_paths:
        return

    # Resolve and validate all paths first
    resolved: list[str] = []
    for fp in file_paths:
        p = Path(fp).resolve()
        if not p.is_file():
            raise XMediaUploadError(f"Media file not found: {p}")
        resolved.append(str(p))

    # X's file input accepts multiple files at once
    file_input = page.locator('input[type="file"]').first
    try:
        await file_input.set_input_files(resolved, timeout=timeout)
    except Exception as exc:
        raise XMediaUploadError(f"Failed to set files on input: {exc}") from exc

    # Wait for media preview thumbnails to appear
    # X renders them as img or video elements inside the compose area
    await asyncio.sleep(2)  # brief settle time for upload processing

    logger.info("Attached %d media file(s)", len(resolved))


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------


async def goto_and_wait(
    page: Page,
    url: str,
    *,
    wait_for: str = "domcontentloaded",
    timeout: int = 30_000,
) -> None:
    """Navigate to *url* and wait for the specified load state."""
    await page.goto(url, wait_until=wait_for, timeout=timeout)
    await asyncio.sleep(1)  # let JS-rendered content hydrate


async def wait_for_toast(page: Page, *, timeout: int = 10_000) -> str:
    """Wait for X's toast notification and return its text.

    Useful for confirming that an action (post, like, etc.) succeeded.
    Returns empty string if no toast appears within the timeout.
    """
    from src.utils.selectors import TOAST_NOTIFICATION

    try:
        toast = page.locator(TOAST_NOTIFICATION).first
        await toast.wait_for(state="visible", timeout=timeout)
        return await extract_text(toast)
    except Exception:
        return ""
