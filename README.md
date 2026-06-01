# X Personas

Autonomous X/Twitter agent that loads a structured persona, scrolls the home feed, decides engagements using an LLM, generates in-character responses, and executes actions via Playwright.

## Quick Start

### 1. Setup
```bash
git clone <repo> && cd x-persona
uv sync
cp .env.example .env # Add your LLM keys (DASHSCOPE_API_KEY, etc.)
```

### 2. Authenticate
```bash
# Log in manually once to save auth.json session
uv run python -m src.agent.runner --persona <your-persona>.md --visible --once
```

### 3. Generate Persona
```bash
uv run python -m src.generate_persona <raw-samples>.md
```

### 4. Run Agent
```bash
# Dry run (test LLM decisions, no browser)
uv run python -m src.agent.runner --persona <persona>-struct.md --dry-run

# Continuous Loop (Default)
uv run python -m src.agent.runner --persona <persona>-struct.md --provider dashscope

# With Manual Action Approval
uv run python -m src.agent.runner --persona <persona>-struct.md --provider dashscope --visible --ask
```

## CLI Reference

| Flag | Default | Description |
|---|---|---|
| `--persona` | required | Path to persona-struct.md |
| `--provider` | `openai` | `openai`, `anthropic`, or `dashscope` |
| `--visible` | off | Run headed (shows browser window) |
| `--dry-run` | off | Test LLM decisions without starting browser |
| `--once` | off | Run a single cycle and exit |
| `--ask` | off | Confirm actions `[Y/n/s]` in terminal before executing |
| `--quiet` | off | Suppress debug logging |

## Features & Pacing
* **Safe Delays:** 3–8s between actions, 5–15s between scrolls, 10–30 min break after `--scroll-limit` (default 2500 viewports).
* **Auto-Sync:** Updates profile stats in `<persona>-struct.md` at startup.
* **Strict Limits:** Enforces hourly and daily rate limits for likes, replies, quotes, reposts, and follows.
* **Tab isolation:** Opens a single tab per post to perform all actions, then closes it.
