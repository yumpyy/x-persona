# X Personas — Project Documentation

## Overview

X Personas is an AI agent system that creates and runs realistic social media personas on X (Twitter). It uses LangGraph to orchestrate a workflow where an agent:

1. Loads a structured persona definition (who they are, how they talk, what they care about)
2. Scrapes the X home feed to see what's happening
3. Scores each post using a deterministic decision engine based on the persona's preferences
4. Decides engagement actions — like, reply, quote tweet, or repost
5. Generates reply/quote text using an LLM that matches the persona's linguistic profile exactly
6. Executes actions via Playwright browser automation
7. Logs all activity to a per-persona activity log

The goal is to make bots that don't look or feel like bots — they post with authentic voice, engage meaningfully, and build real-feeling presence over time.

---

## Project Structure

```
x-personas/
├── personam-struct.md            # Standard template for defining personas
├── agent_pln.md                  # LangGraph agent architecture plan
├── playwright-function.md        # Spec for Playwright automation functions
├── profiles.md                   # X profile URLs being studied as references
├── ref-persona.md                # A filled-out example persona (vaibhav)
├── cneural-net-persona.md        # Sample persona source data — raw posts & replies
├── purusha-persona.md            # Sample persona source data — raw posts & replies
├── learning-map.md               # Learning resources
├── main.py                       # CLI entry point
├── pyproject.toml                # Python project config (pydantic, playwright)
├── src/
│   ├── __init__.py
│   ├── models/                   # Pydantic data models
│   │   ├── __init__.py
│   │   ├── feed.py               # FeedPost, PostMetrics, QuotedPost, FeedResponse
│   │   └── post.py              # Reply (recursive), PostData, ActionResult, PostResponse
│   └── utils/                   # Playwright browser automation
│       ├── __init__.py
│       ├── browser.py            # BrowserSession — shared browser lifecycle
│       ├── feed.py              # get_home_feed()
│       └── post.py              # get_post_data(), post(), like(), repost()
```

---

## Key Concepts

### Persona Definition (`persona-struct.md`)

A persona is defined across 14 sections in a markdown template:

| Section | What it captures |
|---|---|
| 1. Identity & Metadata | Handle, display name, bio, occupation, follower counts |
| 2. Linguistic Profile | Languages, code-mixing, slang, emoji habits, grammar quirks |
| 3. Personality & Vibe | Core traits, humor style, hard "never" rules |
| 4. Content Buckets | Types of content they post, with frequency and examples |
| 5. Posting Behavior | Post length, media habits, thread frequency, repost behavior |
| 6. Reply Behavior | Context-dependent reply length matrix, escalation triggers |
| 7. Engagement Triggers | Topics, accounts, and formats that make them stop scrolling |
| 8. Topic Stances | Specific opinions on subjects, with intensity |
| 9. Decision Engine | Scoring formula, thresholds, engagement type matrix, follow logic |
| 10. Reference Accounts | Accounts they admire or borrow from |
| 11. Current Context | What they're building, learning, experiencing |
| 12. Tone Rules | Constraints for all generated content |
| 13. Source Data & History | Raw post/reply data files referenced by the LLM |
| 14. Activity Log | Per-persona activity log schema |

### Persona Source Data

Files like `cneural-net-persona.md` and `purusha-persona.md` contain raw posts and replies scraped from real X profiles. They are organized with `<posts>` and `<replies>` tags. These serve as reference material for the LLM to understand the persona's authentic language, interaction patterns, and relationship dynamics.

### Decision Engine

The core of the engagement logic. Each home feed post is scored using:

```
score = (topic_affinity × 0.4) + (account_relationship × 0.3) + (format_affinity × 0.2) + (recency_bonus × 0.1)
```

Scoring is deterministic — implemented in Python code. No LLM calls for scoring.

| Score | Action |
|---|---|
| 8-10 | Quote tweet + like |
| 6-7.9 | Reply + like |
| 4-5.9 | Like only |
| 2-3.9 | Scroll past, maybe read |
| 0-1.9 | Ignore |

---

## Architecture

### Agent Workflow (LangGraph)

```
persona-struct.md → [load_persona] → [fetch_feed] → [score_posts]
                                                         ↓
                                                  [decide_engagement]
                                                         │
                                          ┌──────────────┼──────────────┐
                                          ↓              ↓              ↓
                                   [generate      [execute       (skip to
                                   _content] →   _actions]     log_activity]
                                          ↓              ↓
                                          └──────────────┘
                                                         ↓
                                                  [log_activity]
                                                         ↓
                                                  [follow_decision]
                                                         ↓
                                                        END
```

### Nodes

| Node | Description |
|---|---|
| `load_persona` | Reads and parses the persona markdown into structured data |
| `fetch_feed` | Scrapes x.com/home via Playwright for current posts |
| `score_posts` | Applies scoring formula to each post deterministically |
| `decide_engagement` | Applies thresholds + engagement type matrix, queues actions |
| `generate_content` | LLM generates reply/quote text matching persona's voice |
| `execute_actions` | Playwright executes queued actions (like, repost, quote, reply) |
| `log_activity` | Appends actions to `<persona>-activity-log.md` |
| `follow_decision` | Scores accounts and optionally follows new ones |

### Models (Pydantic)

| File | Models |
|---|---|
| `feed.py` | PostMetrics, QuotedPost, FeedPost, FeedResponse |
| `post.py` | Reply (recursive), PostData, ActionResult, PostResponse |
| `scored.py` *(planned)* | ScoreBreakdown, ScoredPost |
| `engagement.py` *(planned)* | ActionType, PendingAction, ExecutedAction |
| `log.py` *(planned)* | ActivityLogEntry, ActivityLog |

### Utils (Playwright)

| File | Functions |
|---|---|
| `browser.py` | BrowserSession — start/stop/save_auth, context manager |
| `feed.py` | get_home_feed() — scrape home feed |
| `post.py` | get_post_data(), post(), like(), repost() |

---

## How It Works Step by Step

1. **Define a persona** — Fill out persona-struct.md for the target profile. Reference raw post/reply data in section 13.

2. **Run the agent** — Point the runner at the persona file:
   ```
   python -m src.agent.runner --persona cneural-net-persona.md --headless
   ```

3. **Agent loads persona** — Parses the markdown into structured sections. The linguistic profile, engagement triggers, topic stances, and scoring weights become the agent's "identity."

4. **Agent fetches feed** — Uses Playwright to log into X and scrape the home feed. Each post becomes a FeedPost model.

5. **Agent scores posts** — The scoring engine computes a score for each post using the formula from the persona struct. Topic keywords, account relationship lookup, post format detection, and recency all contribute.

6. **Agent decides engagement** — Posts above thresholds get queued as actions. The engagement type matrix (section 9g) determines whether to reply, quote, like, or repost based on context.

7. **LLM generates content** — For reply/quote actions, an LLM call generates text that matches the persona's linguistic profile exactly — code-mixing ratio, slang, emoji patterns, sentence length, all from the persona definition.

8. **Agent executes actions** — Playwright clicks the like/repost/reply/quote buttons on X.

9. **Agent logs everything** — Every action is recorded in `<persona>-activity-log.md` with timestamp, action type, target, content, score, and reason.

10. **Agent considers follows** — New accounts in the feed are scored using the follow criteria. High-scoring accounts get followed (respecting rate limits).

---

## Profiles Being Studied

From `profiles.md`:

| Handle | Handle |
|---|---|
| @cneuralnetwork | cneural-net-persona.md |
| @maharshii | — |
| @purusa0x6c | purusha-persona.md |
| @sharpeye_wnl | — |

---

## Running the Agent

### Prerequisites

- Python 3.12+
- Playwright installed (`playwright install chromium`)
- A logged-in X account (auth state saved to `auth.json`)

### Commands

```bash
# One cycle
python -m src.agent.runner --persona cneural-net-persona.md

# Continuous loop (check feed every 30 minutes)
python -m src.agent.runner --persona cneural-net-persona.md --loop --interval 1800

# With a different LLM provider
python -m src.agent.runner --persona ref-persona.md --provider anthropic --model claude-sonnet-4-20250514

# Visible browser (for debugging)
python -m src.agent.runner --persona ref-persona.md --no-headless
```

---

## Dependencies

- `pydantic>=2.13.4` — Data models with strict validation
- `playwright>=1.60.0` — Browser automation for X
- `langgraph` — Agent orchestration
- `langchain-openai` or `langchain-anthropic` — LLM integration

---

## Related Files

| File | Purpose |
|---|---|
| `persona-struct.md` | Standard persona template |
| `playwright-function.md` | Playwright function specification |
| `agent_pln.md` | Agent architecture plan |
| `profiles.md` | Real X profiles being studied |
| `ref-persona.md` | Filled-out example persona |
| `cneural-net-persona.md` | Sample source data |
| `purusha-persona.md` | Sample source data |
| `todo.md` | Project task tracking |
