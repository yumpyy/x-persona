"""X/Twitter feed parsing and content discovery."""

from __future__ import annotations

import re

from playwright.async_api import Page

from xpersonas.core.models import PlatformPost


def _parse_num(s: str) -> int:
    s = s.lower().replace(",", "")
    return int(float(s.replace("k", "e3").replace("m", "e6")))


async def _parse_article_metrics(article) -> dict[str, int]:
    metrics: dict[str, int] = {}

    for key, testid in [("replies", "reply"), ("reposts", "retweet"), ("likes", "like"), ("bookmarks", "bookmark")]:
        btn = await article.query_selector(f'[data-testid="{testid}"]')
        if btn:
            label = await btn.get_attribute("aria-label") or ""
            m = re.search(r"([\d,.]+[KkMm]?)", label)
            if m:
                metrics[key] = _parse_num(m.group(1))

    views_link = await article.query_selector('a[href*="/analytics"]')
    if views_link:
        label = await views_link.get_attribute("aria-label") or ""
        m = re.search(r"([\d,.]+[KkMm]?)", label)
        if m:
            metrics["views"] = _parse_num(m.group(1))

    return metrics


async def _parse_article(article) -> PlatformPost | None:
    status_link = await article.query_selector('a[href*="/status/"]')
    if not status_link:
        return None

    href = await status_link.get_attribute("href")
    match = re.search(r"/status/(\d+)", href or "")
    if not match:
        return None
    status_id = match.group(1)

    name_el = await article.query_selector('[data-testid="User-Name"]')
    author_name = await name_el.inner_text() if name_el else "Unknown"
    author_name = author_name.split("\n")[0].strip()

    author_verified = False
    if name_el:
        verified_el = await name_el.query_selector('[data-testid="icon-verified"]')
        if verified_el:
            author_verified = True

    handle_el = await article.query_selector('[data-testid="User-Name"] a[tabindex="-1"] span')
    handle_text = await handle_el.inner_text() if handle_el else ""
    handle = handle_text.replace("@", "").strip() or "unknown"

    text_el = await article.query_selector('[data-testid="tweetText"]')
    text = await text_el.inner_text() if text_el else ""

    time_el = await article.query_selector("time")
    timestamp = await time_el.get_attribute("datetime") if time_el else ""

    social_ctx = await article.query_selector('[data-testid="socialContext"]')
    is_retweet = False
    is_reply = False
    if social_ctx:
        ctx_text = (await social_ctx.inner_text()).lower()
        is_retweet = "repost" in ctx_text or "retweet" in ctx_text
        is_reply = "reply" in ctx_text
    is_quote = await article.query_selector('[data-testid="quoteTweet"]') is not None

    metrics = await _parse_article_metrics(article)

    media_urls: list[str] = []
    img_els = await article.query_selector_all('img[src*="pbs.twimg.com/media"]')
    for img in img_els:
        src = await img.get_attribute("src")
        if src:
            media_urls.append(src)
    if not media_urls:
        photo_els = await article.query_selector_all('[data-testid="tweetPhoto"] img')
        for img in photo_els:
            src = await img.get_attribute("src")
            if src:
                media_urls.append(src)

    return PlatformPost(
        id=status_id,
        platform="x",
        author_id=handle,
        author_name=author_name,
        author_handle=handle,
        text=text,
        timestamp=timestamp or "",
        metrics=metrics,
        media_urls=media_urls,
        is_reply=is_reply,
        is_repost=is_retweet,
        is_quote=is_quote,
        author_verified=author_verified,
    )


async def parse_feed_articles(page: Page, limit: int = 20) -> list[PlatformPost]:
    """Parse visible tweet articles from the current page."""
    try:
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
    except Exception:
        return []

    articles = await page.query_selector_all('article[data-testid="tweet"]')
    posts: list[PlatformPost] = []
    for article in articles[:limit]:
        try:
            post = await _parse_article(article)
            if post:
                posts.append(post)
        except Exception:
            continue
    return posts


async def search_posts(page: Page, query: str, limit: int = 20) -> list[PlatformPost]:
    """Search X for posts matching a query."""
    url = f"https://x.com/search?q={query}&src=typed_query&f=live"
    await page.goto(url, wait_until="domcontentloaded")
    try:
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
    except Exception:
        return []

    posts: list[PlatformPost] = []
    articles = await page.query_selector_all('article[data-testid="tweet"]')
    for article in articles[:limit]:
        try:
            post = await _parse_article(article)
            if post:
                posts.append(post)
        except Exception:
            continue
    return posts


async def get_post_detail(page: Page, post_id: str) -> PlatformPost | None:
    """Fetch a single post's details."""
    await page.goto(f"https://x.com/i/status/{post_id}", wait_until="domcontentloaded")
    try:
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
    except Exception:
        return None

    article = await page.query_selector('article[data-testid="tweet"]')
    if article:
        return await _parse_article(article)
    return None


async def get_replies(page: Page, post_id: str, limit: int = 20) -> list[PlatformPost]:
    """Fetch replies on a post."""
    await page.goto(f"https://x.com/i/status/{post_id}", wait_until="domcontentloaded")
    try:
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
    except Exception:
        return []

    try:
        await page.wait_for_function(
            "document.querySelectorAll('article[data-testid=\"tweet\"]').length > 1",
            timeout=5000,
        )
    except Exception:
        pass
    await page.wait_for_timeout(1000)

    all_articles = await page.query_selector_all('article[data-testid="tweet"]')
    reply_articles = all_articles[1:]  # skip the main post

    posts: list[PlatformPost] = []
    for article in reply_articles[:limit]:
        try:
            post = await _parse_article(article)
            if post:
                posts.append(post)
        except Exception:
            continue
    return posts
