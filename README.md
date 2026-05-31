# x-persona

Playwright-based automation utilities for X (Twitter) persona management.

## Setup

```bash
uv sync
uv run playwright install chromium
```

## First-time login

```bash
uv run x-login
```

## Usage

```python
import asyncio
from utils import BrowserManager, get_home_feed, like, post

async def main():
    async with BrowserManager() as bm:
        page = await bm.get_page("your_handle")
        feed = await get_home_feed(page)
        await like(page, feed[0].post_id, handle=feed[0].author_handle)
        await page.close()

asyncio.run(main())
```
