# X Personas — Overview

Autonomous X/Twitter persona agent built with LangGraph. Mimics human scrolling behavior, uses an LLM to decide engagement (likes, replies, reposts, quotes), and generates in-character content from writing samples. One LangGraph cycle per `ainvoke()`, runner loops perpetually.

---

## Directory Layout

```
x-personas/
├── personas/
│   ├── _template/
│   │   └── persona.md                # Blank 14-section template (reference)
│   └── <name>/                       # Per-persona directory (e.g. purusa0x6c)
│       ├── persona.md                # Structured persona definition
│       ├── activity-log.md           # Markdown table of all engagements (dedup source)
│       ├── auth.json                 # Browser auth session state (gitignored)
│       ├── rate-limits.json          # Persisted rate limit counters (gitignored)
│       ├── stats-cache.json          # Cached stats for fast startup (gitignored)
│       └── source/                   # Writing samples and custom files
│
├── pyproject.toml                    # Dependencies (playwright, langgraph, pydantic, etc.)
├── .env / .env.example               # API keys (OPENAI_API_KEY, VLM_MODEL, etc.)
├── persona-struct.md                 # Legacy blank template (symlink to _template/)
│
├── docs/                             # This directory
│
├── x_personas/
│   ├── generate_persona.py           # CLI to generate persona.md from raw source data
│   │
│   ├── agent/
│   │   ├── runner.py                 # CLI entry point (headless + tui subcommand), perpetual loop
│   │   ├── graph.py                  # LangGraph StateGraph with 10 nodes
│   │   ├── state.py                  # PersonaState TypedDict (19 fields incl. vlm_config)
│   │   ├── config.py                 # LLM factory (ChatOpenAI) + VLM config
│   │   ├── rate_limiter.py           # Per-cycle + hourly/daily caps, persisted
│   │   ├── history.py                # Load engaged status IDs, recent engagements, original posts
│   │   ├── log.py                    # log() with [HH:MM:SS] timestamps, pluggable sinks, set_quiet()
│   │   │
│   │   └── nodes/
│   │       ├── load_persona.py       # Parse personas/<name>/persona.md → structured dict
│   │       ├── fetch_feed.py         # Parse visible articles, filter seen+engaged
│   │       ├── llm_decide.py         # LLM decides which posts to engage (structured output)
│   │       ├── hydrate_replies.py    # Open tab, scrape thread context for reply targets
│   │       ├── generate_content.py   # LLM generates reply/quote text with writing samples
│   │       ├── execute_actions.py    # One tab per post, batch all actions, --ask mode
│   │       ├── log_activity.py       # Append to activity log, persist rate limits
│   │       ├── follow_decision.py    # Score follow candidates via 9i criteria
│   │       ├── state_cleansing.py    # Clear per-cycle state fields
│   │       └── scroll_page.py        # 5-15s delay, smooth scroll ×3
│   │
│   ├── tui/                          # Textual TUI (parallel mode)
│   │   ├── __main__.py               # Entry: `python -m x_personas.tui`
│   │   ├── app.py                    # XPersonasTUI(App), persona lifecycle, graceful shutdown
│   │   ├── store.py                  # TUIStore — reactive state, settings, filesystem sync, stats cache
│   │   │
│   │   ├── screens/
│   │   │   ├── dashboard.py          # Persona DataTable, rate bars, status — Tab to enter
│   │   │   ├── persona_detail.py     # Activity table + log + detail panel — drag-resizable
│   │   │   ├── intervene.py          # Manual intervene (force post, reset scroll, etc.)
│   │   │   ├── config_editor.py      # Opens persona.md in system editor ($VISUAL/$EDITOR)
│   │   │   ├── wizard.py             # New-persona setup wizard
│   │   │   ├── history_browser.py    # Activity log browser
│   │   │   ├── settings.py           # Runtime settings (model, intervals, etc.)
│   │   │   └── help_overlay.py       # Keyboard shortcuts reference
│   │   │
│   │   ├── widgets/
│   │   │   ├── help_bar.py           # Single-line footer with keybinding hints
│   │   │   ├── log_stream.py         # Queue-draining RichLog (agent → TUI sink)
│   │   │   ├── error_log.py          # Error-level RichLog widget
│   │   │   ├── activity_table.py     # Activity log DataTable widget
│   │   │   ├── height_splitter.py    # Mouse-draggable horizontal bar (resizes above widget)
│   │   │   └── width_splitter.py     # Mouse-draggable vertical bar (resizes right widget)
│   │   │
│   │   ├── workers/
│   │   │   ├── persona_worker.py     # Runs agent cycle in background, command queue
│   │   │   └── stats_worker.py       # Periodic rate-limit refresh from filesystem
│   │   │
│   │   └── css/
│   │       └── app.tcss              # Catppuccin Mocha theme, layout, splitter styles
│   │
│   ├── models/                       # Pydantic models
│   │   ├── engagement.py             # ActionType, PendingAction, PostDecision, EngagementDecisions
│   │   ├── feed.py                   # PostMetrics, QuotedPost, FeedPost, FeedResponse
│   │   ├── post.py                   # Reply, PostData, ActionResult, PostResponse
│   │   ├── profile.py                # ProfileStats, MediaAttachment
│   │   ├── scored.py                 # ScoreBreakdown, ScoredPost
│   │   └── log.py                    # ActivityLogEntry, ActivityLog
│   │
│   ├── prompts/
│   │   ├── llm_decide_system.md      # System prompt w/ {persona_sections}, {recent_engagements}
│   │   └── llm_decide_user.md        # User prompt w/ {feed_posts}
│   │
│   └── utils/
│       ├── browser.py                # BrowserSession (Playwright lifecycle, auth state)
│       ├── feed.py                   # scroll_down(smooth), get_home_feed(), navigate_home()
│       ├── post.py                   # post(), like(), reply(), quote(), repost(), open_post_tab()
│       ├── mouse.py                  # Cubic Bezier cursor, Fitts's Law overshoot, click ripples
│       ├── _helpers.py               # safe_click(), safe_fill(), safe_type(), extract_text(), etc.
│       ├── selectors.py              # Centralized DOM selectors for X
│       ├── like.py / reply.py / quote.py / repost.py  # Standalone action functions
│       ├── post_data.py              # Full reply tree building via get_post_data()
│       ├── profile.py                # get_profile_stats(), update_persona_file_metadata()
│       ├── edit_profile.py           # edit_profile() for name/bio/location/website
│       └── exceptions.py             # Custom exception hierarchy
│
└── tests/
    ├── test_agent.py                 # 15 unit tests (persona parsing, models, rate limiter, etc.)
    ├── test_agent_multimodal.py      # 2 tests for multimodal payload assembly
    ├── test_agent_replies.py         # 3 tests for reply chaining/dedup/SKIP
    ├── test_actions.py               # Manual live test (like/repost)
    ├── test_cursor_visual.py         # Manual visual test (mouse movements)
    ├── test_feed.py                  # Manual live test (feed scraping)
    └── test_post.py                  # Manual live test (post data)
```

---

## CLI Usage

### Headless mode (default)
```bash
uv run python -m x_personas.agent.runner --persona <name> [flags]
```

Or via the installed script:
```bash
uv run x-personas --persona <name> [flags]
```

### TUI mode
```bash
uv run x-personas tui [--persona <name>] [--quiet]
```

Or via module:
```bash
uv run python -m x_personas.tui [--persona <name>]
```

### All Flags

| Flag | Default | Description |
|---|---|---|---|
| `--persona` | *required* | Persona name (`purusha`) resolves to `personas/purusha/persona.md`; explicit paths also work |
| `--dry-run` | off | Call LLM once with sample posts, no browser |
| `--visible` | off | Show browser window (default headless) |
| `--once` | off | Single cycle, no perpetual loop |
| `--ask` | off | Prompt for approval before each action |
| `--quiet` | off | Suppress debug logs |
| `--browser` | system default | Path to Chromium binary |
| `--scroll-limit` | `2500` | Pixels scrolled before 10-30 min break (`-1` for infinite) |
| `--no-cursor` | off | Disable DOM cursor overlay and click ripples |
| `--auth` | `personas/<name>/auth.json` | Path to save/load browser auth state |

### Quick Examples

```bash
# Dry run — test LLM decisions without browser
uv run x-personas --persona purusa0x6c --dry-run

# Single cycle headless
uv run x-personas --persona purusa0x6c --once

# Continuous visible mode with approval (VLM enabled via VLM_MODEL=gpt-4o in .env)
uv run x-personas --persona purusa0x6c --visible --ask

# Quiet continuous run with explicit path
uv run x-personas --persona personas/purusa0x6c/persona.md --quiet
```

---

## How a Single Cycle Works

```
load_persona → scroll_feed → llm_decide
                              ├── hydrate_replies → generate_content  (reply/quote text)
                              ├── execute_actions                      (like/repost/reply/quote)
                              └── log_activity
→ log_activity → follow_decision → state_cleansing → scroll_page → END
```

1. **load_persona** — Parse 14-section `personas/<name>/persona.md` into structured dict (skipped if already loaded)
2. **scroll_feed** — Extract visible `<article>` elements from DOM, filter by `seen_post_ids` + `engaged_ids`
3. **llm_decide** — Compile persona + feed + recent engagements into prompts, call VLM (or text LLM fallback) with `.with_structured_output(EngagementDecisions)`. Routes to `generate_content` if reply/quote, `execute_actions` if like-only, `log_activity` if none
4. **hydrate_replies** — For reply/quote targets: open Playwright tab per unique `status_id`, scrape thread ancestors/peers via `get_post_data()`
5. **generate_content** — Per reply/quote: VLM call (temp 0.8) with writing samples, thread context, dedup check; supports `[SKIP]` and mutual chaining
6. **execute_actions** — Group by `target_status_id`, one tab per post, batch all actions (like → reply → quote priority), 3-8s delays; `--ask` for approval
7. **log_activity** — Append to `activity-log.md`, persist rate limits
8. **follow_decision** — Score follow candidates via 9i topic overlap criteria
9. **state_cleansing** — Clear `feed_posts`, `pending_actions`, `executed_actions`, etc.
10. **scroll_page** — 5-15s delay, 3× smooth scroll (`behavior: 'smooth'`)

After `--scroll-limit` pixels (default 2500): 10-30 min break, re-navigate to `x.com/home`, reload engaged IDs from activity log.

---

## Key Features

| Feature | Description |
|---|---|
| **LLM-driven decisions** | No keyword-matching. LLM receives full persona profile + feed posts, decides qualitatively |
| **Two-phase engagement** | `llm_decide` (cheap, decides WHAT) → `generate_content` (expensive, writes text with writing samples) |
| **Structured output** | `EngagementDecisions` / `PostDecision` Pydantic models enforced via function calling |
| **Tab-per-post execution** | One Playwright tab per unique `target_status_id`, batches all actions (reply+like = 1 tab) |
| **Realistic behavior** | 3-8s delays, 5-15s scroll delays, smooth scroll, Cubic Bezier cursor, Fitts's Law overshoot |
| **Rate limiting** | Per-cycle (like:5, reply:2, repost:2, quote:1) + hourly + daily, persisted to JSON |
| **Deduplication** | Activity log is source of truth; engaged IDs loaded at cycle start |
| **Break logic** | After N scrolls, 10-30 min break, re-navigate home |
| **Original post scheduler** | Publishes original tweets every N engagements (random 10-20) with time-of-day awareness |
| **Profile sync** | At startup: scrapes live stats, syncs bio, updates persona file |
| **Reply context** | `hydrate_replies` scrapes thread for contextual replies before generation |
| **Mutual chaining** | `generate_content` can chain replies off mutual handles' comments |
| **[SKIP] support** | LLM returns `[SKIP]` to abort when content is saturated or uninteresting |
| **Critique variety policy** | Max 1 critical engagement per cycle; blocked if recent history has critique |
| **Multimodal (optional)** | Feed images sent to VLM for visual context; disabled when `VLM_MODEL` is unset |
| **OpenAI-compatible API** | Works with OpenAI, DeepSeek, Ollama, vLLM, or any OpenAI-compatible endpoint |
| **Custom cursor overlay** | Visual DOM cursor with Bezier easing and click ripple effects (headed mode) |
| **Auth isolation** | Per-persona auth state files (`personas/<name>/auth.json`) |
| **20 tests** | All passing |

---

## TUI Mode

The Textual TUI provides a keyboard-driven, htop-like interface for managing multiple personas in parallel. Launched via `x-personas tui` or `python -m x_personas.tui`.

### Architecture

```
XPersonasTUI (App)
├── TUIStore          — reactive state, persona discovery, filesystem sync, stats cache
├── MainScreen        — single-screen layout: sidebar + main area
│   ├── Sidebar       — persona list (RichLog) + stats + rate bars
│   │   └── WidthSplitter — mouse-draggable bar resizes sidebar width
│   ├── Activity      — DataTable with Time/Action/Target/Score columns
│   │   └── HeightSplitter — mouse-draggable bar resizes activity table height
│   └── Log           — RichLog for live agent output
├── PersonaWorker     — runs agent cycle in background per persona
│   └── command queue  — force original post, reset scroll, etc.
├── StatsWatcher      — periodic rate-limit refresh from filesystem
└── Log sinks         — agent log() → queue → LogStream widget
```

### Keybindings

| Key | Scope | Action |
|---|---|---|
| Up/Down | Sidebar | Navigate persona list |
| Enter | Sidebar | Focus activity table (up/down navigates rows) |
| Up/Down | Activity | Navigate activity rows |
| Enter | Activity | Open detail panel for selected row |
| Esc | Activity | Return focus to sidebar |
| Esc | Global | Cancel quit confirmation / flags mode / compose mode |
| S | Global | Start / Stop selected persona |
| K | Global | Kill (force stop) selected persona |
| I | Global | Manual intervene |
| R | Global | Refresh sidebar + activity |
| O | Global | Enter compose mode (inline footer) |
| G / C / Esc | Compose | Generate / Custom / Cancel |
| C | Global | Open config in system editor |
| H | Global | History browser |
| E | Global | Toggle flags mode (ask, visible) |
| F | Global | Settings |
| ? | Global | Help overlay |
| Q | Global | Quit (confirms if personas are running) |

### Mouse Controls

- **Drag WidthSplitter** (between sidebar and main) — resize sidebar width (15-50 chars)
- **Drag HeightSplitter** (between activity table and log) — resize activity table height (3-30 rows)
- **DataTable rows** — click to select, Enter to open detail panel
- **Focus highlight** — active section gets a blue border (`#89b4fa`)

### Design Principles

- **No buttons** — all actions via keyboard shortcuts
- **Single-screen layout** — sidebar + main area, no tab switching
- **Focus modes** — up/down navigates sidebar personas; Enter switches to activity table; Esc returns
- **Shared filesystem** — TUI reads same `activity-log.md`, `rate-limits.json`, `persona.md` as headless mode
- **Per-persona workers** — each persona runs its own agent cycle in a background task
- **Command queue** — interventions (force original post, reset scroll) dispatched between LangGraph cycles
- **Pluggable log sinks** — agent `log()` writes to queue, TUI drains to LogStream widget
- **Log persistence** — per-persona log buffers survive across persona switches
- **Stats cache** — `stats-cache.json` avoids re-parsing activity logs on startup
- **Graceful shutdown** — quit confirmation when personas are running, workers cleaned up before exit
- **Catppuccin Mocha** — hardcoded hex color scheme across CSS and inline Rich markup

---

## Persona File Format

The persona file is a 14-section markdown document parsed by `load_persona.py`. Sections are referenced by number:

| Section | Content |
|---|---|
| `## 1. Identity & Metadata` | Handle, display name, bio, follower count, etc. |
| `## 2. Linguistic Profile` | Vocabulary, emoji usage, slang, spelling quirks, grammar |
| `## 3. Personality & Vibe` | Personality traits, communication style |
| `## 4. Content Buckets` | Topics the persona posts about |
| `## 5. Posting Behavior` | Frequency, timing, habits |
| `## 6. Reply Behavior` | Length matrix, escalation triggers, reply templates |
| `## 7. Engagement Triggers` | Topics, accounts, formats that trigger engagement |
| `## 8. Topic Stances` | Per-topic stance (like/dislike), intensity, nuance/action policy |
| `## 9a. Topic Affinity Weights` | Numeric weights for topic scoring |
| `## 9b. Account Relationship Weights` | Numeric weights for account relationships |
| `## 9c. Format Affinity Weights` | Numeric weights for post formats |
| `## 9d. Recency Bonus` | Recency-based score adjustments |
| `## 9f. Engagement Thresholds` | Score ranges → action mapping |
| `## 9g. Engagement Type Matrix` | Conditions → engagement type |
| `## 9h. Reply Guidelines` | Free-text reply rules |
| `## 9i. Follow Criteria` | Numeric weights for follow decisions |
| `## 12. Tone Rules` | Tone constraints and rules |
| `## 13. Source Data` | Reference to writing samples files in `source/` dir |

A blank 14-section template lives at `personas/_template/persona.md` (also at `persona-struct.md` at root for legacy access).

---

## File Artifacts

| File | Purpose | Git |
|---|---|---|
| `personas/<name>/persona.md` | Persona definition | ignored |
| `personas/<name>/activity-log.md` | Markdown table of all engagements (dedup source) | ignored |
| `personas/<name>/auth.json` | Browser auth session state | ignored |
| `personas/<name>/rate-limits.json` | Persisted rate limit counters | ignored |
| `personas/<name>/stats-cache.json` | Cached stats (total, today, last action) for fast startup | ignored |
| `personas/<name>/source/` | Writing samples and custom files | ignored |
| `personas/_template/persona.md` | Blank 14-section template | tracked |
| `.env` | API keys and model config | ignored |
