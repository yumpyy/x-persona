# X Personas

Autonomous social media agent that mimics real personas on X/Twitter.
Scrolls feed one viewport at a time, scores posts, opens each interaction
in a new browser tab, and loops perpetually with randomized human-like delays.

## How to run

### 1. Install

```bash
git clone <repo> && cd x-personas
uv sync
```

### 2. Set up environment

Copy `.env.example` to `.env` with your LLM provider key:

```bash
cp .env.example .env
# Then edit .env with your API keys
```

Supported providers:

| Provider | Key env var | Model env var | Base URL env var |
|---|---|---|---|
| DashScope | `DASHSCOPE_API_KEY` | `DASHSCOPE_MODEL` | `DASHSCOPE_BASE_URL` |
| OpenAI | `OPENAI_API_KEY` | `OPENAI_MODEL` | — |
| Anthropic | `ANTHROPIC_API_KEY` | `ANTHROPIC_MODEL` | — |

### 3. Authenticate with X

Run the agent once **with `--visible`** so you can log into X manually.
This creates `auth.json` (Playwright saved session) for future headless runs:

```bash
uv run python -m src.agent.runner --persona <your-persona>.md --once
```

A browser window opens → log into X → close the window. Auth is saved.

### 4. Generate a persona

Scraped posts/replies → LLM analyzes tone, topics, slang, reply style → structured persona file:

```bash
# Preview what would be generated
uv run python -m src.generate_persona <handle>.md --dry-run

# Generate the persona-struct.md
uv run python -m src.generate_persona <handle>.md
```

Input: markdown file with raw scraped posts/replies (see `purusha-persona.md`)
Output: `<handle>-persona-struct.md`

### 5. Dry run (verify persona)

Parses the persona, scores sample posts, shows decisions — no browser or LLM needed:

```bash
uv run python -m src.agent.runner --persona <handle>-persona-struct.md --dry-run
```

### 6. Run the agent

#### Single cycle (one scroll, act, exit)

```bash
uv run python -m src.agent.runner --persona <handle>-persona-struct.md --provider dashscope --once
```

#### Perpetual (default)

Scrolls 1500 times (~1–3 hours of activity), takes a 10–30 minute break, re-navigates to x.com/home, repeats:

```bash
uv run python -m src.agent.runner --persona <handle>-persona-struct.md --provider dashscope
```

#### Infinite scrolling (no break)

```bash
uv run python -m src.agent.runner --persona <handle>-persona-struct.md --provider dashscope --scroll-limit -1
```

## CLI flags

| Flag | Default | Description |
|---|---|---|
| `--persona` | required | Path to persona-struct.md |
| `--provider` | `openai` | `openai`, `anthropic`, or `dashscope` |
| `--model` | provider default | Model name |
| `--api-key` | env var | API key override |
| `--base-url` | env var | Base URL override |
| `--visible` | off | Show browser window (default: headless) |
| `--quiet` | off | Suppress debug logs |
| `--dry-run` | off | Parse + score only, no browser/LLM |
| `--once` | off | Single cycle then exit |
| `--scroll-limit` | 1500 | Scrolls before break (`-1` = infinite) |
| `--browser` | auto | Path to Chromium binary (e.g. `/usr/bin/chromium`) |

After `--scroll-limit` scrolls (default 1500) the agent pauses 10–30 minutes,
re-navigates to x.com/home, and continues.

## Human-like pacing

| Phase | Delay |
|---|---|
| Between scrolls (after decisions) | 5–15s |
| Between actions (same tab) | 3–8s |
| After scroll limit | 10–30 min break |

## Rate limits

| Action | Per cycle | Per hour | Per day |
|---|---|---|---|
| likes | 5 | 20 | 80 |
| replies | 2 | 8 | 30 |
| reposts | 2 | 8 | 30 |
| quotes | 1 | 4 | 15 |
| follows | — | 3 | 15 |

One action per unique handle per cycle. Limits persist across restarts via
`.rate-limits-<persona>.json`.

## Architecture

See [arch.md](arch.md) for the full system design.
