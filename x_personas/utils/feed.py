import re

from playwright.async_api import BrowserContext, Page

from x_personas.models.feed import FeedPost, FeedResponse, PostMetrics, QuotedPost


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
        author_verified=author_verified,
    )


def detect_current_page(page: Page) -> str:
    url = page.url
    if "x.com/home" in url or "twitter.com/home" in url:
        return "Home Feed"
    elif "/status/" in url:
        match = re.search(r"/status/(\d+)", url)
        status_id = match.group(1) if match else "Unknown"
        return f"Tweet Detail (ID: {status_id})"
    elif "x.com/i/flow/login" in url or "x.com/login" in url:
        return "Login Screen"
    elif "x.com/notifications" in url:
        return "Notifications"
    elif "x.com/messages" in url:
        return "Direct Messages"
    elif "x.com/bookmarks" in url:
        return "Bookmarks"
    elif "x.com/search" in url:
        return "Search Page"
    elif "x.com/settings" in url:
        return "Settings"
    elif "x.com/compose/post" in url:
        return "Post Compose Dialog"
    else:
        parsed_path = url.replace("https://", "").replace("http://", "").split("/")
        if len(parsed_path) > 1:
            potential_handle = parsed_path[1].split("?")[0]
            if potential_handle and potential_handle not in (
                "home", "explore", "notifications", "messages", "bookmarks", "settings", "i", "search"
            ):
                return f"Profile Page (@{potential_handle})"
        return f"Unknown Page ({url})"


async def navigate_home(page: Page) -> None:
    await page.goto("https://x.com/home", wait_until="domcontentloaded")
    
    from x_personas.agent.log import log
    log(f"Page loaded: {detect_current_page(page)}")
    
    # Fast path: check if tweets load within 5 seconds initially
    try:
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=5000)
        return
    except Exception:
        pass

    # Timeline failed to load within 5 seconds (could be logged out, slow network, or landing page redirect)
    print("\n" + "!" * 80)
    print("⚠️  X TIMELINE LOAD TIMEOUT (COULD BE LOGGED OUT OR SLOW NETWORK)")
    print("👉 If you are logged out, please log in manually in the visible headed browser window.")
    print("👉 The agent will automatically resume once the timeline is loaded successfully.")
    print("!" * 80 + "\n")

    # Poll for the timeline to load for up to 120 seconds
    max_poll_seconds = 120
    for sec in range(1, max_poll_seconds + 1):
        if page.is_closed():
            raise RuntimeError("Browser tab was closed during login waiting.")

        # Check if timeline tweets are now visible
        if await page.locator('article[data-testid="tweet"]').first.is_visible():
            print("\n✅ Session successfully authenticated and loaded! Resuming agent loops...")
            try:
                await page.context.storage_state(path="auth.json")
                print("💾 Saved new authenticated session cookies to auth.json")
            except Exception as save_err:
                print(f"⚠️  Could not save auth.json state: {save_err}")
            return

        if sec % 10 == 0:
            print(f"⏱️  Still waiting for timeline to load... ({sec}/{max_poll_seconds}s passed)")

        await page.wait_for_timeout(1000)

    raise TimeoutError("Failed to load timeline or authenticate session within 120 seconds.")


async def scroll_down(page: Page, times: int = 1) -> None:
    for _ in range(times):
        await page.evaluate("window.scrollBy({ top: window.innerHeight, behavior: 'smooth' })")
        await page.wait_for_timeout(1000)
