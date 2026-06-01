#!/usr/bin/env python3
"""Visually test smooth human mouse movements and visual fake cursor overlay on a live headed browser."""

import asyncio
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.browser import BrowserSession
from src.utils.mouse import smooth_click, smooth_move, ensure_cursor_overlay, trigger_click_effect


async def run_visual_test():
    print("Launching headed browser session...")
    
    # We default to headless=False (headed) to show the visual mouse movement on screen!
    # If in a headless server environment, you can pass --headless CLI argument.
    headless = "--headless" in sys.argv
    
    print(f"Browser mode: {'HEADLESS' if headless else 'HEADED'}")
    
    async with BrowserSession(headless=headless) as ctx:
        page = await ctx.new_page()
        
        print("Navigating to example.com...")
        await page.goto("https://example.com", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        
        print("Injecting fake cursor overlay...")
        await ensure_cursor_overlay(page)
        
        # 1. Slide cursor in a triangle shape
        print("1. Gliding mouse smoothly in a triangle path...")
        points = [(400, 300), (800, 100), (600, 500)]
        for x, y in points:
            print(f"  Gliding smoothly to ({x}, {y})...")
            await smooth_move(page, x, y)
            await page.wait_for_timeout(500)
            
        # 2. Smooth click the 'More information...' link
        print("2. Locating 'More information...' link...")
        link = page.locator("a")
        
        print("  Gliding cursor and performing smooth click with pulse effect...")
        # This will calculate the link's center bounding box, glide the cursor, pulse, and click!
        await smooth_click(page, link)
        
        print("  ✓ Navigation triggered successfully!")
        await page.wait_for_timeout(3000)
        
        # 3. Slide cursor on the newly loaded page
        print("3. Gliding smoothly across the new page...")
        await smooth_move(page, 200, 150)
        await page.wait_for_timeout(1000)
        
    print("\n✓ Visual smooth mouse test completed successfully!")


if __name__ == "__main__":
    asyncio.run(run_visual_test())
