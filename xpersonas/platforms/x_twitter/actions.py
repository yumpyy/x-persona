"""X/Twitter page-based action implementations."""

from __future__ import annotations

import asyncio
import random

from playwright.async_api import Page

from xpersonas.platforms.x_twitter.mouse import smooth_click


async def like_on_page(page: Page) -> bool:
    """Like the first tweet on the page."""
    article = page.locator('article[data-testid="tweet"]').first
    await article.wait_for(timeout=15000)
    await page.wait_for_timeout(1000)
    like_btn = article.locator('[data-testid="like"]')
    await smooth_click(page, like_btn)
    await page.wait_for_timeout(1000)
    return await article.locator('[data-testid="unlike"]').is_visible()


async def repost_on_page(page: Page) -> bool:
    """Repost the first tweet on the page."""
    article = page.locator('article[data-testid="tweet"]').first
    await article.wait_for(timeout=15000)
    await page.wait_for_timeout(1000)
    rt_btn = article.locator('[data-testid="retweet"]')
    await smooth_click(page, rt_btn)
    await page.wait_for_timeout(1000)
    repost_option = page.locator('[data-testid="retweetConfirm"]')
    try:
        await smooth_click(page, repost_option)
    except Exception:
        pass
    await page.wait_for_timeout(1000)
    return await article.locator('[data-testid="unretweet"]').is_visible()


async def reply_on_page(page: Page, text: str) -> bool:
    """Reply to the first tweet on the page."""
    article = page.locator('article[data-testid="tweet"]').first
    await article.wait_for(timeout=15000)
    await page.wait_for_timeout(1000)

    reply_btn = article.locator('[data-testid="reply"]')
    await smooth_click(page, reply_btn)
    await page.wait_for_timeout(1000)

    textarea = page.locator('[data-testid^="tweetTextarea_"]').filter(visible=True).first
    if not await textarea.is_visible():
        textarea = page.locator('div[role="textbox"]').filter(visible=True).first

    await textarea.wait_for(state="visible", timeout=15000)
    await smooth_click(page, textarea)
    await page.wait_for_timeout(500)

    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.01, 0.035))
    await page.wait_for_timeout(1000)

    submit_btn = page.locator('[data-testid="tweetButton"]').filter(visible=True).first
    if not await submit_btn.is_visible():
        submit_btn = page.locator('[data-testid="tweetButtonInline"]').filter(visible=True).first

    await smooth_click(page, submit_btn)
    await page.wait_for_timeout(2000)
    return True


async def quote_on_page(page: Page, text: str) -> bool:
    """Quote the first tweet on the page."""
    article = page.locator('article[data-testid="tweet"]').first
    await article.wait_for(timeout=15000)
    await page.wait_for_timeout(1000)

    rt_btn = article.locator('[data-testid="retweet"]')
    await smooth_click(page, rt_btn)
    await page.wait_for_timeout(1000)

    quote_option = page.get_by_role("menuitem").filter(has_text="Quote")
    try:
        await smooth_click(page, quote_option)
    except Exception:
        return False
    await page.wait_for_timeout(1000)

    textarea = page.locator('[data-testid^="tweetTextarea_"]').filter(visible=True).first
    if not await textarea.is_visible():
        textarea = page.locator('div[role="textbox"]').filter(visible=True).first

    await textarea.wait_for(state="visible", timeout=15000)
    await smooth_click(page, textarea)
    await page.wait_for_timeout(500)

    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.01, 0.035))
    await page.wait_for_timeout(1000)

    submit_btn = page.locator('[data-testid="tweetButton"]').filter(visible=True).first
    if not await submit_btn.is_visible():
        submit_btn = page.locator('[data-testid="tweetButtonInline"]').filter(visible=True).first

    await smooth_click(page, submit_btn)
    await page.wait_for_timeout(2000)
    return True


async def follow_on_page(page: Page) -> bool:
    """Follow the author of the first tweet on the page."""
    article = page.locator('article[data-testid="tweet"]').first
    await article.wait_for(timeout=15000)
    await page.wait_for_timeout(1000)

    follow_btn = article.locator('button[data-testid$="-follow"]')
    try:
        await smooth_click(page, follow_btn)
        await page.wait_for_timeout(1000)
        return True
    except Exception:
        return False


async def post_on_page(page: Page, text: str) -> str | None:
    """Compose and publish a new original post."""
    await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")

    textarea = page.locator('[data-testid="tweetTextarea_0"]').first
    await textarea.wait_for(state="visible", timeout=15000)
    await page.wait_for_timeout(1000)

    await smooth_click(page, textarea)
    await page.wait_for_timeout(500)

    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.015, 0.045))
    await page.wait_for_timeout(1000)

    submit_btn = page.locator('[data-testid="tweetButton"]').first
    if not await submit_btn.is_visible():
        submit_btn = page.locator('[data-testid="tweetButtonInline"]').first

    await smooth_click(page, submit_btn)
    await page.wait_for_timeout(3000)
    return None


async def open_post_tab(page: Page, status_id: str) -> Page:
    """Navigate to a specific post URL."""
    await page.goto(f"https://x.com/i/status/{status_id}", wait_until="domcontentloaded")
    await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
    return page
