# LangGraph Agent Architecture — X Personas

## Directory structure

```
x_personas/
├── agent/
│   ├── __init__.py
│   ├── config.py             # LLM provider config (OpenAI/Anthropic)
│   ├── graph.py              # StateGraph definition + compilation
│   ├── runner.py             # CLI entry point (on-demand + --loop)
│   ├── state.py              # PersonaState TypedDict
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── load_persona.py
│   │   ├── fetch_feed.py
│   │   ├── score_posts.py
│   │   ├── decide_engagement.py
│   │   ├── generate_content.py
│   │   ├── execute_actions.py
│   │   ├── log_activity.py
│   │   └── follow_decision.py
│   └── scoring/
│       ├── __init__.py
│       └── engine.py         # Deterministic scoring formula
├── models/
│   ├── __init__.py            # + new exports
│   ├── feed.py                # existing
│   ├── post.py                # existing
│   ├── scored.py              # NEW
│   ├── engagement.py          # NEW
│   └── log.py                 # NEW
└── utils/
    ├── __init__.py
    ├── browser.py             # existing
    ├── feed.py                # existing
    └── post.py                # existing + add quote(), reply()
```

---

## New models

### models/scored.py

| Model | Fields | Description |
|---|---|---|
| `ScoreBreakdown` | topic_affinity, account_relationship, format_affinity, recency_bonus, final_score | Component scores from the formula |
| `ScoredPost` | post: FeedPost, score: float, breakdown: ScoreBreakdown | Feed post + computed score |

### models/engagement.py

| Model | Fields | Description |
|---|---|---|
| `ActionType(Enum)` | LIKE, REPLY, REPOST, QUOTE | Valid engagement types |
| `PendingAction` | action_type, target_status_id, target_handle, content (str\|None), score, reason | An action queued for execution |
| `ExecutedAction` | action: PendingAction, success, error, timestamp | Result of executing an action |

### models/log.py

| Model | Fields | Description |
|---|---|---|
| `ActivityLogEntry` | timestamp, action, target, content, score, context | One row in the activity log |
| `ActivityLog` | entries: list[ActivityLogEntry], activity_log_file: str | Wrapper for the log file |

---

## State (TypedDict)

```python
class PersonaState(TypedDict):
    persona_file: str
    activity_log_file: str
    llm_config: dict

    persona_sections: dict           # parsed persona markdown sections
    source_data_files: list[str]     # section 13 references

    feed_posts: list[FeedPost]
    feed_scroll_position: str | None

    scored_posts: list[ScoredPost]

    pending_actions: list[PendingAction]
    executed_actions: list[ExecutedAction]

    follow_candidates: list[FeedPost]
    follows_this_session: int
```

---

## Node design

| Node | What it does | LLM? | Routing |
|---|---|---|---|
| `load_persona` | Reads persona-struct.md, parses tables into dict | No | → `fetch_feed` |
| `fetch_feed` | Calls `get_home_feed()` on x.com/home | No | → `score_posts` |
| `score_posts` | Applies scoring formula to each post | No | → `decide_engagement` |
| `decide_engagement` | Applies thresholds + engagement type matrix, produces pending actions | No | → `generate_content` or → `execute_actions` or → `log_activity` |
| `generate_content` | Generates reply/quote text matching persona linguistic profile | Yes | → `execute_actions` |
| `execute_actions` | Calls Playwright tools (like, repost, quote, reply) | No | → `log_activity` |
| `log_activity` | Appends to `<persona>-activity-log.md` | No | → `follow_decision` |
| `follow_decision` | Scores accounts using section 9i criteria, optionally follows | No | → `END` |

---

## Graph flow

```
START
  → load_persona
  → fetch_feed
  → score_posts
  → decide_engagement
      │
      ├─ [pending_actions with reply/quote] → generate_content → execute_actions
      ├─ [pending_actions like/repost only] → execute_actions
      └─ [no actions] ─────────────────────→
      │
      ↓
  → log_activity
  → follow_decision
  → END
```

- `decide_engagement` uses `Command` to route: if any pending action needs LLM-generated text, it routes to `generate_content`; if actions are purely mechanical (like, repost), it routes directly to `execute_actions`; if no actions, it skips straight to `log_activity`.
- `execute_actions` loops through all pending actions in order, calling the appropriate Playwright tool for each.

---

## Scoring engine

File: `x_personas/agent/scoring/engine.py`

Pure Python. No LLM calls. Implements the formula from persona-struct.md section 9:

```
score = (topic_affinity × 0.4) + (account_relationship × 0.3) + (format_affinity × 0.2) + (recency_bonus × 0.1)
```

```python
class ScoringEngine:
    def __init__(self, persona_sections: dict):
        self.topic_weights = persona_sections["9a"]
        self.account_weights = persona_sections["9b"]    # has baked-in defaults
        self.format_weights = persona_sections["9c"]
        self.recency_bonus = persona_sections["9d"]       # has baked-in defaults

    def score_post(self, post: FeedPost) -> ScoredPost:
        topic = self._detect_topic(post.text)        # keyword matching against 9a labels
        topic_score = self.topic_weights.get(topic, 5)  # default 5 if no match
        account_score = self.account_weights.get(...)   # lookup by handle or default
        format_score = self.format_weights.get(...)
        recency = self._compute_recency(post.timestamp)
        final_score = topic_score*0.4 + account_score*0.3 + format_score*0.2 + recency*0.1
        return ScoredPost(...)
```

Topic detection uses keywords from section 7 (engagement triggers — topics) combined with the category labels from section 9a.

---

## LLM content generation

File: `x_personas/agent/config.py`

```python
def get_llm(config: dict):
    provider = config.get("provider", "openai")
    model = config.get("model", "gpt-4o-mini")
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model)
```

Node `generate_content` builds a system prompt from:

- Linguistic profile (section 2)
- Reply length matrix (section 6)
- Reply escalation triggers (section 6)
- Reply generation guidelines (section 9h)
- Source data samples (section 13)
- Recent activity log entries (to avoid repetition)

One LLM call per pending reply/quote action.

---

## Utils to add: quote() and reply()

Both added to existing `x_personas/utils/post.py`.

```python
async def reply(context: BrowserContext, status_id: str, text: str) -> ActionResult
    # Navigate to x.com/i/status/{status_id}
    # Click reply button
    # Type text in textarea
    # Click submit

async def quote(context: BrowserContext, status_id: str, text: str) -> ActionResult
    # Navigate to x.com/i/status/{status_id}
    # Click retweet button → select "Quote"
    # Type text
    # Click submit
```

---

## Runner

File: `x_personas/agent/runner.py`

```
Usage:
  python -m x_personas.agent.runner --persona cneural-net-persona.md --headless
  python -m x_personas.agent.runner --persona cneural-net-persona.md --loop --interval 1800
  python -m x_personas.agent.runner --persona cneural-net-persona.md --provider anthropic --model claude-sonnet-4-20250514
```

```python
async with BrowserSession(headless=args.headless) as ctx:
    graph = create_graph()
    config = {"configurable": {"thread_id": persona_name, "browser_context": ctx, "llm_config": llm_config}}
    state = {"persona_file": args.persona, "activity_log_file": activity_log}

    if args.loop:
        while True:
            await graph.ainvoke(state, config)
            await asyncio.sleep(args.interval)
    else:
        await graph.ainvoke(state, config)
```

---

## Error handling

| Error type | Strategy |
|---|---|
| Playwright timeout (feed, actions) | Retry policy: 3 attempts, exponential backoff |
| LLM content generation failure | Store error in state, loop back with context for retry |
| Like/repost/reply action fails | Log failure, continue to next pending action |
| Persona file not found | Let error bubble up — exit with message |
| Browser session lost | Runner detects and restarts session |

---

## Summary

| Item | Count |
|---|---|
| New model files | 3 (scored.py, engagement.py, log.py) |
| New agent files | 8 (state.py, graph.py, config.py, runner.py, 4 node files) |
| New scoring files | 2 (init, engine.py) |
| Modified files | 2 (models/init.py + utils/post.py) |
| Total new Python files | ~14 |
| LLM calls per cycle | 0 to N (one per reply/quote action) |
