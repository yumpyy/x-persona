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
│         │            ┌───────┴───────┐                       │
│         │            │               │                       │
│         │       ┌────┴────┐   ┌──────┴─────┐                │
│         │       │ generate │   │  execute   │                │
│         │       │ content  │   │  actions   │                │
│         │       │ (LLM:    │   │  (likes    │                │
│         │       │  reply/  │   │   only)    │                │
│         │       │  quote)  │   └─────┬──────┘                │
│         │       └────┬─────┘        │                        │
│         │            └──────┬───────┘                        │
│         │                   ▼                                 │
│         │            ┌───────────────┐                       │
│         │            │ execute_actions│  New tab per action  │
│         │            │ (Playwright)   │  batch by post ID   │
│         │            └───────┬───────┘                       │
│         │                    ▼                                │
│         │            ┌───────────────┐                       │
│         │            │ log_activity   │──► .md               │
│         │            └───────┬───────┘                       │
│         │                    ▼                                │
│         │            ┌───────────────┐                       │
│         │            │ follow_decision│                      │
│         │            └───────┬───────┘                       │
│         │                    ▼                                │
│         │            ┌───────────────┐                       │
│         └────────────│ state_cleansing│                      │
│                      │ (clear cycle   │                      │
│                      │  state, keep   │                      │
│                      │  persona +     │                      │
│                      │  seen IDs)     │                      │
│                      └───────┬───────┘                       │
│                              ▼                                │
│                      ┌───────────────┐                       │
│                      │  scroll_page   │                       │
│                      │  (5-15s delay  │                       │
│                      │   + smooth     │                       │
│                      │   scroll)      │                       │
│                      └───────┬───────┘                       │
│                              │                                │
│                              └── END (per cycle)              │
└──────────────────────────────────────────────────────────────┘
                           │
            Runner handles breaks externally:
            scroll_count >= scroll_limit (default 2500) → 10–30 min sleep
                                                       → re-navigate x.com/home
                                                       → reset scroll_count
                                                       → reload engaged_ids from log
```

## Per-cycle flow (one graph.ainvoke call)

1. `load_persona` — parse persona (no-op if already loaded)
2. `scroll_feed` — parse currently visible posts, filter seen/engaged
3. `llm_decide` — **LLM** sees full persona profile + visible feed posts, returns structured decisions via `EngagementDecisions` Pydantic model (action_type as list, score, reason)
4. `generate_content` — if reply/quote actions exist, dedicated LLM call per action with writing samples to generate text
5. `execute_actions` — new tab per post, all actions on one tab
6. `log_activity` — append to `<persona>-activity-log.md`
7. `follow_decision` — evaluate follow candidates
8. `state_cleansing` — clear cycle state (keep persona + seen IDs)
9. `scroll_page` — wait 5-15s, smooth scroll one viewport → end cycle

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
│   ├── runner.py                  # CLI entry point, perpetual loop, break logic
│   ├── graph.py                   # LangGraph StateGraph (one cycle per ainvoke)
│   ├── state.py                   # PersonaState TypedDict
│   ├── config.py                  # LLM provider factory (OpenAI/Anthropic/DashScope)
│   ├── rate_limiter.py            # Persistent per-cycle/hourly/daily caps + delay fns
│   ├── history.py                 # Load engaged status_ids from activity-log.md
│   ├── nodes/
│   │   ├── load_persona.py        # Parse persona-struct.md (no-op on re-entry)
│   │   ├── fetch_feed.py          # → scroll_feed (parse viewport, dedup)
│   │   ├── llm_decide.py          # → LLM: decide which posts to engage with
│   │   ├── generate_content.py    # → LLM: write reply/quote text with samples
│   │   ├── scroll_page.py         # → scroll_page (5-15s delay, smooth scroll)
│   │   ├── execute_actions.py     # Playwright: new tab per post, batch all actions
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
    ├── browser.py                 # BrowserSession (Playwright lifecycle)
    ├── feed.py                    # navigate_home, scroll_down (smooth), _parse_article
    └── post.py                    # get_post_data, open_post_tab, like/repost/reply/quote_on_page
```

## Agent graph nodes

| Node | Type | Purpose |
|---|---|---|
| `load_persona` | sync | Parse persona-struct.md → sections dict (no-op if already loaded) |
| `scroll_feed` | async | Parse visible posts, filter dedup (no scroll) |
| `llm_decide` | async | LLM sees persona + feed posts → structured `EngagementDecisions` via `.with_structured_output()` |
| `generate_content` | async | LLM generates reply/quote text for pending actions (with writing samples) |
| `execute_actions` | async | New tab per post (batch actions by post ID), 3–8s delay |
| `log_activity` | sync | Append to `<persona>-activity-log.md`, persist rate limits |
| `follow_decision` | sync | Evaluate follow candidates against criteria + session limits |
| `state_cleansing` | sync | Clear feed_posts, scored_posts, actions; keep persona + seen IDs |
| `scroll_page` | async | Wait 5–15s, smooth scroll one viewport, increment scroll_count |

## Prompt templates

All prompt templates are in `src/prompts/`:

- **`llm_decide_system.md`**: Persona identity, linguistic style, topics, accounts, format preferences, engagement thresholds/matrix, reply guidelines → filled dynamically from persona sections with `{persona_sections}` placeholder
- **`llm_decide_user.md`**: Rendered feed posts → filled with `{feed_posts}`

The `generate_content` node builds its prompt dynamically (no template file needed since writing samples vary per action).
