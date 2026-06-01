# X Personas — Project Documentation

## Overview

X Personas is an AI agent system designed to run realistic, autonomous personas on X (Twitter). Built on LangGraph, the system orchestrates a clean, cycle-by-cycle workflow:

1. **Load Persona**: Parses a structured identity profile (`persona-struct.md`) containing traits, writing samples, topic preferences, and interaction boundaries.
2. **Scroll & Parse Feed**: Navigates the home timeline via Playwright and extracts all currently visible posts.
3. **Decide Engagement (LLM)**: An LLM evaluates the persona profile against visible posts, outputting structured actions (like, reply, quote, repost, or ignore) with specific scores and justifications.
4. **Hydrate Conversations**: If reply or quote actions are scheduled, Playwright fetches parent/sibling context in a background tab to ensure correct conversational flow.
5. **Generate Response Content**: A separate, focused LLM call writes reply or quote text matching the persona's vocabulary, emoji habits, and linguistic quirks (including writing style and slang samples).
6. **Execute Actions**: Playwright performs the actions on X. Actions for the same post are batched and executed within a single dedicated tab to optimize speed and security.
7. **Log Activity**: Every action is saved locally in a markdown-formatted activity log.
8. **Follow Decisions**: Periodically evaluates encountered accounts against follow guidelines.

---

## Project Structure

```
x-persona/
├── persona-struct.md             # Standard markdown template for defining personas
├── README.md                     # Project quickstart and CLI guide
├── DOC.md                        # Technical documentation
├── pyproject.toml                # Project configurations and dependencies
├── uv.lock                       # Lockfile mapping exact dependencies
├── src/
│   ├── generate_persona.py       # Helper to generate filled-out persona-struct.md from raw post logs
│   ├── models/                   # Pydantic data models
│   │   ├── __init__.py
│   │   ├── engagement.py         # EngagementDecisions, PostDecision schema
│   │   ├── feed.py               # FeedPost, PostMetrics, QuotedPost, FeedResponse schema
│   │   ├── log.py                # ActivityLogEntry schema
│   │   └── post.py               # Action results and status responses
│   ├── agent/                    # LangGraph workflow orchestration
│   │   ├── __init__.py
│   │   ├── runner.py             # Perpetual loop CLI runner with rate-limit and break management
│   │   ├── graph.py              # LangGraph StateGraph topology
│   │   ├── state.py              # LangGraph State model (TypedDict)
│   │   ├── config.py             # LLM client factory (OpenAI, Anthropic, DashScope)
│   │   ├── rate_limiter.py       # Actions-per-cycle, hourly, and daily limits
│   │   ├── history.py            # Deduplication & engagement logs parser
│   │   └── nodes/                # LangGraph Node implementations
│   │       ├── load_persona.py
│   │       ├── fetch_feed.py     # Captures viewport feed details
│   │       ├── llm_decide.py     # Decision-making node using structured LLM output
│   │       ├── hydrate_replies.py
│   │       ├── generate_content.py
│   │       ├── execute_actions.py
│   │       ├── log_activity.py
│   │       ├── follow_decision.py
│   │       ├── state_cleansing.py
│   │       └── scroll_page.py
│   └── utils/                    # Core browser automation functions
│       ├── __init__.py
│       ├── browser.py            # Playwright session and context isolation manager
│       ├── feed.py               # Home feed parsing and navigation helpers
│       ├── selectors.py          # Centralized DOM selector constants
│       ├── mouse.py              # Humanized cursor physics
│       ├── post.py               # Action executors (likes, reposts)
│       ├── reply.py              # Reply composition executor
│       └── quote.py              # Quote tweet composition executor
└── tests/                        # Automated unit and integration test suites
```

---

## Architecture & Workflow

The agent runs as a LangGraph `StateGraph` where each perpetual cycle handles scrolling, evaluation, composition, and execution sequentially.

### LangGraph Cycle Topology

```
             ┌────────────────┐
             │  load_persona  │
             └───────┬────────┘
                     ▼
             ┌────────────────┐
             │  scroll_feed   │  (Parse visible posts in viewport)
             └───────┬────────┘
                     ▼
             ┌────────────────┐
             │   llm_decide   │  (LLM decides actions via structured output)
             └───────┬────────┘
                     │
         ┌───────────┴───────────┐  (Conditional Route)
         ▼                       ▼
 ┌──────────────┐        ┌──────────────┐
 │ hydrate_repl │        │   execute    │ (Liking-only actions bypass
 │     _context │        │   _actions   │  composition)
 └───────┬──────┘        └───────┬──────┘
         ▼                       │
 ┌──────────────┐                │
 │   generate   │                │
 │   _content   │                │
 └───────┬──────┘                │
         ▼                       │
 ┌──────────────┐                │
 │   execute    │◄───────────────┘
 │   _actions   │
 └───────┬──────┘
         ▼
 ┌──────────────┐
 │ log_activity │  (Persist to <persona>-activity-log.md)
 └───────┬──────┘
         ▼
 ┌────────────────┐
 │follow_decision │  (Evaluate encountered profiles for follows)
 └───────┬────────┘
         ▼
 ┌────────────────┐
 │state_cleansing │  (Flush cycle state, preserve seen & engaged post IDs)
 └───────┬────────┘
         ▼
 ┌────────────────┐
 │  scroll_page   │  (Smooth human-like scrolling to fresh viewport)
 └────────────────┘
```

---

## Core Technical Systems

### 1. Structured LLM Decision Node (`llm_decide.py`)
Rather than relying on fragile manual parsing or brittle regex patterns, the decision node executes a structured function call utilizing the LLM provider's `.with_structured_output()` interface. 
* **Input**: Persona specifications (Identity, Topics, Stances, Thresholds) coupled with visible feed posts (Text, Author handle, Recency).
* **Target Schema**: `EngagementDecisions` which holds a list of `PostDecision` objects:
  - `action_type`: A list of actions (e.g. `["like", "reply"]` or `["like", "quote"]`).
  - `score`: The logical priority score (0.0 to 10.0).
  - `reason`: Structured textual explanation mapping back to the persona's stances.
  - `target_status_id`: Unique post ID.

### 2. Conversational Context Hydration (`hydrate_replies.py`)
To prevent flat or irrelevant responses, when a reply or quote is decided, the agent opens the targeted status details page in a parallel context. It parses the parent post and parent-replies to provide the generation node with rich conversational history.

### 3. Humanized Playwright Automation (`execute_actions.py`)
* **Tab-per-Post**: To prevent page corruption and minimize session footprint, each engagement opens a separate background tab, runs all decided actions for that specific post (e.g., likes, then writes reply), and safely closes the tab.
* **Natural Delays**: Randomized action delays (3–8s) and scroll delays (5–15s) avoid automated traffic detection.
* **Cursor Simulation & RIpples**: Heading runs overlay a visible cursor in the DOM displaying natural cubic-Bézier paths and click ripples to aid human visual debugging.

### 4. Robust Rate Limiting (`rate_limiter.py`)
Actions are strictly checked and persisted to a local state file `.rate-limits-<persona>.json` to ensure limits are respected even across sudden agent restarts:
* **Likes**: Max 5/cycle, 20/hour, 80/day
* **Replies**: Max 2/cycle, 8/hour, 30/day
* **Reposts**: Max 2/cycle, 8/hour, 30/day
* **Quotes**: Max 1/cycle, 4/hour, 15/day
* **Follows**: Max 3/hour, 15/day

---

## Verification & Safe Execution

### Operator Approval Gate (`--ask`)
By running with the `--ask` CLI flag, you enable the interactive approval gate. The workflow halts before executing any browser-level writes:
* Displays a detailed summary: targeted post, score, rationale, and proposed response.
* Prompts the operator to:
  - `Y`/`y`: Approve and execute the action block.
  - `N`/`n`: Terminate and skip the action block entirely.
  - `S`/`s`: Skip composition while executing safe read-actions like likes.

### Dry-Run Verification (`--dry-run`)
To verify LLM alignment without spinning up any automated browser sessions, you can run:
```bash
uv run python -m src.agent.runner --persona persona-struct.md --dry-run
```
This feeds a set of mock posts representing different topics (tech, random posts, personal milestones) to the decision prompt and showcases how the LLM structures its actions, scores, and explanations in the terminal.

---

## Setting Up and Running

### 1. Prerequisites
* Python 3.12+
* An authenticated X session state. Save your cookies and local storage state into `auth.json` at the root directory of the project.

### 2. Configuration Setup
Copy the environment template and insert your API keys:
```bash
cp .env.example .env
```
Fill in the appropriate API keys for your preferred LLM provider (DashScope/Qwen, OpenAI, or Anthropic/Claude).

### 3. Run Commands
```bash
# Verify parsing and LLM choices using dummy data
uv run python -m src.agent.runner --persona persona-struct.md --dry-run

# Run headed with manual approval gate (recommended for initial setup)
uv run python -m src.agent.runner --persona persona-struct.md --visible --ask

# Run completely headless and autonomous
uv run python -m src.agent.runner --persona persona-struct.md
```
