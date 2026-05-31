#!/usr/bin/env python3
"""Quick test for Playwright with real Chromium profile.

Steps:
  1. Close ALL Chromium instances first (profile must not be in use)
  2. Run this — launches Chromium via Playwright with your real profile
  3. If auth.json exists from a previous run, it skips x.com entirely
"""

import asyncio
import os
import sys
from pathlib import Path

from src.utils.browser import BrowserSession


def _find_chromium_profile() -> str | None:
    candidates = [
        os.path.expanduser("~/.config/chromium"),
        os.path.expanduser("~/.var/app/org.chromium.Chromium/config/chromium"),
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


async def main():
    chromium_path = "/usr/bin/chromium"
    if not Path(chromium_path).exists():
        print(f"FAIL: chromium not found at {chromium_path}")
        sys.exit(1)
    print(f"[1/4] chromium found at {chromium_path}")

    profile = _find_chromium_profile()
    if not profile:
        print("FAIL: no chromium profile found")
        sys.exit(1)
    print(f"      profile: {profile}")

    auth_file = Path("auth.json")
    if auth_file.exists():
        print(f"      auth.json found (will load as fallback)")

    session = BrowserSession(
        headless=False,
        executable_path=chromium_path,
        user_data_dir=profile,
    )

    try:
        print("[2/4] launching browser with your real profile ...")
        ctx = await session.start()

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        print("[3/4] checking x.com ...")
        await page.goto("https://x.com/home", wait_until="domcontentloaded")
        await asyncio.sleep(3)

        logged_in = await page.query_selector('[data-testid="SideNav_AccountSwitcher"]')
        if logged_in:
            print("      ✓ logged in (profile has your session)")
        else:
            print("      ⚠ not logged in — log in manually, then press Enter")
            await _await_enter()

        await page.goto("https://x.com/home", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        logged_in = await page.query_selector('[data-testid="SideNav_AccountSwitcher"]')
        if not logged_in:
            print("FAIL: not logged in")
            sys.exit(1)

        print("      ✓ home feed loaded")

        print("[4/4] saving auth state for future runs ...")
        await session.save_auth_state()
        print(f"      saved to {Path('auth.json').resolve()}")

        title = await page.title()
        print(f"\nPlaywright + real Chromium profile: OK ('{title}')")
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    finally:
        await session.stop()


def _await_enter():
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    asyncio.run(main())
