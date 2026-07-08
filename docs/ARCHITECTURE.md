# Architecture

How xpersonas is built.

---

## System overview

```
┌─────────────────────────────────────────────────────────┐
│                      xpersonas                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐  ┌──────────┐                            │
│  │   API    │  │   CLI    │                            │
│  │(FastAPI) │  │(typer)   │                            │
│  └────┬─────┘  └────┬─────┘                            │
│       └──────────────┼──────────────┘                  │
│                      │                                  │
│  ┌───────────────────▼───────────────────┐             │
│  │           Agent Runner                 │             │
│  │  (asyncio tasks, one per persona)      │             │
│  └───────────────────┬───────────────────┘             │
│                      │                                  │
│  ┌───────────────────▼───────────────────┐             │
│  │         LangGraph StateGraph           │             │
│  │  (strategy-aware topology)             │             │
│  └───────────────────┬───────────────────┘             │
│                      │                                  │
│  ┌─────────┬─────────┼─────────┐                       │
│  │         │         │         │                       │
│  ▼         ▼         ▼         ▼                       │
│ ┌────┐  ┌────┐  ┌────┐  ┌────┐                        │
│ │ X  │  │Red-│  │Link│  │Mast│  Platform Adapters     │
│ │Twit│  │dit │  │edIn│  │odon│                        │
│ └────┘  └────┘  └────┘  └────┘                        │
│                                                         │
│  ┌───────────────────────────────────────┐             │
│  │          Storage (SQLite)              │             │
│  │  tenants, personas, activity_log,     │             │
│  │  rate_limits, agent_runs, metrics     │             │
│  └───────────────────────────────────────┘             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Agent runtime

### AgentRunner

`AgentRunner` (`agent/runner.py`) manages the lifecycle of agent instances. Each persona runs as an independent asyncio task.

```python
runner = AgentRunner(db, max_concurrent=5)
instance = await runner.start_persona(persona_id)
```

Each persona gets:
- Its own asyncio task
- Its own Playwright BrowserContext (browser session isolation)
- Its own LangGraph graph instance
- Independent state (engaged IDs, seen IDs, scroll count)

### Graph topology

The graph changes based on `persona_config.engagement.strategy`. Built by `build_graph(strategy)` in `agent/graph.py`.

**active / selective / relationship_building:**
```
load_persona → fetch_content → llm_decide → hydrate_context → generate_content → execute_actions → log_activity → state_cleansing → scroll_page → END
```

**curation:**
```
load_persona → fetch_content → llm_decide → generate_content → execute_actions → log_activity → state_cleansing → scroll_page → END
```

**monitor_and_escalate / competitive_intel:**
```
load_persona → fetch_content → llm_decide → log_activity → state_cleansing → END
```

**support:**
```
load_persona → fetch_content → llm_decide → hydrate_context → generate_content → execute_actions → log_activity → state_cleansing → END
```

### Agent state

State flows through the graph as a `TypedDict`. Key fields:

| Field | Description |
|-------|-------------|
| `persona_config` | Full persona JSON |
| `feed_posts` | Posts fetched from the platform |
| `pending_actions` | Actions decided by LLM, waiting to execute |
| `executed_actions` | Actions that have been executed |
| `engaged_ids` | Post IDs the persona has engaged with (historical) |
| `seen_ids` | Post IDs seen this cycle (dedup) |
| `thread_contexts` | Reply threads for posts being engaged with |
| `_routing_target` | Controls which node to visit next |

---

## Platform adapters

### PlatformAdapter ABC

Every platform implements this interface (`platforms/base.py`):

```python
class PlatformAdapter(ABC):
    @property
    def name(self) -> str: ...
    @property
    def supported_actions(self) -> list[str]: ...

    async def initialize(self, auth: AuthConfig) -> None: ...
    async def shutdown(self) -> None: ...

    async def fetch_feed(self, cursor=None, limit=20) -> tuple[list[PlatformPost], str | None]: ...
    async def search(self, query: str, limit=20) -> list[PlatformPost]: ...
    async def get_post_detail(self, post_id: str) -> PlatformPost: ...
    async def get_replies(self, post_id: str, limit=20) -> list[PlatformPost]: ...

    async def like(self, post_id: str) -> PlatformActionResult: ...
    async def reply(self, post_id: str, text: str) -> PlatformActionResult: ...
    async def repost(self, post_id: str) -> PlatformActionResult: ...
    async def quote(self, post_id: str, text: str) -> PlatformActionResult: ...
    async def follow(self, author_id: str) -> PlatformActionResult: ...
    async def post_original(self, text: str) -> PlatformActionResult: ...

    async def navigate_home(self) -> None: ...
    async def scroll(self, times: int = 1) -> None: ...
```

### Registry

Adapters are registered via decorator:

```python
@register_adapter
class XTwitterAdapter(PlatformAdapter):
    ...
```

Discovery happens at import time. The `get_adapter(platform_name)` function returns a new instance.

### X/Twitter adapter

The X adapter uses Playwright for browser automation:

| Module | What it does |
|--------|-------------|
| `adapter.py` | `XTwitterAdapter`: implements `PlatformAdapter` |
| `browser.py` | `BrowserSession`: Chromium launch, auth state, anti-detection |
| `feed.py` | DOM parsing: extracts posts from `article[data-testid="tweet"]` |
| `actions.py` | Like, reply, quote, repost, follow, post, all via Playwright |
| `mouse.py` | Bezier curve mouse movement, character-by-character typing |
| `selectors.py` | CSS selectors (single source of truth) |

---

## Storage

### SQLite with WAL mode

- **WAL mode**: concurrent reads while writing
- **Foreign keys**: enforced via `PRAGMA foreign_keys=ON`
- **JSON columns**: persona config, product features, etc. stored as JSON
- **Busy timeout**: 5000ms to handle concurrent access

### Schema (14 tables)

```
tenants ──┬── personas ──┬── activity_log
          │              ├── rate_limits
          │              ├── agent_runs
          │              ├── browser_sessions
          │              ├── escalations
          │              ├── metrics
          │              ├── contacts ──── contact_interactions
          │              └── products
          └── api_keys
```

### Repositories

Each table has a repository class:

| Repo | Table | Key methods |
|------|-------|-------------|
| `TenantRepo` | `tenants` | `create`, `get`, `list_all`, `update`, `delete` |
| `PersonaRepo` | `personas` | `create`, `get`, `list_for_tenant`, `update`, `delete` |
| `ActivityRepo` | `activity_log` | `record`, `get_engaged_ids`, `get_recent`, `get_stats` |
| `RateLimitRepo` | `rate_limits` | `record`, `can_act`, `get_status` |
| `ProductRepo` | `products` | `create`, `get`, `list_for_tenant`, `delete` |
| `ContactRepo` | `contacts` | `upsert_interaction`, `list_for_persona`, `get_ready_for_connection` |
| `EscalationRepo` | `escalations` | `create`, `list_for_persona`, `acknowledge`, `pending` |
| `RunRepo` | `agent_runs` | `create`, `update_status`, `get_running`, `list_running` |

---

## API server

### FastAPI with lifespan

The server starts an `AgentRunner` on startup and shuts it down on exit:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    db = init_db(db_path)
    runner = AgentRunner(db)
    set_runner(runner)
    yield
    await runner.stop_all()
```

### Dependency injection

```python
# deps.py
_db: Database | None = None

def init_db(db_path: str) -> Database:
    global _db
    _db = Database(db_path)
    _db.connect()
    _db.initialize()
    return _db

def get_db() -> Database:
    return _db
```

Routes use `Depends(get_db)` to get the database connection.

---

## LLM integration

### Two-phase decision making

1. **llm_decide**: LLM reads the feed and decides which posts to engage with. Returns structured `EngagementDecisions` with actions, scores, and reasons.

2. **generate_content**: For each action that needs text (reply, quote), LLM generates content in the persona's voice using writing samples.

### Model

Uses `langchain_openai.ChatOpenAI` with structured output:

```python
llm = ChatOpenAI(model="your-model", temperature=0.0)
structured_llm = llm.with_structured_output(EngagementDecisions)
response = await structured_llm.ainvoke([...])
```

### Persona compilation

The persona config is compiled into a text block for the LLM prompt:

```
Identity: Dev Tools Fan (@devtoolsfan)
Bio: I try every dev tool so you don't have to.
Occupation: Developer Advocate
Traits: helpful, technical, opinionated
Vibe: Experienced dev who's seen it all
Topics you care about:
  - CI/CD: love (intensity 8)
  - slow builds: dislike (intensity 7)
```

---

## Adding a new platform

1. Create `xpersonas/platforms/<platform_name>/`
2. Implement `PlatformAdapter` in `adapter.py`
3. Use `@register_adapter` decorator
4. Implement browser automation in `browser.py`, `feed.py`, `actions.py`
5. Import the adapter module in `xpersonas/platforms/__init__.py`

The agent graph is platform-agnostic: it calls `adapter.search()`, `adapter.like()`, etc. The graph doesn't know or care which platform it's talking to.
