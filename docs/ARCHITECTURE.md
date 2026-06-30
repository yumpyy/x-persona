# Architecture

## LangGraph Flow

The agent is built as a `StateGraph(PersonaState)` with 10 nodes and conditional routing.

```
                         ┌──────────────────┐
                         │   load_persona    │
                         │  (skip if loaded) │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │   scroll_feed     │
                         │  (parse articles, │
                         │   filter seen)    │
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │   llm_decide      │
                         │  (LLM structured  │
                         │   output)         │
                         └────────┬─────────┘
                                  │
              ┌───────────────────┼────────────────────┐
              │  reply/quote      │  like-only         │  none
              ▼                   ▼                     ▼
     ┌────────────────┐  ┌───────────────┐   ┌────────────────┐
     │ hydrate_replies │  │ execute_act-  │   │  log_activity   │
     │ (scrape thread) │  │ ions (like,   │   │                 │
     └────────┬───────┘  │ repost)       │   └────────┬───────┘
              │          └───────┬───────┘            │
              ▼                  │                    │
     ┌────────────────┐         │                    │
     │generate_content│         │                    │
     │(LLM per reply, │         │                    │
     │ temp 0.8)      │         │                    │
     └────────┬───────┘         │                    │
              │                 │                    │
              ▼                 ▼                    │
     ┌───────────────────────────────────────────────┘
     │               execute_actions
     │     (batch per post, one tab each)
     └──────────────────────┬───────────────────────┘
                            │
                    ┌───────▼────────┐
                    │  log_activity   │
                    │  (append to     │
                    │  activity log,  │
                    │  persist limits)│
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │ follow_decision │
                    │ (score follow   │
                    │  candidates)    │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │state_cleansing │
                    │ (clear cycle   │
                    │  state)        │
                    └───────┬────────┘
                            │
                    ┌───────▼────────┐
                    │  scroll_page   │
                    │  (5-15s delay, │
                    │   3x smooth)   │
                    └───────┬────────┘
                            │
                            ▼
                          END
```

## State (PersonaState)

Defined in `x_personas/agent/state.py` as a `TypedDict` with 18 fields:

```python
class PersonaState(TypedDict):
    persona_file: str                    # Path to the persona markdown
    activity_log_file: str               # Path to activity log
    llm_config: dict                     # LLM provider config
    persona_sections: dict               # Parsed persona (14 sections)
    source_data_files: list[str]         # Writing sample file paths
    feed_posts: list[FeedPost]           # Visible posts in current cycle
    feed_scroll_position: str | None     # Scroll position tracking
    scored_posts: list[ScoredPost]       # (legacy)
    pending_actions: list[PendingAction] # Actions queued for execution
    executed_actions: list[ExecutedAction] # Completed actions
    thread_contexts: dict[str, PostData]  # Reply thread cache
    follow_candidates: list[FeedPost]    # Accounts to consider following
    follows_this_session: int            # Follows in current session
    rate_limit_file: str                 # Path to rate limit JSON
    cycle_action_counts: dict[str, int]  # Per-cycle action usage
    seen_post_ids: list[str]             # Post IDs seen this session
    engaged_ids: list[str]               # Post IDs engaged historically
    scroll_count: int                    # Total scrolls in session
    error: str | None                    # Error state
```

Internal routing key `_routing_target` (not in TypedDict) determines the next node after `llm_decide` and `generate_content`.

## Conditional Routing

Defined in `graph.py`:

```python
builder.add_conditional_edges(
    "llm_decide",
    lambda s: s.get("_routing_target", "log_activity"),
    {
        "generate_content": "hydrate_replies",   # reply/quote → scrape thread
        "execute_actions": "execute_actions",     # like-only → execute
        "log_activity": "log_activity",           # none → skip
    }
)

builder.add_conditional_edges(
    "generate_content",
    lambda s: s.get("_routing_target", "execute_actions"),
    # Always routes to execute_actions after content generation
)
```

## Node Details

### load_persona
- **File:** `x_personas/agent/nodes/load_persona.py`
- **Idempotent:** Returns `{}` if `persona_sections` already populated (Graph sets `set_entry_point` but subsequent cycles skip)
- Parses 14 sections from markdown: identity tables, linguistic profile sub-tables, engagement trigger tables, numeric weight tables, engagement matrix rows, follow criteria
- Extracts source data file paths from section 13
- **Notable parsers:**
  - `_parse_linguistic_profile()` — vocabulary/emoji/slang sub-sections in section 2
  - `_parse_reply_matrix()` — length matrix, escalation triggers, common reply templates in section 6
  - `_parse_engagement_triggers()` — topics, accounts, formats in section 7
  - `_parse_decision_weights()` — sections 9a-9d key→float tables
  - `_parse_thresholds()` — section 9f score→action pairs
  - `_parse_engagement_matrix()` — section 9g condition→action rows
  - `_parse_follow_criteria()` — section 9i key→float pairs

### scroll_feed
- **File:** `x_personas/agent/nodes/fetch_feed.py`
- Queries `article[data-testid="tweet"]` elements from current page DOM
- Calls `_parse_article()` to extract: status_id, author, handle, text, timestamp, metrics, media, verification status, reply/quote/retweet flags
- Filters out posts in `seen_post_ids` (session) and `engaged_ids` (historical activity log)
- Returns new posts + updated `seen_post_ids`

### llm_decide
- **File:** `x_personas/agent/nodes/llm_decide.py`
- Compiles persona sections into system prompt text via `_build_persona_text()`:
  - Section 1 → Persona Identity
  - Section 2 → Linguistic Style (vocabulary, emoji, slang, quirks)
  - Section 3 → Personality & Vibe
  - Section 4 → Content Buckets
  - Section 5 → Posting Behavior
  - Section 6 → Reply Behavior (length matrix, escalation triggers, templates)
  - Section 7 → Engagement Triggers (topics, accounts, formats)
  - Section 8 → Topic Stances
  - Sections 9a-9i → Weights, thresholds, matrix, guidelines, follow criteria
  - Section 12 → Tone Rules
  - Section 13 → Source Data files
- Renders feed posts into user prompt text via `_build_feed_text()`
- Loads `llm_decide_system.md` and `llm_decide_user.md` templates, replaces `{persona_sections}`, `{recent_engagements}`, `{feed_posts}`
- Appends up to 4 image URLs from feed posts to the user content for multimodal reasoning
- Calls LLM with `.with_structured_output(EngagementDecisions)` at temperature 0.0 (deterministic)
- Enforces **critique variety policy** in Python:
  - Loads recent 10 engagements via `load_recent_engagements()`
  - Detects disliked topics from section 8 stances
  - If recent history has critique → discards all critical decisions
  - Caps critical decisions at 1 per cycle
- Converts decisions to `PendingAction`s via `_decisions_to_pending()`:
  - Maps action_type strings to `ActionType` enum
  - Enforces per-cycle caps (like:5, reply:2, repost:2, quote:1)
  - Checks hourly/daily limits via `RateLimitState.can_act()`
  - Deduplicates by handle (one handle per cycle)
- Sets `_routing_target`:
  - `"generate_content"` if any reply/quote pending
  - `"execute_actions"` if only likes/reposts
  - `"log_activity"` if no actions

### hydrate_replies
- **File:** `x_personas/agent/nodes/hydrate_replies.py`
- For each pending reply/quote action:
  - Opens a Playwright tab via `get_post_data(ctx, status_id)`
  - Scrapes: main post text, metrics, media URLs, and up to 15 scrolls of replies
  - Caches result in `thread_contexts[status_id]`
- Skips already-cached status_ids

### generate_content
- **File:** `x_personas/agent/nodes/generate_content.py`
- For each pending reply/quote (where `content is None`):

  **Reply-to-Reply Chaining:**
  - Extracts close mutual handles from section 7 (`"friend"` or `"mutual"` in relationship field)
  - Scans thread replies for mutual handles
  - If found: pivots `target_status_id` and `target_handle` to the mutual's reply for reply-to-reply chaining

  **Content Generation:**
  - Builds system prompt: core guidelines + full persona text via `_build_system_text()`
  - Builds user prompt with:
    - Action label (reply/quote) and target handle
    - Reason for engaging
    - Existing replies on thread (up to 15) for **deduplication check**
    - CRITICAL DEDUPLICATION CHECK: tells LLM to return `[SKIP]` if no fresh angle
    - Writing samples from source data files (up to 3 files, 600 chars each)
    - Recent 15 engagements for **repetition avoidance** (don't repeat your own recent content)
    - Diversity rules (don't copy-paste reply templates)
    - Technical accuracy rules (don't force jargon that doesn't fit)
    - Persona voice rules (matching vocabulary, casing, emoji, slang)
  - Appends up to 2 media URLs from thread context for multimodal
  - Calls LLM with `.with_structured_output(GeneratedText)` at temperature 0.8
  - If response is `[SKIP]`: removes action from pending list
  - On error: removes action from pending list (boundary protection)

  **generate_original_post()** (called from runner):
  - Same approach but includes time-of-day alignment and recent original post history for diversity
  - Forces under 140 characters
  - Temperature 0.85

### execute_actions
- **File:** `x_personas/agent/nodes/execute_actions.py`
- Groups pending actions by `target_status_id`
- For each group:
  - Sorts by priority: REPOST(0) → LIKE(1) → REPLY(2) → QUOTE(3)
  - **`--ask` mode:** Prompts user for [Y/n/s] before executing
  - Opens one tab per post via `open_post_tab(ctx, status_id)`
  - Simulates human reading dwell time (2.5-6s) before acting
  - Executes each action sequentially via:
    - `like_on_page(page)` / `repost_on_page(page)` / `reply_on_page(page, text)` / `quote_on_page(page, text)`
  - Verifies each action (checks button flipped states)
  - Records `ExecutedAction` with success/error and timestamp
  - 3-8s delay between actions (same tab)
  - Closes tab after all actions on that post
- Returns `executed_actions` list and clears `pending_actions`

### log_activity
- **File:** `x_personas/agent/nodes/log_activity.py`
- Initializes activity log file if absent (creates markdown table header)
- For each executed action:
  - Formats entry: `| timestamp | action_type | @handle / status_id | content | score | reason [✓/✗] |`
  - Appends to `<name>-activity-log.md`
  - Records successful actions in `RateLimitState` (for hourly/daily tracking)
- Persists rate limit state to `.rate-limits-<name>.json`

### follow_decision
- **File:** `x_personas/agent/nodes/follow_decision.py`
- Scores each feed post against follow criteria from section 9i:
  - topic overlap (weight 0.4)
  - mutual connections (weight 0.3)
  - posting frequency & quality (weight 0.2)
  - bio similarity (weight 0.1)
- Score ≥ 7 and within session limit → "follow" candidate
- Score ≥ 5 → "observe" candidate
- Session limit: max 3 follows per hour

### state_cleansing
- **File:** `x_personas/agent/nodes/state_cleansing.py`
- Clears all per-cycle state fields:
  - `feed_posts`, `feed_scroll_position`, `scored_posts`
  - `pending_actions`, `executed_actions`
  - `follow_candidates`, `cycle_action_counts`
  - `error`

### scroll_page
- **File:** `x_personas/agent/nodes/scroll_page.py`
- Waits 5-15s (random uniform) — simulates human reading
- Scrolls 3 times via `scroll_down(page, times=3)` using `behavior: 'smooth'`
- Increments `scroll_count` by 3

## Runner (`runner.py`)

The `run_perpetual()` function handles:

**Startup:**
1. Resolves persona file path, validates it's non-empty
2. Selects auth state file: `auth-<persona>.json` (per-persona) or `auth.json` (shared)
3. Loads engaged status IDs from activity log
4. Launches `BrowserSession` (headless by default)
5. Navigates to `x.com/home`
6. Detects logged-in handle from DOM
7. Scrapes live profile stats via `get_profile_stats()` and compares with persona file
8. If bio mismatch: updates X.com bio via `edit_profile()`
9. Syncs profile stats back to persona file via `update_persona_file_metadata()`
10. Initializes original post scheduler counters from history

**Main loop:**
1. Calls `graph.ainvoke(state, config)` — one LangGraph cycle
2. Logs cycle summary: scroll count, new posts, pending/executed actions
3. **Original Post Scheduler:** After N engagements (random 10-20), generates and publishes an original tweet via `generate_original_post()` + `post()`
4. If `--once`: exits after one cycle
5. **Break logic:** When `scroll_count >= scroll_limit`:
   - Waits 600-1800s (10-30 min)
   - Re-navigates to `x.com/home`
   - Resets `scroll_count`, reloads `engaged_ids` from activity log, clears `seen_post_ids`

### Dynamic Config Injection

The runner injects `browser_context` and `home_page` via `config["configurable"]`, so graph nodes can access the browser without being passed in state:

```python
config = {
    "configurable": {
        "thread_id": persona_name,
        "browser_context": ctx,
        "home_page": home_page,
        "llm_config": llm_config,
        "ask": ask,
    }
}
```
