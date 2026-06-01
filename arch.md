## System Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     PERSONA GENERATOR                       │
│                    src/generate_persona.py                  │
│                                                            │
│  Raw scraped posts/replies  ──►  LLM analyzes patterns ──►  │
│  from a real X account          (tone, topics, slang,       │
│  (e.g. purusha-persona.md)      reply style, stances)       │
│                                                             │
│  Output: persona-struct.md (filled 14-section template)     │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     AUTONOMOUS AGENT                          │
│                        src/agent/                            │
│                                                              │
│  ┌──────────────┐                                            │
│  │ load_persona  │  (no-op if already loaded)                │
│  └──────┬───────┘                                            │
│         ▼                                                     │
│  ┌──────────────┐    ┌──────────────┐                        │
│  │  scroll_feed  │───►│  llm_decide   │                      │
│  │  (1 viewport) │    │  (LLM sees    │                      │
│  └──────────────┘    │   persona +   │                       │
│         ▲            │   feed posts, │                       │
│         │            │   returns      │                      │
│         │            │   structured   │                      │
│         │            │   decisions)   │                      │
│         │            └───────┬───────┘                      │
│         │                    │                               │
│         │            ┌───────┴────────────────────────┐      │
│         │            │                                │      │
│         │      ┌─────▼─────┐                   ┌──────▼─────┐│
│         │      │  hydrate  │                   │  execute   ││
│         │      │  replies  │                   │  actions   ││
│         │      └─────┬─────┘                   │  (likes    ││
│         │            ▼                         │   only)    ││
│         │      ┌─────▼─────┐                   └──────┬─────┘│
│         │      │ generate  │                          │      │
│         │      │ content   │                          │      │
│         │      │ (LLM:     │                          │      │
│         │      │  reply/   │                          │      │
│         │      │  quote)   │                          │      │
│         │      └─────┬─────┘                          │      │
│         │            └──────────────┬─────────────────┘      │
│         │                           ▼                        │
│         │                    ┌───────────────┐               │
│         │                    │ execute_actions│  New tab per post,   │
│         │                    │ (Playwright)   │  batch all actions   │
│         │                    └───────┬───────┘               │
│         │                            ▼                       │
│         │                    ┌───────────────┐               │
│         │                    │ log_activity   │──► .md       │
│         │                    └───────┬───────┘               │
│         │                            ▼                       │
│         │                    ┌───────────────┐               │
│         │                    │ follow_decision│              │
│         │                    └───────┬───────┘               │
│         │                            ▼                       │
│         │                    ┌───────────────┐               │
│         └────────────────────│ state_cleansing│              │
│                              │ (clear cycle   │              │
│                              │  state, keep   │              │
│                              │  persona +     │              │
│                              │  seen IDs)     │              │
│                              └───────┬───────┘               │
│                                      ▼                       │
│                              ┌───────────────┐               │
│                              │  scroll_page   │               │
│                              │  (5-15s delay  │               │
│                              │   + smooth     │               │
│                              │   scroll)      │               │
│                              └───────┬───────┘               │
│                                      │                       │
│                                      └── END (per cycle)     │
└──────────────────────────────────────────────────────────────┘
                           │
            Runner handles breaks externally:
            scroll_count >= scroll_limit (default 2500) → 10–30 min sleep
                                                       → re-navigate x.com/home
                                                       → reset scroll_count
                                                       → reload engaged_ids from log
                                                       (each cycle scrolls 3x, so ~833 cycles)
```

## Per-cycle flow (one graph.ainvoke call)

1. `load_persona` — parse persona (no-op if already loaded)
2. `scroll_feed` — parse currently visible posts, filter seen/engaged, and log page transitions
3. `llm_decide` — **LLM** sees full persona profile + visible feed posts, returns structured decisions via `EngagementDecisions` Pydantic model (action_type as list of like/reply/quote, score, reason). IGNORE posts are omitted entirely.
4. `hydrate_replies` — if reply/quote actions exist, Playwright navigates to status page in new tab to fetch thread ancestor/peer context and check for duplicate replies.
5. `generate_content` — if reply/quote actions exist, dedicated LLM call per action with writing samples and hydrated thread context to generate text, enforcing persona constraints (vocabulary, casing, emoji rules).
6. `execute_actions` — executes pending likes, reposts, replies, and quotes (opening exactly one tab per post). Supports an interactive approval mode (`--ask`) displaying author, actions, and scores for operator consent (`Y`/`n`/`s`).
7. `log_activity` — append to `<persona>-activity-log.md`
8. `follow_decision` — evaluate follow candidates
9. `state_cleansing` — clear cycle state (keep persona + seen IDs)
10. `scroll_page` — wait 5-15s, **3 smooth scrolls** (1s gap), increment scroll_count → end cycle

## Scroll happens after decisions, not before

Each LangGraph cycle first **parses** whatever is currently visible in the viewport.
After all decisions are made and actions executed (or skipped), a dedicated
`scroll_page` node waits 5-15s (human reading time) and smooth-scrolls by one viewport
height. This ensures the next cycle sees fresh content.

Previously seen posts are tracked via `seen_post_ids` and filtered out on re-parse.

## LLM-driven decisions (no keyword matching)

The old heuristic scoring engine (topic × 0.4 + account × 0.3 + format × 0.2 + recency × 0.1) has been removed. The LLM now makes all engagement decisions:

1. **System prompt**: compiled from persona sections (identity, vocabulary, topics, account relationships, format preferences, engagement thresholds, matrix, reply guidelines)
2. **User prompt**: rendered feed posts with text, handle, metrics, flags
3. **LLM returns structured output**: `EngagementDecisions` with `PostDecision[]` — each has `action_type: list[str]` (e.g. `["like", "reply"]`), `target_status_id`, `target_handle`, `score`, `reason`
4. **No content** is generated in this call — only decisions

Content for replies and quotes is generated in a **separate** `generate_content` call with writing samples from source data, giving higher quality text.

## Tab-per-interaction

Instead of clicking buttons on the home page feed, each engagement
opens a dedicated Playwright tab:

```
for each pending action batch (grouped by post ID):
    page = await context.new_page()
    await page.goto(f"https://x.com/i/status/{status_id}")
    // perform all actions for this post (like, reply, etc.)
    await page.close()
    sleep random(3, 8) seconds
```

This avoids navigation on the home tab, feels less bot-like, and
works reliably even if the interaction fails.

## Dedup

| Source | What it tracks | Used by |
|---|---|---|
| `seen_post_ids` (in-memory) | All posts parsed this session | `scroll_feed` — skip re-processing |
| `engaged_ids` (activity log) | All posts ever engaged | `scroll_feed` — skip previously engaged; `llm_decide` — filter input |
| `history.load_engaged_status_ids()` | Reads `<persona>-activity-log.md` | Runner reloads after breaks |
| handle dedup | One author per cycle | `_decisions_to_pending` — first decision per handle wins |

## Two-phase workflow

### Phase 1: Generate Persona (one-time per account)

Scraped posts and replies from a real X account → LLM analyzes linguistic
patterns, topics, reply behavior, stances → outputs a filled
`persona-struct.md` file.

### Phase 2: Run Agent (perpetual)

Persona file → agent logs into X, scrolls feed one viewport per cycle,
sends visible posts + persona to the LLM for engagement decisions,
generates reply/quote text separately with writing samples, opens a new
tab per interaction, executes via Playwright, logs everything, cleanses
cycle state, and loops back.

## Human-like pacing

| Phase | Delay | Implementation |
|---|---|---|
| Between actions (on same tab) | 3–8s | `rate_limiter.action_delay()` |
| Between scrolls (end of cycle) | 5–15s | `rate_limiter.scroll_delay()` |
| Between scroll-limit batches | 10–30 min | `runner.py` `asyncio.sleep()` |
| Re-navigation after break | N/A | `feed.navigate_home(page)` |

## Built-in safeguards

| Limit | Per cycle | Per hour | Per day |
|---|---|---|---|
| Likes | 5 | 20 | 80 |
| Replies | 2 | 8 | 30 |
| Reposts | 2 | 8 | 30 |
| Quotes | 1 | 4 | 15 |
| Follows | — | 3 | 15 |

- 1 action per unique handle per cycle (no spamming the same person)
- Limits persist across restarts via `.rate-limits-<persona>.json`

## Directory layout

```
src/
├── prompts/                       # LLM prompt templates
│   ├── llm_decide_system.md       # System prompt for engagement decisions
│   └── llm_decide_user.md         # User prompt template with feed posts
├── generate_persona.py            # Phase 1: source data → persona-struct.md
├── agent/
│   ├── runner.py                  # CLI entry point, perpetual loop, break logic, live sync
│   ├── graph.py                   # LangGraph StateGraph (one cycle per ainvoke)
│   ├── state.py                   # PersonaState TypedDict
│   ├── config.py                  # LLM provider factory (OpenAI/Anthropic/DashScope)
│   ├── rate_limiter.py            # Persistent per-cycle/hourly/daily caps + delay fns
│   ├── history.py                 # Load engaged status_ids from activity-log.md
│   ├── nodes/
│   │   ├── load_persona.py        # Parse persona-struct.md (no-op on re-entry)
│   │   ├── fetch_feed.py          # → scroll_feed (parse viewport, dedup)
│   │   ├── llm_decide.py          # → LLM: decide which posts to engage with
│   │   ├── hydrate_replies.py     # → Playwright: scrape thread ancestor context
│   │   ├── generate_content.py    # → LLM: write reply/quote text with samples
│   │   ├── scroll_page.py         # → scroll_page (5-15s delay, smooth scroll)
│   │   ├── execute_actions.py     # Playwright: new tab per post, batch all actions, approvals
│   │   ├── log_activity.py        # Append to activity-log.md
│   │   ├── follow_decision.py     # Score accounts, decide to follow
│   │   └── state_cleansing.py     # Clear cycle state, preserve persona + seen IDs
│   ├── log.py                     # Timestamped debug logging
├── models/
│   ├── feed.py                    # FeedPost, FeedResponse, PostMetrics, QuotedPost
│   ├── post.py                    # ActionResult, PostData, PostResponse, Reply
│   ├── engagement.py              # ActionType(Enum), PendingAction, ExecutedAction,
│   │                              # PostDecision, EngagementDecisions (Pydantic)
│   └── log.py                     # ActivityLogEntry, ActivityLog
└── utils/
    ├── browser.py                 # BrowserSession (Playwright lifecycle, 100% desktop scale)
    ├── feed.py                    # navigate_home, scroll_down (smooth), _parse_article, page state
    ├── mouse.py                   # cubic Bézier mouse easing pointer and press ripples
    └── post.py                    # get_post_data, open_post_tab, like/repost/reply/quote_on_page
```

## Agent graph nodes

| Node | Type | Purpose |
|---|---|---|
| `load_persona` | sync | Parse persona-struct.md → sections dict (no-op if already loaded) |
| `scroll_feed` | async | Parse visible posts, filter dedup (no scroll), logs active page states |
| `llm_decide` | async | LLM sees persona + feed posts → structured `EngagementDecisions` via `.with_structured_output()` |
| `hydrate_replies` | async | Scrapes parent / peer replies in thread for context-aware chaining |
| `generate_content` | async | LLM generates reply/quote text utilizing thread context and writing samples |
| `execute_actions` | async | New tab per post (batch actions by post ID), 3–8s delay (supports terminal approvals) |
| `log_activity` | sync | Append to `<persona>-activity-log.md`, persist rate limits |
| `follow_decision` | sync | Evaluate follow candidates against criteria + session limits |
| `state_cleansing` | sync | Clear cycle state (keep persona + seen IDs) |
| `scroll_page` | async | Wait 5–15s, smooth scroll one viewport, increment scroll_count |

## Custom Interaction Utilities

### 1. Bézier Cursor Interaction
To support mouse-based interaction simulation:
* **Easing:** Moves the cursor along cubic Bézier curves.
* **Cursor Overlay:** In headed runs (`--visible`), renders a mouse pointer overlay in the DOM. Clicking triggers a scale animation and indicator waves.
* **Stealth Bypass:** Mouse DOM injections are bypassed during headless runs. The operator can deactivate overlays in headed sessions via the `--no-cursor` switch.

### 2. Startup Account Auto-Sync Scraper
When starting a session:
1. The orchestrator queries the left-hand navigation sidebar for the profile button, immediately resolving the active logged-in handle.
2. Navigates automatically to the user's profile and scrapes actual real-time statistics (followers, following, display name, bio, and verified status) using dual-selector compatible queries.
3. Rewrites the `identity & metadata` table in `<persona>-struct.md` on disk safely (preserving all custom metadata).
4. Re-loads the parsed metadata into memory so that the agent's LLM cycles act on perfectly accurate stats.

### 3. Interactive Approval Gateway (`--ask`)
Bypasses the automated execution sequence. It summarizes pending interaction groups (author, target status, proposed text, and LLM logical reasoning score) and prompts the operator to approve (`Y`/`y`), reject (`N`/`n`), or skip (`S`/`s`) before executing actions on the page.

### 4. Dynamic Page-State Recognition Engine
Every navigation and new tab load calls `detect_current_page(page: Page) -> str` to identify and print context-specific logs identifying if we are on the Home Feed, Login Screen, Profile Page, Notifications panel, Settings, or Tweet detail tabs.

## Prompt templates

All prompt templates are in `src/prompts/`:

- **`llm_decide_system.md`**: Dynamic prompt filled with `{persona_sections}` capturing stances, rules, thresholds, and profiles.
- **`llm_decide_user.md`**: Filled dynamically with `{feed_posts}`.

The `generate_content` node compiles prompts dynamically combining `{persona_sections}`, hydrated thread context, and selected writing samples.
