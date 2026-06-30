# Utility Modules Reference

All utilities are in `x_personas/utils/`.

---

## Browser (`browser.py`)

**`BrowserSession`** — Playwright browser lifecycle manager.

```python
class BrowserSession:
    def __init__(
        headless: bool = True,
        auth_state_path: str = "auth.json",
        executable_path: str | None = None,
        user_data_dir: str | None = None,
        user_agent: str | None = None,
        timezone_id: str | None = None,
        locale: str = "en-IN",
        geolocation: dict | None = None,
        viewport: dict | None = None,
    )
```

- Supports both persistent context (with `user_data_dir`) and ephemeral context (with auth state file)
- Default UA: Chrome 132 on Linux x86_64
- Ignores Playwright's default automation args for stealth
- Sets `--disable-blink-features=AutomationControlled` flag
- `locale` defaults to `"en-IN"`
- `viewport` defaults to 1280×900 (headless) or no_viewport (headed)
- `save_auth_state()` persists storage state to `auth_state_path`
- Can be used as async context manager: `async with BrowserSession(...) as ctx`

---

## Feed (`feed.py`)

**`_parse_article(article)`** — Core DOM parser for tweet articles.

Extracts: `status_id` (from `/status/<id>` URL), `author_name`, `handle`, `text`, `timestamp`, `is_retweet`, `is_reply`, `is_quote`, metrics (replies/retweets/likes/bookmarks/views), quoted post data, media URLs, avatar URL, verified status.

**`get_home_feed(context, scroll_count=3)`** — Full feed scraping (used for testing, not in graph).

**`navigate_home(page)`** — Navigate to `x.com/home` with 120s login wait fallback. If timeline doesn't load in 5s, prints a warning and polls for 120s (for manual login in headed mode). Saves auth state when login detected.

**`scroll_down(page, times=1)`** — Smooth scroll via `window.scrollBy({ top: window.innerHeight, behavior: 'smooth' })`.

**`detect_current_page(page)`** — URL-based page type detection: Home Feed, Tweet Detail, Login Screen, Notifications, Messages, Bookmarks, Search, Settings, Post Compose, Profile Page.

---

## Post (`post.py`)

High-level action functions used by `execute_actions.py`. All use `smooth_click` for human-like interaction.

**`open_post_tab(context, status_id)`** — Opens new tab to `https://x.com/i/status/{status_id}`.

**Page-level actions** (used in action tab — one tab already opened to the post):
- `like_on_page(page)` — Clicks like button, verifies by checking unlike button visibility
- `repost_on_page(page)` — Clicks retweet, then confirms via retweetConfirm selector
- `reply_on_page(page, text)` — Clicks reply, types character-by-character (0.01-0.035s delay), clicks post button
- `quote_on_page(page, text)` — Clicks retweet, selects "Quote" menu item, types, posts

**Context-level actions** (standalone, opens own tab):
- `post(context, text)` — Navigates to compose page, types, posts
- `like(context, status_id)` / `repost(context, status_id)` / `reply(context, status_id, text)` / `quote(context, status_id, text)`

**`_parse_article_metrics(article)`** — Parses metrics from aria-labels on action buttons.

---

## Mouse (`mouse.py`)

Human-like mouse movement simulation with visual cursor overlay.

**Features:**
- Cubic Bezier curves with randomized control points for natural arm-swing arcs
- Fitts's Law deceleration easing (slow start, fast middle, slow end)
- Target overshooting for distances > 180px (2-5% past target, correct back)
- Muscle micro-jitter (±0.8px per step)
- Human neuromuscular latency (7-15ms between steps)

**Functions:**
- `smooth_move(page, target_x, target_y)` — Glides cursor from current position to target
- `smooth_click(page, element_or_selector)` — Move to element center, hover delay (0.18-0.38s), click effect, click
- `smooth_hover(page, element_or_selector)` — Move to element and hover

**Visual overlay (headed mode):**
- Injects `<div id="fake-cursor">` with SVG cursor (Obsidian/Carbon-style dark body, white outline)
- `trigger_click_effect()` — Expands concentric touch-ripples (indigo + dark double rings) at click point
- SVG cursor scales down (0.82) on click for tactile feedback
- Disabled when `DISABLE_CURSOR` env var is set (headless or `--no-cursor`)

---

## Helpers (`_helpers.py`)

Shared low-level async utilities.

- **`safe_click(page, selector, ...)`** — Wait, scroll, smooth_click, with pre/post delays
- **`safe_fill(page, selector, text, ...)`** — Wait, clear, fill input
- **`safe_type(page, selector, text, ...)`** — Click content-editable and type character-by-character
- **`extract_text(element)`** — Trimmed inner_text or ""
- **`extract_text_from_page(page, selector)`** — Convenience wrapper
- **`scroll_page(page, distance=800, pause=1.5)`** — Scroll and wait
- **`parse_count(raw)`** — Parse "1.2K" → 1200, "3,456" → 3456, "2.5M" → 2500000
- **`extract_status_id(href)`** — Extract numeric ID from `/status/<id>`
- **`attach_media(page, file_paths)`** — Upload media to X compose via file input
- **`goto_and_wait(page, url, ...)`** — Navigate and wait for JS hydration
- **`wait_for_toast(page, ...)`** — Wait for X toast notification and return text

---

## Selectors (`selectors.py`)

Centralized DOM selectors — single source of truth for all CSS/`data-testid` selectors.

| Group | Selectors |
|---|---|
| Tweet/article | `TWEET_ARTICLE`, `TWEET_TEXT`, `TWEET_USER_NAME`, `TWEET_TIMESTAMP`, `TWEET_PERMALINK` |
| Action buttons | `REPLY_BUTTON`, `REPOST_BUTTON`, `UNREPOST_BUTTON`, `LIKE_BUTTON`, `UNLIKE_BUTTON`, `SHARE_BUTTON`, `BOOKMARK_BUTTON` |
| Repost menu | `REPOST_MENU_ITEM`, `QUOTE_MENU_ITEM` |
| Compose | `COMPOSE_TEXTBOX`, `COMPOSE_POST_BUTTON`, `COMPOSE_INLINE_POST_BUTTON`, `COMPOSE_FILE_INPUT`, `COMPOSE_MEDIA_BUTTON` |
| Reply dialog | `REPLY_DIALOG`, `REPLY_TEXTBOX`, `REPLY_POST_BUTTON` |
| Profile | `PROFILE_HEADER`, `PROFILE_BIO`, `PROFILE_LOCATION`, `PROFILE_URL`, `PROFILE_JOINED`, `PROFILE_VERIFIED`, `PROFILE_FOLLOWERS_LINK`, `PROFILE_FOLLOWING_LINK`, `PROFILE_EDIT_BUTTON` |
| Profile edit | `EDIT_NAME_INPUT`, `EDIT_BIO_TEXTAREA`, `EDIT_LOCATION_INPUT`, `EDIT_WEBSITE_INPUT`, `EDIT_SAVE_BUTTON` |
| Misc | `TOAST_NOTIFICATION`, `PRIMARY_COLUMN`, `BACK_BUTTON` |
| Conversation | `CONVERSATION_TWEET`, `SHOW_REPLIES_BUTTON` |

---

## Post Data (`post_data.py`)

**`get_post_data(context_or_page, feed_post_or_id, max_reply_scrolls=15)`** — Full post data with nested reply tree.

Navigates to status page, scrapes:
- Main post: text, timestamp, metrics (likes/reposts/quotes from stat bar), media URLs
- Replies: scrolls up to 15 times, collects reply articles, parses reply_id/author/text/timestamp/likes
- Builds nested reply tree via `_build_reply_tree()`: groups consecutive same-author replies into chains

---

## Standalone Action Files

Wrappers for individual actions with similar API:

- `like.py` — `like(context_or_page, status_id, handle=None)` → `ActionResult`
- `repost.py` — `repost(context_or_page, status_id, handle=None)` → `ActionResult`
- `reply.py` — `reply(context_or_page, status_id, text, handle=None, media_paths=None)` → `PostResponse`
- `quote.py` — `quote(context_or_page, status_id, text, handle=None, media_paths=None)` → `PostResponse`

All support both `Page` and `BrowserContext` as first argument. All navigate directly to the status URL, click the relevant button, type text, and verify the action.

---

## Profile (`profile.py`)

**`get_profile_stats(context_or_page, username)`** → `ProfileStats`

Scrapes `x.com/{username}` for: display name, bio, location, website, followers/following counts, posts count, verified status, join date.

**`update_persona_file_metadata(file_path, handle, display_name, bio, followers, following, verified)`**

Non-destructively updates the section 1 table in the persona markdown file with live scraped stats.

---

## Edit Profile (`edit_profile.py`)

**`edit_profile(context_or_page, name=None, bio=None, location=None, website=None)`** → `ActionResult`

Navigates to `x.com/settings/profile`, fills specified fields, clicks Save. Only modifies non-None fields.

---

## Exceptions (`exceptions.py`)

Custom exception hierarchy for X automation:

```
XPersonaError (base)
├── XAuthError              # Missing/expired session
├── XNavigationError        # Navigation failed / redirect
├── XElementNotFoundError   # DOM element not found
├── XActionError            # Action failed (partial success possible)
│   └── XMediaUploadError   # Media upload failure
└── XRateLimitError         # X rate limit hit
```
