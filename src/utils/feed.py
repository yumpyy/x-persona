import re

from playwright.async_api import BrowserContext, Page

from src.models.feed import FeedPost, FeedResponse, PostMetrics, QuotedPost


def _parse_num(s: str) -> int:
    s = s.lower().replace(",", "")
    return int(float(s.replace("k", "e3").replace("m", "e6")))


async def _parse_article_metrics(article) -> PostMetrics:
    metrics = PostMetrics()

    reply_btn = await article.query_selector('[data-testid="reply"]')
    if reply_btn:
        label = await reply_btn.get_attribute("aria-label") or ""
        m = re.search(r"([\d,.]+[KkMm]?)", label)
        if m:
            metrics.replies = _parse_num(m.group(1))

    retweet_btn = await article.query_selector('[data-testid="retweet"]')
    if retweet_btn:
        label = await retweet_btn.get_attribute("aria-label") or ""
        m = re.search(r"([\d,.]+[KkMm]?)", label)
        if m:
            metrics.retweets = _parse_num(m.group(1))

    like_btn = await article.query_selector('[data-testid="like"]')
    if like_btn:
        label = await like_btn.get_attribute("aria-label") or ""
        m = re.search(r"([\d,.]+[KkMm]?)", label)
        if m:
            metrics.likes = _parse_num(m.group(1))

    bookmark_btn = await article.query_selector('[data-testid="bookmark"]')
    if bookmark_btn:
        label = await bookmark_btn.get_attribute("aria-label") or ""
        m = re.search(r"([\d,.]+[KkMm]?)", label)
        if m:
            metrics.bookmarks = _parse_num(m.group(1))

    views_link = await article.query_selector('a[href*="/analytics"]')
    if views_link:
        label = await views_link.get_attribute("aria-label") or ""
        m = re.search(r"([\d,.]+[KkMm]?)", label)
        if m:
            metrics.views = _parse_num(m.group(1))

    return metrics


async def get_home_feed(
    context: BrowserContext,
    scroll_count: int = 3,
) -> FeedResponse:
    page = context.pages[0] if context.pages else await context.new_page()

    await page.goto("https://x.com/home", wait_until="domcontentloaded")
    await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)

    posts: list[FeedPost] = []

    for _ in range(scroll_count):
        article_els = await page.query_selector_all('article[data-testid="tweet"]')

        for article in article_els:
            try:
                post = await _parse_article(article)
                if post and not any(p.status_id == post.status_id for p in posts):
                    posts.append(post)
            except Exception:
                continue

        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        await page.wait_for_timeout(1500)

    return FeedResponse(posts=posts)


async def _parse_article(article) -> FeedPost | None:
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

    quoted_post = None
    if is_quote:
        qt_el = await article.query_selector('[data-testid="quoteTweet"]')
        if qt_el:
            qt_text_el = await qt_el.query_selector('[data-testid="tweetText"]')
            qt_text = await qt_text_el.inner_text() if qt_text_el else ""
            qt_name_el = await qt_el.query_selector('[data-testid="User-Name"]')
            qt_name = await qt_name_el.inner_text() if qt_name_el else ""
            quoted_post = QuotedPost(
                status_id="",
                author_name=qt_name.split("\n")[0].strip(),
                handle="",
                text=qt_text,
            )

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

    avatar_url = None
    avatar_el = await article.query_selector('img[src*="pbs.twimg.com/profile_images"]')
    if avatar_el:
        avatar_url = await avatar_el.get_attribute("src")

    return FeedPost(
        status_id=status_id,
        author_name=author_name,
        handle=handle,
        text=text,
        timestamp=timestamp or "",
        is_retweet=is_retweet,
        is_quote=is_quote,
        is_reply=is_reply,
        metrics=metrics,
        quoted_post=quoted_post,
        media_urls=media_urls,
        author_avatar_url=avatar_url,
    )


async def navigate_home(page: Page) -> None:
    await page.goto("https://x.com/home", wait_until="domcontentloaded")
    await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)


async def scroll_down(page: Page, times: int = 1) -> None:
    for _ in range(times):
        await page.evaluate("window.scrollBy({ top: window.innerHeight, behavior: 'smooth' })")
        await page.wait_for_timeout(1000)
