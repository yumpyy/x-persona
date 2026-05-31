"""Edit the authenticated user's profile on X.

Navigates to ``x.com/settings/profile`` and updates the specified
fields (name, bio, location, website).  Only provided fields are
changed; ``None`` values are skipped.

Usage::

    page = await bm.get_page("cneuralnetwork")
    success = await edit_profile(page, bio="Building cool stuff 🚀")
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from utils._helpers import goto_and_wait, safe_click, safe_fill
from utils.exceptions import XActionError, XNavigationError
from utils.selectors import (
    EDIT_BIO_TEXTAREA,
    EDIT_LOCATION_INPUT,
    EDIT_NAME_INPUT,
    EDIT_SAVE_BUTTON,
    EDIT_WEBSITE_INPUT,
    PROFILE_EDIT_BUTTON,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

logger = logging.getLogger("x_persona")

_PROFILE_URL = "https://x.com/settings/profile"


async def edit_profile(
    page: Page,
    *,
    name: str | None = None,
    bio: str | None = None,
    location: str | None = None,
    website: str | None = None,
    timeout: int = 30_000,
) -> bool:
    """Update the authenticated user's profile fields.

    Only the fields that are explicitly passed (not ``None``) will be
    changed.  All other fields are left untouched.

    Parameters
    ----------
    page:
        An authenticated Playwright page.
    name:
        New display name.
    bio:
        New bio / description text.
    location:
        New location string.
    website:
        New website URL.
    timeout:
        Maximum time (ms) to wait for the save to complete.

    Returns
    -------
    bool
        ``True`` if the profile was saved successfully.

    Raises
    ------
    XActionError
        If the save fails.
    """
    if all(v is None for v in (name, bio, location, website)):
        logger.warning("edit_profile called with no fields to update")
        return True

    await goto_and_wait(page, _PROFILE_URL)
    logger.info("Editing profile")

    # Wait for the edit form to load
    try:
        await page.locator(EDIT_NAME_INPUT).first.wait_for(
            state="visible", timeout=15_000
        )
    except Exception as exc:
        raise XNavigationError(
            "Profile edit page did not load"
        ) from exc

    # Update each field if provided
    changes: list[str] = []

    if name is not None:
        await safe_fill(page, EDIT_NAME_INPUT, name)
        changes.append(f"name='{name}'")

    if bio is not None:
        await _fill_bio(page, bio)
        changes.append(f"bio='{bio[:30]}…'" if len(bio) > 30 else f"bio='{bio}'")

    if location is not None:
        await safe_fill(page, EDIT_LOCATION_INPUT, location)
        changes.append(f"location='{location}'")

    if website is not None:
        await safe_fill(page, EDIT_WEBSITE_INPUT, website)
        changes.append(f"website='{website}'")

    logger.info("Fields updated: %s", ", ".join(changes))

    # Click Save
    try:
        await safe_click(page, EDIT_SAVE_BUTTON, timeout=5_000)
    except Exception as exc:
        raise XActionError(f"Failed to click Save: {exc}") from exc

    # Wait for the save to complete — X navigates back or shows a toast
    await asyncio.sleep(3)

    logger.info("Profile saved successfully")
    return True


async def _fill_bio(page: Page, text: str) -> None:
    """Fill the bio textarea, handling its special behavior.

    X's bio field is a ``<textarea>`` that may need clearing before
    filling.  We select all existing text first.
    """
    textarea = page.locator(EDIT_BIO_TEXTAREA).first
    await textarea.wait_for(state="visible", timeout=5_000)

    # Triple-click to select all existing text
    await textarea.click(click_count=3)
    await asyncio.sleep(0.2)

    if text:
        await page.keyboard.type(text, delay=0.02)
    else:
        # Clear the field
        await page.keyboard.press("Delete")
