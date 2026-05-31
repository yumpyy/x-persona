#!/usr/bin/env python3
"""Test fetching a single post by status_id."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser import BrowserSession
from src.utils.post import get_post_data


async def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python tests/test_post.py <status_id>")
        print("  e.g. uv run python tests/test_post.py 2060820483797332132")
        sys.exit(1)

    status_id = sys.argv[1]

    session = BrowserSession(headless=False)
    ctx = await session.start()
    post = await get_post_data(ctx, status_id)

    print(f"Status:    https://x.com/i/status/{post.status_id}")
    print(f"Author:    {post.author_name} (@{post.handle})")
    print(f"Time:      {post.timestamp}")
    print(f"Text:      {post.text}")
    print(f"Likes:     {post.metrics.likes}")
    print(f"Retweets:  {post.metrics.retweets}")
    print(f"Replies:   {post.metrics.replies}")
    print(f"Views:     {post.metrics.views or '—'}")
    print(f"Bookmarks: {post.metrics.bookmarks}")
    print(f"Images:    {len(post.media_urls)}")
    for i, url in enumerate(post.media_urls):
        print(f"  [{i+1}] {url}")
    print(f"Replies:   {len(post.replies)}")
    for i, r in enumerate(post.replies[:10]):
        _print_reply(r, i + 1, 2)

    await session.stop()


def _print_reply(r, idx: int, indent: int = 2):
    pad = "  " * indent
    print(f"{pad}[{idx}] @{r.handle}")
    print(f"{pad}     Name:      {r.author_name}")
    print(f"{pad}     Status:    https://x.com/i/status/{r.status_id}")
    print(f"{pad}     Time:      {r.timestamp}")
    print(f"{pad}     Likes:     {r.likes}")
    print(f"{pad}     Text:      {r.text}")
    for j, child in enumerate(r.replies[:5]):
        _print_reply(child, j + 1, indent + 2)


if __name__ == "__main__":
    asyncio.run(main())
