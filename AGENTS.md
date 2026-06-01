## Goal
- Build an autonomous X/Twitter persona agent with LangGraph that mimics human scrolling behavior, uses LLM to decide engagement, and generates content with writing samples.

## Constraints & Preferences
- Persona generator (`src/generate_persona.py`) is separate from the agent — source data feeds into LLM → structured `persona-struct.md` → agent consumes it
- Agent uses LangGraph `StateGraph` — one full cycle per `ainvoke()`, runner loops perpetually
- Scroll happens **after** all decisions (at end of cycle, in `scroll_page` node), not before scoring
- Each engagement opens a new Playwright tab per **post** (all actions for same post batched in one tab, closed after)
- Random delays: 3-8s between actions, 5-15s between scrolls
- After `--scroll-limit` (default 2500), 10-30 min break, re-navigate home, reload engaged IDs from activity log
- Existing activity log markdown table is the dedup source — `history.load_engaged_status_ids()` reads it
- Block-and-wait on interactions — single-threaded, one tab at a time
- LLM provider: DashScope (DeepSeek via Alibaba Cloud, OpenAI-compatible) with env vars
- `--visible` flag shows browser (default headless); `--browser` flag for custom Chromium binary
- `--quiet` flag suppresses debug logs
- Prompts stored in `src/prompts/` as markdown templates with placeholders

## Progress
### Done
- LLM-driven decisions — `llm_decide` node replaces old keyword-matching `ScoringEngine` + threshold-based `decide_engagement`. LLM sees full persona profile + feed posts, returns structured `EngagementDecisions` via `.with_structured_output()` (Pydantic models: `PostDecision` with list action_type, `EngagementDecisions`)
- Two-phase content generation — `llm_decide` only decides WHICH posts to engage; dedicated `generate_content` node generates reply/quote text with writing samples from source data
- Prompts in `src/prompts/` — `llm_decide_system.md` (with `{persona_sections}` placeholder), `llm_decide_user.md` (with `{feed_posts}` placeholder)
- Pydantic models in `src/models/engagement.py` — `PostDecision(action_type: list[str], reason, score)`, `EngagementDecisions(decisions: list[PostDecision])`
- Smooth scroll via `behavior: 'smooth'` in `scroll_down`
- Default scroll-limit 2500; Chromium binary via `--browser /usr/bin/chromium`
- Perpetual agent design: scroll-by-scroll, LangGraph cycle per `ainvoke()`, tab-per-post interaction, random delays, break logic
- New files: `src/prompts/`, `src/agent/nodes/llm_decide.py`
- Rewritten files: `graph.py` (llm_decide + generate_content + conditional routing), `runner.py` (dry-run calls LLM)
- Removed: entire `src/agent/scoring/` directory, `score_posts.py`, `decide_engagement.py`
- Debug logging throughout all nodes with `[HH:MM:SS]` timestamps
- All tests pass (11 tests)

### In Progress
- (none)

### Blocked
- (none)

## Key Decisions
- **LLM makes decisions** — no more keyword-matching formulas. The LLM receives the persona profile + visible posts and returns structured decisions via Pydantic models. This allows qualitative judgment (tone, nuance) instead of keyword counting.
- **Two LLM calls per cycle with text actions** — first `llm_decide` decides which posts to engage (cheaper, faster), then `generate_content` per reply/quote with writing samples (better text quality)
- **`.with_structured_output(EngagementDecisions)`** — LangChain's structured output enforces the response schema via function calling, no manual JSON parsing
- **`action_type` as `list[str]`** — one decision can represent multiple actions for the same post (e.g. `["reply", "like"]`), deduplicated by handle by the code
- Scroll happens after all decisions (`scroll_page` at end of cycle) — lets the agent act on currently visible posts before moving on
- Post actions batched by `target_status_id` in one tab — reply+like on same post costs one tab open/close instead of two
- `--visible` replaces `--headless` — headless is default, `--visible` toggles it off
- Custom browser via `--browser` flag threaded through `BrowserSession(executable_path=...)`
- Debug logs are print-based via `log()` utility with `set_quiet()` toggle

## Next Steps
- Run with `--dry-run` to verify LLM decisions without launching browser
- Run live with `--visible` to watch the agent scroll and engage

## Critical Context
- `auth.json` exists (249KB) — browser session already authenticated
- `.env` has DashScope credentials set
- `purusha-persona-struct.md` has all 14 sections including 9f thresholds, 9g matrix, 9h guidelines
- Rate limits persist via `.rate-limits-<persona>.json`
- Activity log is `<persona>-activity-log.md` markdown table
- `--dry-run` now calls the LLM once with sample posts — costs a tiny amount per run

## Relevant Files
- `src/prompts/llm_decide_system.md` — system prompt template for engagement decisions
- `src/prompts/llm_decide_user.md` — user prompt template with feed posts
- `src/agent/nodes/llm_decide.py` — LLM-driven decision node
- `src/agent/nodes/generate_content.py` — dedicated LLM call per reply/quote with writing samples
- `src/agent/nodes/execute_actions.py` — batch actions by post ID, one tab per post, 3-8s delays
- `src/agent/graph.py` — perpetual loop with conditional routing: scroll_feed → llm_decide → [generate_content → execute_actions | execute_actions | log_activity] → log_activity → follow_decision → state_cleansing → scroll_page → END
- `src/agent/runner.py` — `--visible`, `--quiet`, `--browser`, `--scroll-limit 2500`, perpetual loop with breaks, dry-run calls LLM
- `src/agent/history.py` — `load_engaged_status_ids()` reads `<persona>-activity-log.md`
- `src/agent/log.py` — `log()` and `set_quiet()`
- `src/models/engagement.py` — `PostDecision`, `EngagementDecisions` Pydantic models for structured output
- `src/utils/feed.py` — `scroll_down()` with smooth scroll
