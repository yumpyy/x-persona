import asyncio
import re

from playwright.async_api import BrowserContext, Page

from x_personas.models.feed import PostMetrics
from x_personas.models.post import ActionResult, PostData, PostResponse, Reply
from x_personas.utils.mouse import smooth_click


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


async def get_post_data(context: BrowserContext, status_id: str) -> PostData:
    page = context.pages[0] if context.pages else await context.new_page()

    url = f"https://x.com/i/status/{status_id}"
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_selector('[data-testid="tweetText"]', timeout=15000)

    name_el = await page.query_selector('[data-testid="User-Name"]')
    author_name = await name_el.inner_text() if name_el else "Unknown"
    author_name = author_name.split("\n")[0].strip()

    handle_el = await page.query_selector('[data-testid="User-Name"] a[tabindex="-1"] span')
    handle_text = await handle_el.inner_text() if handle_el else ""
    handle = handle_text.replace("@", "").strip() or "unknown"

    text_el = await page.query_selector('[data-testid="tweetText"]')
    text = await text_el.inner_text() if text_el else ""

    time_el = await page.query_selector("time")
    timestamp = await time_el.get_attribute("datetime") if time_el else ""

    article = await page.query_selector('article[data-testid="tweet"]')
    if article:
        metrics = await _parse_article_metrics(article)
    else:
        metrics = PostMetrics()

    try:
        await page.wait_for_function(
            "document.querySelectorAll('article[data-testid=\"tweet\"]').length > 1",
            timeout=5000,
        )
    except Exception:
        pass
    await page.wait_for_timeout(1000)

    replies = await _collect_replies(page)

    media_urls: list[str] = []
    img_els = await page.query_selector_all('article[data-testid="tweet"] img[src*="pbs.twimg.com/media"]')
    for img in img_els:
        src = await img.get_attribute("src")
        if src:
            media_urls.append(src)

    return PostData(
        status_id=status_id,
        author_name=author_name,
        handle=handle,
        text=text,
        timestamp=timestamp or "",
        metrics=metrics,
        replies=replies,
        media_urls=media_urls,
    )


async def _collect_replies(page) -> list[Reply]:
    replies: list[Reply] = []

    all_articles = await page.query_selector_all('article[data-testid="tweet"]')
    reply_articles = all_articles[1:]

    for article in reply_articles:
        try:
            reply = await _parse_reply_article(article)
            if reply:
                replies.append(reply)
        except Exception:
            continue

    return replies


async def _parse_reply_article(article) -> Reply | None:
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

    like_btn = await article.query_selector('[data-testid="like"]')
    if like_btn:
        label = await like_btn.get_attribute("aria-label") or ""
        m = re.search(r"([\d,.]+[KkMm]?)", label)
        likes = _parse_num(m.group(1)) if m else 0
    else:
        likes = 0

    return Reply(
        status_id=status_id,
        author_name=author_name,
        handle=handle,
        text=text,
        timestamp=timestamp or "",
        likes=likes,
        replies=[],
    )


async def post(context: BrowserContext, text: str) -> PostResponse:
    """Compose and publish a completely new original post (tweet) on X/Twitter.

    Uses smooth visual mouse movements and high-fidelity clicking.
    """
    page = context.pages[0] if context.pages else await context.new_page()
    try:
        await page.goto("https://x.com/compose/post", wait_until="domcontentloaded")
        
        textarea = page.locator('[data-testid="tweetTextarea_0"]').first
        await textarea.wait_for(state="visible", timeout=15000)
        await page.wait_for_timeout(1000)

        # Smooth glide cursor and click compose area
        await smooth_click(page, textarea)
        await page.wait_for_timeout(500)

        # Type character-by-character naturally to emulate human keystroke profiles
        import random
        for char in text:
            await page.keyboard.type(char)
            await asyncio.sleep(random.uniform(0.015, 0.045))
        await page.wait_for_timeout(1000)

        # Locate the submit button (on compose dialog it is typically tweetButton, fallback to tweetButtonInline)
        submit_btn = page.locator('[data-testid="tweetButton"]').first
        if not await submit_btn.is_visible():
            submit_btn = page.locator('[data-testid="tweetButtonInline"]').first

        # Smooth glide cursor to click submit
        await smooth_click(page, submit_btn)
        await page.wait_for_timeout(3000)

        return PostResponse(
            success=True,
            url=page.url,
            status_id=None,
        )
    except Exception as e:
        return PostResponse(success=False, error=str(e))


async def like(context: BrowserContext, status_id: str) -> ActionResult:
    page = context.pages[0] if context.pages else await context.new_page()

    article = page.locator(f'article:has(a[href*="/status/{status_id}"])')
    await article.wait_for(timeout=15000)

    await page.wait_for_timeout(1000)
    like_btn = article.locator('[data-testid="like"]')
    await like_btn.click()
    await page.wait_for_timeout(1000)

    is_liked = await article.locator('[data-testid="unlike"]').is_visible()
    return ActionResult(success=is_liked)


async def repost(context: BrowserContext, status_id: str) -> ActionResult:
    page = context.pages[0] if context.pages else await context.new_page()

    article = page.locator(f'article:has(a[href*="/status/{status_id}"])')
    await article.wait_for(timeout=15000)

    await page.wait_for_timeout(1000)
    rt_btn = article.locator('[data-testid="retweet"]')
    await rt_btn.click()
    await page.wait_for_timeout(1000)

    repost_option = page.locator('[data-testid="retweetConfirm"]')
    try:
        await repost_option.click(timeout=3000)
    except Exception:
        pass

    await page.wait_for_timeout(1000)
    is_reposted = await article.locator('[data-testid="unretweet"]').is_visible()
    return ActionResult(success=is_reposted)


async def reply(context: BrowserContext, status_id: str, text: str) -> ActionResult:
    page = context.pages[0] if context.pages else await context.new_page()

    article = page.locator(f'article:has(a[href*="/status/{status_id}"])')
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

    import random
    import asyncio
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.01, 0.035))
    await page.wait_for_timeout(1000)

    submit_btn = page.locator('[data-testid="tweetButton"]').filter(visible=True).first
    if not await submit_btn.is_visible():
        submit_btn = page.locator('[data-testid="tweetButtonInline"]').filter(visible=True).first
        
    await smooth_click(page, submit_btn)
    await page.wait_for_timeout(2000)

    return ActionResult(success=True)


async def quote(context: BrowserContext, status_id: str, text: str) -> ActionResult:
    page = context.pages[0] if context.pages else await context.new_page()

    article = page.locator(f'article:has(a[href*="/status/{status_id}"])')
    await article.wait_for(timeout=15000)
    await page.wait_for_timeout(1000)

    rt_btn = article.locator('[data-testid="retweet"]')
    await smooth_click(page, rt_btn)
    await page.wait_for_timeout(1000)

    quote_option = page.get_by_role("menuitem").filter(has_text="Quote")
    try:
        await smooth_click(page, quote_option)
    except Exception:
        return ActionResult(success=False, error="Quote option not found")
    await page.wait_for_timeout(1000)

    textarea = page.locator('[data-testid^="tweetTextarea_"]').filter(visible=True).first
    if not await textarea.is_visible():
        textarea = page.locator('div[role="textbox"]').filter(visible=True).first
        
    await textarea.wait_for(state="visible", timeout=15000)
    await smooth_click(page, textarea)
    await page.wait_for_timeout(500)

    import random
    import asyncio
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.01, 0.035))
    await page.wait_for_timeout(1000)

    submit_btn = page.locator('[data-testid="tweetButton"]').filter(visible=True).first
    if not await submit_btn.is_visible():
        submit_btn = page.locator('[data-testid="tweetButtonInline"]').filter(visible=True).first
        
    await smooth_click(page, submit_btn)
    await page.wait_for_timeout(2000)

    return ActionResult(success=True)


async def open_post_tab(context: BrowserContext, status_id: str) -> Page:
    page = await context.new_page()
    await page.goto(f"https://x.com/i/status/{status_id}", wait_until="domcontentloaded")
    
    from x_personas.utils.feed import detect_current_page
    from x_personas.agent.log import log
    log(f"Page loaded: {detect_current_page(page)}")
    
    await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
    return page


async def like_on_page(page: Page) -> ActionResult:
    article = page.locator('article[data-testid="tweet"]').first
    await article.wait_for(timeout=15000)
    await page.wait_for_timeout(1000)
    like_btn = article.locator('[data-testid="like"]')
    await smooth_click(page, like_btn)
    await page.wait_for_timeout(1000)
    is_liked = await article.locator('[data-testid="unlike"]').is_visible()
    return ActionResult(success=is_liked)


async def repost_on_page(page: Page) -> ActionResult:
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
    is_reposted = await article.locator('[data-testid="unretweet"]').is_visible()
    return ActionResult(success=is_reposted)


async def reply_on_page(page: Page, text: str) -> ActionResult:
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
    
    import random
    import asyncio
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.01, 0.035))
    await page.wait_for_timeout(1000)
    
    submit_btn = page.locator('[data-testid="tweetButton"]').filter(visible=True).first
    if not await submit_btn.is_visible():
        submit_btn = page.locator('[data-testid="tweetButtonInline"]').filter(visible=True).first
        
    await smooth_click(page, submit_btn)
    await page.wait_for_timeout(2000)
    return ActionResult(success=True)


async def quote_on_page(page: Page, text: str) -> ActionResult:
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
        return ActionResult(success=False, error="Quote option not found")
    await page.wait_for_timeout(1000)
    
    textarea = page.locator('[data-testid^="tweetTextarea_"]').filter(visible=True).first
    if not await textarea.is_visible():
        textarea = page.locator('div[role="textbox"]').filter(visible=True).first
        
    await textarea.wait_for(state="visible", timeout=15000)
    await smooth_click(page, textarea)
    await page.wait_for_timeout(500)
    
    import random
    import asyncio
    for char in text:
        await page.keyboard.type(char)
        await asyncio.sleep(random.uniform(0.01, 0.035))
    await page.wait_for_timeout(1000)
    
    submit_btn = page.locator('[data-testid="tweetButton"]').filter(visible=True).first
    if not await submit_btn.is_visible():
        submit_btn = page.locator('[data-testid="tweetButtonInline"]').filter(visible=True).first
        
    await smooth_click(page, submit_btn)
    await page.wait_for_timeout(2000)
    return ActionResult(success=True)
