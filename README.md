# xpersonas

Self-hosted platform for running autonomous AI personas on social media.

Define a persona. Agent lives that identity. Scrolling, reading, engaging, posting like a real human.

> **Not** a scheduling tool, analytics dashboard, or chatbot. It's an autonomous agent.

---

<!-- TODO: add screenshot or screen recording here -->
<!-- ![xpersonas demo](docs/demo.png) -->

---

## Architecture

```mermaid
graph TB
    subgraph "Entry Points"
        CLI[CLI<br/>Typer + Rich]
        API[REST API<br/>FastAPI + Swagger]
    end

    subgraph "Agent Runtime"
        Runner["AgentRunner<br/>asyncio task pool<br/>semaphore-constrained"]
        Graph["LangGraph StateGraph<br/>7 strategies, 13 nodes<br/>dynamic topology"]
        State["AgentState<br/>TypedDict flowing through graph"]

        Runner --> Graph
        Graph --> State
    end

    CLI --> Runner
    API --> Runner

    subgraph "LLM Layer"
        LLM["OpenAI-compatible API<br/>structured output<br/>Pydantic models"]
    end

    State <-->|decisions + content| LLM

    subgraph "Platform Adapters"
        Registry["Adapter Registry<br/>auto-discovery<br/>decorator-based"]
        X["XTwitterAdapter<br/>Playwright"]
        Registry --> X
    end

    Graph <-->|search, like, reply, quote| Registry

    subgraph "Browser Layer"
        Browser["Chromium<br/>headless / visible<br/>slowmo support"]
        AntiDet["Anti-Detection<br/>Bezier mouse motion<br/>char-by-char typing<br/>random delays 50-150ms"]
        Auth["Auth State<br/>per-persona cookies<br/>session persistence"]
    end

    X --> Browser
    Browser --> AntiDet
    Browser --> Auth

    subgraph "Storage Layer"
        DB[("SQLite<br/>WAL mode<br/>12 tables")]
        Repos["8 Repositories<br/>Tenant, Persona, Activity<br/>RateLimit, Product, Contact<br/>Escalation, Run"]
    end

    Runner --> DB
    DB --> Repos

    subgraph "Anti-Detection"
        Scroll["Smooth Scroll<br/>behavior: smooth"]
        Timing["Random Delays<br/>3-8s actions<br/>2-5s cycles"]
        Breaks["Break Logic<br/>10-30min after ~2500 posts"]
    end

    AntiDet --> Scroll
    AntiDet --> Timing
    AntiDet --> Breaks
```

### Agent graph topology

The graph changes at runtime based on `persona_config.engagement.strategy`. Conditional edges route through different node paths:

```mermaid
flowchart TB
    Start([cycle start]) --> LP[load_persona<br/>parse config, resolve strategy]
    LP --> FC[fetch_content<br/>feed scroll or topic search]
    FC --> LLM{llm_decide<br/>LLM scores posts<br/>returns EngagementDecisions}

    LLM -->|reply / quote| HC[hydrate_context<br/>fetch thread ancestors<br/>check dedup]
    LLM -->|like / repost| EA[execute_actions<br/>Playwright browser<br/>with anti-detection]
    LLM -->|promo mention| PE[promo_engage<br/>pain point search<br/>frequency caps]
    LLM -->|no action| LA[log_activity]

    HC --> GC[generate_content<br/>LLM writes in persona voice<br/>using writing samples]
    GC --> EA
    PE --> GC

    EA --> LA

    LA --> RT[relationship_track<br/>contact scoring<br/>rapport + stage]
    RT --> SC[state_cleansing<br/>clear transient state<br/>preserve history]
    SC --> SP[scroll_page<br/>smooth scroll<br/>increment counter]
    SP --> END([cycle end / break check])
```

### Strategy matrix

| Strategy | Nodes | Behavior |
|----------|-------|----------|
| `active` | all 13 | Full loop: search, decide, generate, execute, track |
| `selective` | all 13 | Same topology, higher LLM score threshold |
| `relationship_building` | all 13 | Fewer actions, more contact tracking |
| `curation` | 10 | Skip hydrate_context, no reply threads |
| `support` | 11 | Search-based fetch, reply-only |
| `monitor_and_escalate` | 6 | Log only, no actions, webhook escalation |
| `competitive_intel` | 6 | Log only, sentiment tracking |

[Full architecture docs](docs/ARCHITECTURE.md)

---

## Quick start

### Prerequisites

- Python 3.12+
- OpenAI-compatible API key
- Chromium (via Playwright)

### Install

```bash
git clone <repo-url> && cd x-personas
uv sync
playwright install chromium
```

### Configure LLM

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="your-model"
```

### Initialize and run

```bash
# Setup database + first tenant
xpersonas init setup --db xpersonas.db --tenant-name "MyCompany"

# Create a persona
xpersonas persona create --db xpersonas.db --tenant-id <id> --handle "mybot" --display-name "My Bot" --strategy "active"

# Start agent (headless)
xpersonas agent start <persona_id> --db xpersonas.db

# Or watch it work (visible browser + confirm each action)
xpersonas agent start <persona_id> --visible --ask

# Dry run (validates graph, no browser)
xpersonas agent once <persona_id> --dry-run
```

---

## Docs

| Doc | What's in it |
|-----|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design, agent runtime, graph topology, storage schema |
| [Persona format](docs/PERSONA_FORMAT.md) | Full JSON schema with all fields |
| [Building personas](docs/BUILDING_PERSONAS.md) | Step-by-step guide with examples |
| [CLI reference](docs/CLI.md) | Every command and option |
| [API reference](docs/API.md) | All REST endpoints |
| [Safety](docs/SAFETY.md) | Anti-detection, rate limiting, FTC compliance |

---

## License

MIT
