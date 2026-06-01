#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser import BrowserSession
from src.utils.post import post


async def run_post():
    # Vaibhav's first tweet text selection
    tweet_text = "started category theory for programmers. i hate math. this will be interesting"
    
    print(f"🚀 Preparing to publish original tweet using smooth human emulation:")
    print(f"   📝 Content: \"{tweet_text}\"")
    print(f"   🎨 Custom Obsidian Pointer overlay: ENABLED")
    
    choice = input("\nDo you want to post this live on X now? [y/N]: ").strip().lower()
    if choice not in ("y", "yes"):
        print("❌ Posting cancelled by user.")
        return

    print("\nStarting headed browser session and logging in...")
    async with BrowserSession(headless=False) as ctx:
        print("Navigating to compose post overlay...")
        result = await post(ctx, tweet_text)
        
        if result.success:
            print("\n🎉 Tweet successfully published with smooth human emulated clicks!")
            print(f"   URL: {result.url}")
        else:
            print(f"\n❌ Failed to publish tweet: {result.error}")


if __name__ == "__main__":
    asyncio.run(run_post())
