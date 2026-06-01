from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
from src.agent.config import get_llm_config
from src.agent.graph import create_graph
from src.agent.history import load_engaged_status_ids
from src.agent.log import log, set_quiet
from src.agent.nodes.load_persona import load_persona
from src.agent.rate_limiter import cycle_caps
from src.models.feed import FeedPost
from src.utils.browser import BrowserSession
from src.utils.feed import navigate_home

load_dotenv()


async def dry_run(persona_file: str, llm_config: dict | None = None) -> None:
    persona_path = Path(persona_file)
    if not persona_path.exists():
        print(f"Persona file not found: {persona_file}", file=sys.stderr)
        sys.exit(1)

    if persona_path.stat().st_size == 0:
        print(f"Persona file '{persona_file}' is completely empty. Please copy the 14-section template from 'persona-struct.md' before running.", file=sys.stderr)
        sys.exit(1)

    print(f"\u2550\u2550\u2550 DRY RUN: {persona_path.stem} \u2550\u2550\u2550\n")

    from src.agent.nodes.llm_decide import llm_decide, _build_feed_text, _build_persona_text

    if llm_config is None:
        llm_config = get_llm_config()
    state = load_persona({
        "persona_file": str(persona_path),
        "activity_log_file": "",
        "llm_config": llm_config,
        "persona_sections": {},
        "source_data_files": [],
        "feed_posts": [],
        "feed_scroll_position": None,
        "scored_posts": [],
        "pending_actions": [],
        "executed_actions": [],
        "thread_contexts": {},
        "follow_candidates": [],
        "follows_this_session": 0,
        "rate_limit_file": "",
        "cycle_action_counts": {},
        "seen_post_ids": [],
        "engaged_ids": [],
        "scroll_count": 0,
        "error": None,
    })
    s = state["persona_sections"]

    print(f"  Sections parsed: {len(s)}")
    print(f"  Topic weights (9a): {len(s.get('9a', {}))} categories")
    for k, v in s.get("9a", {}).items():
        print(f"    {k}: {v}")
    print(f"  Decision thresholds (9f): {len(s.get('9f', {}))} ranges")
    for k, v in s.get("9f", {}).items():
        print(f"    score {k} \u2192 {v}")
    print(f"  Engagement matrix (9g): {len(s.get('9g', []))} rules")
    print(f"  Per-cycle caps: {cycle_caps()}")
    print()

    sample_posts = [
        ("tech_drama", "cursor is just a fork of vscode, they should credit the original authors", "stranger", 0),
        ("ai_tool", "whisper + ffmpeg auto captioning in one line", "devfriend", 0),
        ("tractor", "check out my new eicher tractor", "farmer_friend", 0),
        ("shitpost", "the power of nothing \u2014 filling empty space with everything", "meme_account", 0),
        ("random", "just ate lunch", "random_user", 48),
        ("mutual_news", "got an internship at Google!", "close_friend", 1),
        ("politics", "new policy changes are concerning", "political_account", 3),
    ]

    from datetime import datetime, timedelta, timezone
    sample_feed = []
    for label, text, handle, hours_ago in sample_posts:
        ts = datetime.now(timezone.utc).isoformat()
        if hours_ago > 0:
            ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()
        sample_feed.append(FeedPost(
            status_id=f"dry_{label}",
            author_name=handle,
            handle=handle,
            text=text,
            timestamp=ts,
        ))

    # Show the compiled prompts
    print(f"\u2550\u2550\u2550 COMPILED PERSONA (\u2192 LLM system prompt) \u2550\u2550\u2550\n")
    persona_text = _build_persona_text(s)
    for line in persona_text.split("\n"):
        print(f"  {line}")
    print()

    feed_text = _build_feed_text(sample_feed)
    print(f"  Feed: {len(sample_feed)} posts ({len(feed_text)} chars)\n")

    # Call LLM for decisions
    print(f"\u2550\u2550\u2550 LLM DECISIONS \u2550\u2550\u2550\n")
    print(f"  Calling LLM ({llm_config.get('model', 'default')})...\n")

    decision_state = {
        **state,
        "feed_posts": sample_feed,
        "persona_sections": s,
        "llm_config": llm_config,
    }
    result = await llm_decide(decision_state)
    pending = result.get("pending_actions", [])

    if not pending:
        print("  No posts triggered engagement.\n")
        print("  (LLM decided none of the sample posts were worth engaging with)")
    else:
        print(f"  Total pending: {len(pending)}\n")
        for a in pending:
            txt = f" \u2192 \"{a.content[:60]}...\"" if a.content else ""
            print(f"  [{a.action_type.value:>6}] @{a.target_handle:<20} score={a.score:.1f}{txt}")
            print(f"       {a.reason}")

    print(f"\n\u2550\u2550\u2550 RATE LIMITS \u2550\u2550\u2550")
    counts = result.get("cycle_action_counts", {})
    caps = cycle_caps()
    for action in sorted(caps):
        used = counts.get(action, 0)
        cap = caps[action]
        bar = "\u2588" * used + "\u2591" * (cap - used)
        print(f"  {action:>6}: {bar} {used}/{cap}")

    print(f"\n\u2550\u2550\u2550 DRY RUN COMPLETE \u2550\u2550\u2550")
    print(f"  Browser: NOT launched")
    print(f"  LLM: called once with {len(sample_feed)} sample posts")
    print(f"  No actions were executed.")


async def run_perpetual(
    persona_file: str,
    headless: bool = True,
    scroll_limit: int = 2500,
    llm_config: dict | None = None,
    browser_path: str | None = None,
    ask: bool = False,
    no_cursor: bool = False,
    auth_file: str | None = None,
    once: bool = False,
) -> None:
    if headless or no_cursor:
        os.environ["DISABLE_CURSOR"] = "true"

    persona_path = Path(persona_file)
    if not persona_path.exists():
        print(f"Persona file not found: {persona_file}", file=sys.stderr)
        sys.exit(1)

    if persona_path.stat().st_size == 0:
        print(f"Persona file '{persona_file}' is completely empty. Please copy the 14-section template from 'persona-struct.md' before running.", file=sys.stderr)
        sys.exit(1)

    persona_name = persona_path.stem
    activity_log = f"{persona_name}-activity-log.md"
    rate_limit_file = f".rate-limits-{persona_name}.json"
    llm_config = llm_config or get_llm_config()

    # Determine isolated auth state path
    if not auth_file:
        persona_auth = f"auth-{persona_name}.json"
        if Path(persona_auth).exists():
            auth_file = persona_auth
        elif Path("auth.json").exists():
            auth_file = "auth.json"
        else:
            auth_file = persona_auth
    
    print(f"🔒 Using browser session state file: {auth_file}")

    engaged_ids = list(load_engaged_status_ids(activity_log))
    if engaged_ids:
        print(f"  Found {len(engaged_ids)} previously engaged posts in activity log")

    async with BrowserSession(
        headless=headless,
        executable_path=browser_path,
        auth_state_path=auth_file,
    ) as ctx:
        home_page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await navigate_home(home_page)
        print(f"  Navigated to x.com/home (scroll_limit={scroll_limit}, headless={headless})")

        # --- Dynamic Logged-in Username & Live Stats Sync ---
        logged_in_handle = None
        try:
            profile_link = home_page.locator('a[data-testid="AppTabBar_Profile_Link"]').first
            if await profile_link.is_visible(timeout=3000):
                href = await profile_link.get_attribute("href")
                if href:
                    logged_in_handle = href.lstrip("/").strip()
        except Exception:
            pass

        if not logged_in_handle:
            try:
                switcher = home_page.locator('[data-testid="SideNav_AccountSwitcher_Button"]').first
                if await switcher.is_visible(timeout=2000):
                    text = await switcher.inner_text()
                    import re
                    matches = re.findall(r"@(\w+)", text)
                    if matches:
                        logged_in_handle = matches[0].strip()
            except Exception:
                pass

        if logged_in_handle:
            print(f"\n👤 [Startup] Logged-in user detected: @{logged_in_handle}")
            print(f"  Scraping latest profile statistics for @{logged_in_handle}...")
            try:
                from src.utils.profile import get_profile_stats, update_persona_file_metadata
                stats = await get_profile_stats(home_page, logged_in_handle)
                print(f"  Successfully scraped profile: {stats.display_name} (@{stats.handle})")
                print(f"  Followers: {stats.followers} | Following: {stats.following} | Posts: {stats.posts_count} | Verified: {stats.verified}")
                
                # Safely update the persona file on disk
                persona_path = Path(persona_file)
                update_persona_file_metadata(
                    persona_path,
                    handle=stats.handle,
                    display_name=stats.display_name,
                    bio=stats.bio,
                    followers=stats.followers,
                    following=stats.following,
                    verified=stats.verified
                )
                print(f"💾 Synchronized live profile statistics into {persona_path.name}")
                
                # Re-navigate home to return to feed
                await navigate_home(home_page)
            except Exception as err:
                print(f"⚠️  Could not sync profile stats for @{logged_in_handle}: {err}")
        else:
            print("⚠️  Could not detect logged-in username from the current session.")

        graph = create_graph()
        config = {
            "configurable": {
                "thread_id": persona_name,
                "browser_context": ctx,
                "home_page": home_page,
                "llm_config": llm_config,
                "ask": ask,
            }
        }

        state: dict = {
            "persona_file": str(persona_path),
            "activity_log_file": activity_log,
            "rate_limit_file": rate_limit_file,
            "llm_config": llm_config,
            "thread_contexts": {},
            "seen_post_ids": [],
            "engaged_ids": engaged_ids,
            "scroll_count": 0,
        }

        session_engagements = 0
        target_original_post_count = random.randint(10, 20)
        print(f"🎲 [Original Post Scheduler] Target engagements for next original tweet: {target_original_post_count}")

        cycle = 0
        while True:
            cycle += 1
            log(f"\u2550\u2550\u2550 cycle {cycle} \u2550\u2550\u2550")
            result = await graph.ainvoke(state, config)
            state.update(result)

            sc = state.get("scroll_count", 0)
            new_posts = result.get("feed_posts", [])
            pending = result.get("pending_actions", [])
            executed = result.get("executed_actions", [])
            log(f"cycle {cycle}: scrolls={sc} new_posts={len(new_posts)} pending={len(pending)} executed={len(executed)}")

            successful_engagements = [a for a in executed if a.success]
            if successful_engagements:
                session_engagements += len(successful_engagements)
                print(f"📈 [Original Post Scheduler] Session engagements: {session_engagements}/{target_original_post_count}")

            if session_engagements >= target_original_post_count:
                print("\n📝 [Original Post Scheduler] Triggered! Composing a brand new original post...")
                try:
                    from src.agent.nodes.generate_content import generate_original_post
                    from src.utils.post import post
                    from src.agent.history import load_recent_original_posts
                    from datetime import datetime, timezone

                    # Resolve time of day
                    hour = datetime.now().hour
                    if 5 <= hour < 12:
                        time_of_day = "Morning"
                    elif 12 <= hour < 20:
                        time_of_day = "Afternoon/Evening"
                    else:
                        time_of_day = "Late Night"

                    # Load recent original posts
                    recent_posts = load_recent_original_posts(activity_log, limit=5)
                    print(f"📖 Loaded {len(recent_posts)} recent original posts from memory")

                    tweet_text = await generate_original_post(
                        state["persona_sections"],
                        llm_config,
                        time_of_day,
                        recent_posts
                    )
                    print(f"✨ [Original Post Scheduler] Generated text ({time_of_day}): \"{tweet_text}\"")

                    if ask:
                        ans = input("Confirm publishing original post? [Y/n]: ").strip().lower()
                        if ans and ans != "y":
                            print("❌ Skipped original post publication.")
                            tweet_text = ""

                    if tweet_text:
                        print("🚀 Publishing original post key-by-key...")
                        resp = await post(ctx, tweet_text)
                        if resp.success:
                            print("✅ Original post successfully published!")
                            # Manually append to the activity log table so we have memory of it!
                            ts_str = datetime.now(timezone.utc).isoformat()
                            entry = f"| {ts_str} | original_post | self | {tweet_text} | 10.0 | Standalone original tweet published [{time_of_day}]. |"
                            with open(activity_log, "a", encoding="utf-8") as f:
                                f.write(entry + "\n")
                        else:
                            print(f"❌ Failed to publish original post: {resp.error}")
                except Exception as ex:
                    print(f"⚠️ Error in original post scheduler: {ex}")

                session_engagements = 0
                target_original_post_count = random.randint(10, 20)
                print(f"🎲 Next original post target set to: {target_original_post_count} engagements\n")

            if once:
                print("\n  [Once] Cycle completed. Exiting as requested by --once.")
                break

            if scroll_limit > 0 and sc >= scroll_limit:
                break_duration = random.randint(600, 1800)
                print(f"\n  Scroll limit ({scroll_limit}) reached. Taking {break_duration}s break...")
                await asyncio.sleep(break_duration)

                await navigate_home(home_page)
                print("  Re-navigated to x.com/home")

                state["scroll_count"] = 0
                engaged_ids = list(load_engaged_status_ids(activity_log))
                state["engaged_ids"] = engaged_ids
                state["seen_post_ids"] = []
                print(f"  Engaged posts on record: {len(engaged_ids)}")


async def run_once(
    persona_file: str,
    headless: bool = True,
    scroll_limit: int = 2500,
    llm_config: dict | None = None,
    browser_path: str | None = None,
) -> None:
    await run_perpetual(
        persona_file=persona_file,
        headless=headless,
        scroll_limit=scroll_limit,
        llm_config=llm_config,
        browser_path=browser_path,
        once=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="X Personas LangGraph Agent")
    parser.add_argument(
        "--persona",
        required=True,
        help="Path to persona-struct.md file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse persona and show LLM decisions without launching browser (calls LLM once)",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        default=False,
        help="Show browser window (default: headless)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress debug logs",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single cycle (default: perpetual loop)",
    )
    parser.add_argument(
        "--scroll-limit",
        type=int,
        default=2500,
        help="Scrolls before break (default: 2500, -1 for infinite)",
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "dashscope"],
        default=None,
        help="LLM provider",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="LLM model name (defaults to env var or provider default)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key (defaults to <PROVIDER>_API_KEY env var)",
    )
    parser.add_argument(
        "--base-url",
        default=None,
        help="Base URL for API (defaults to <PROVIDER>_BASE_URL env var)",
    )
    parser.add_argument(
        "--browser",
        default=None,
        help="Path to Chromium binary (default: Playwright-managed browser)",
    )
    parser.add_argument(
        "--ask",
        action="store_true",
        default=False,
        help="Ask for confirmation before executing any action (approval mode)",
    )
    parser.add_argument(
        "--no-cursor",
        action="store_true",
        default=False,
        help="Completely disable visual cursor and click ripple overlays in headed mode",
    )
    parser.add_argument(
        "--auth",
        default=None,
        help="Path to save/load browser auth state (default: auth-<persona>.json)",
    )

    args = parser.parse_args()

    set_quiet(args.quiet)

    llm_config = get_llm_config(
        provider=args.provider,
        model=args.model or os.getenv(
            {
                "openai": "OPENAI_MODEL",
                "anthropic": "ANTHROPIC_MODEL",
                "dashscope": "DASHSCOPE_MODEL",
            }.get(args.provider, ""),
            "",
        ) or None,
        api_key=args.api_key,
        base_url=args.base_url or os.getenv(
            {
                "dashscope": "DASHSCOPE_BASE_URL",
            }.get(args.provider, ""),
            "",
        ) or None,
    )

    if args.dry_run:
        asyncio.run(dry_run(args.persona, llm_config=llm_config))
        return

    asyncio.run(run_perpetual(
        persona_file=args.persona,
        headless=not args.visible,
        scroll_limit=args.scroll_limit,
        llm_config=llm_config,
        browser_path=args.browser,
        ask=args.ask,
        no_cursor=args.no_cursor,
        auth_file=args.auth,
        once=args.once,
    ))


if __name__ == "__main__":
    main()
