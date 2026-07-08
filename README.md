# xpersonas

Self hosted platform for running autonomous AI personas on social media.
Define persona. Agent will live that identity. Scrolling, Reading, Engaging, Posting like a real human.

**Not** a scheduling tool, analytics dashboard, or chatbot. It's an autonomous agent that behaves like a real person online.

---

## What it does

A persona runs on a loop:

1. **Scroll**: Browse the X/Twitter feed or search for specific topics
2. **Decide**: LLM reads posts and decides which ones are worth engaging with, based on the persona's interests and personality
3. **Generate**: LLM writes a reply or quote in the persona's voice, using writing samples you provide
4. **Act**: Like, reply, quote, repost, or follow via Playwright browser automation
5. **Log**: Record every action for auditing and analytics
6. **Repeat**: Loop forever with random delays, breaks, and anti-detection

The persona runs 24/7 in the background. You can have multiple personas running simultaneously, each with their own browser session, strategy, and personality.

---

## Core concepts

### Modes

Two modes change what the persona does. Default is `brand`: set `mode` in the persona JSON to change it:

| Mode | What it does | Example |
|------|-------------|---------|
| **brand** (default) | Represents a company. Can promote products naturally in conversations. | A dev tool brand persona mentions its product when someone complains about slow CI. |
| **personal** | Represents an individual. Builds relationships and network. | A researcher persona engages with papers and practitioners in their field. |

```json
{
  "mode": "personal",
  "identity": { ... }
}
```

### Strategies

The strategy controls how the persona engages. Set it in the persona config under `engagement.strategy`:

| Strategy | Behavior | Actions |
|----------|----------|---------|
| `active` | Engage with everything relevant. High volume. | like, reply, quote, repost, follow |
| `selective` | Only engage with high-quality, relevant content. | like, reply, quote, repost |
| `curation` | Curate and comment on content in your niche. Build authority. | quote, repost, original_post |
| `relationship_building` | Slow, genuine relationship building. Help before promoting. | like, reply, quote |
| `monitor_and_escalate` | Watch for mentions, escalate issues to Slack/Discord. | log, webhook |
| `competitive_intel` | Track competitor mentions and sentiment. | log, webhook |
| `support` | Answer customer questions on social media. | reply |

### Personas

A persona is a JSON file that defines everything about the agent's identity:

```json
{
  "mode": "brand",
  "identity": {
    "handle": "devtoolsfan",
    "display_name": "Dev Tools Fan",
    "bio": "I try every dev tool so you don't have to.",
    "occupation": "Developer Advocate"
  },
  "personality": {
    "core_traits": ["helpful", "technical", "opinionated"],
    "overall_vibe": "Experienced dev who's seen it all",
    "never": ["use marketing language", "be dismissive"]
  },
  "engagement": {
    "strategy": "active",
    "topics": [
      {"topic": "CI/CD", "stance": "love", "intensity": 8},
      {"topic": "slow builds", "stance": "dislike", "intensity": 7}
    ]
  }
}
```

See [docs/PERSONA_FORMAT.md](docs/PERSONA_FORMAT.md) for the full schema, and [docs/BUILDING_PERSONAS.md](docs/BUILDING_PERSONAS.md) for a step-by-step guide with examples.

---

## Quick start

### Prerequisites

- Python 3.12+
- An OpenAI API key (or compatible LLM provider)
- Chromium browser (installed via Playwright)

### 1. Install

```bash
git clone <repo-url> && cd x-personas
python -m venv .venv
source .venv/bin/activate
uv pip install -e .
playwright install chromium
```

### 2. Set up your LLM

xpersonas works with any **OpenAI-compatible API** (OpenAI, Ollama, LM Studio, vLLM, Together AI, Groq, etc.).

```bash
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="your-model"
```

Or create a `.env` file:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=your-model
```

### 3. Initialize the database

```bash
xpersonas init setup --db xpersonas.db --tenant-name "MyCompany"
```

This creates a SQLite database and your first tenant. Default mode is `brand`. To create a personal mode tenant:

```bash
xpersonas init setup --db xpersonas.db --tenant-name "My Personal Brand"
# Then set mode when creating personas
```

### 4. Create a persona

```bash
xpersonas persona create \
  --db xpersonas.db \
  --tenant-id <tenant_id> \
  --handle "devtoolsfan" \
  --display-name "Dev Tools Fan" \
  --strategy "active"
```

Or import from a JSON file (set `mode` in the JSON):
```bash
xpersonas persona import --db xpersonas.db --file my_persona.json
```

### 5. Run the agent

```bash
xpersonas agent start <persona_id> --db xpersonas.db
```

The agent will start scrolling, reading, and engaging with posts on X/Twitter using the persona's identity and strategy.

### 6. Check what's happening

```bash
# See running agents
xpersonas agent status --db xpersonas.db

# View activity log
curl http://localhost:8000/api/v1/activity/<persona_id>

# Check stats
curl http://localhost:8000/api/v1/activity/<persona_id>/stats
```

---

## Examples

### Brand mode: UGC product seeding

A SaaS company wants to seed mentions of their dev tool "FastBuild" across X/Twitter.

**Step 1**: Add the product to the knowledge base.

```bash
xpersonas product create \
  --db xpersonas.db \
  --tenant-id <tenant_id> \
  --name "FastBuild" \
  --description "CI/CD tool that's 10x faster" \
  --pain-points "slow builds,ci is slow,build times,waiting for builds" \
  --buy-url "https://fastbuild.dev"
```

**Step 2**: Create a brand persona with promo enabled.

```json
{
  "mode": "brand",
  "identity": {
    "handle": "devtoolsfan",
    "display_name": "Dev Tools Fan",
    "bio": "I try every dev tool so you don't have to."
  },
  "engagement": {
    "strategy": "active",
    "topics": [
      {"topic": "CI/CD", "stance": "love"},
      {"topic": "slow builds", "stance": "dislike"}
    ]
  },
  "promo": {
    "enabled": true,
    "product_ids": ["prod_xxx"],
    "search_queries": ["slow builds", "ci is slow", "build times"],
    "frequency_cap_per_week": 3
  }
}
```

**What happens**: The agent searches for posts about slow builds. When it finds someone complaining, it writes a helpful reply that naturally mentions FastBuild: like a friend recommending a tool, not an ad.

### Personal mode: Professional networking

A researcher wants to build their network in the distributed systems community.

```json
{
  "mode": "personal",
  "identity": {
    "handle": "distributed_sys_researcher",
    "display_name": "Alex Chen",
    "bio": "PhD student researching distributed consensus protocols"
  },
  "engagement": {
    "strategy": "relationship_building",
    "topics": [
      {"topic": "distributed systems", "stance": "love", "intensity": 9},
      {"topic": "consensus protocols", "stance": "love", "intensity": 8},
      {"topic": "CRDTs", "stance": "like", "intensity": 6}
    ]
  },
  "networking": {
    "target_connections": ["researchers in distributed systems", "systems engineers at cloud companies"],
    "engagement_style": "substantive, technically deep"
  }
}
```

**What happens**: The agent finds researchers posting about distributed systems, engages with their content thoughtfully (questions, related work, honest tradeoffs), and tracks relationships over time. When rapport is high enough, it signals that the contact is ready for a real DM.

---

## API server

Start the API server to manage everything via REST:

```bash
xpersonas serve --db xpersonas.db --port 8000
```

Then open http://localhost:8000/docs for the auto-generated Swagger UI.

### Key endpoints

```bash
# Tenants
POST   /api/v1/tenants                    Create tenant
GET    /api/v1/tenants                    List tenants

# Personas
POST   /api/v1/personas                   Create persona
GET    /api/v1/personas                   List personas

# Agents
POST   /api/v1/agents/start/{persona_id}  Start agent
POST   /api/v1/agents/stop/{persona_id}   Stop agent
GET    /api/v1/agents/status              List running agents

# Activity
GET    /api/v1/activity/{persona_id}      Get activity log
GET    /api/v1/activity/{persona_id}/stats Get statistics

# Products (brand mode)
POST   /api/v1/products                   Create product
GET    /api/v1/products                   List products

# Contacts (personal mode)
GET    /api/v1/contacts/{persona_id}      List contacts
GET    /api/v1/contacts/{persona_id}/ready Connection-ready contacts
```

### Authentication

Generate an API key for a tenant:

```bash
curl -X POST http://localhost:8000/api/v1/tenants/<tenant_id>/api-keys
```

Then include it in requests:

```bash
curl -H "X-API-Key: sk-..." http://localhost:8000/api/v1/personas
```

---

## CLI reference

```bash
xpersonas init setup --db <path> --tenant-name <name>
xpersonas tenant create <name> --db <path>
xpersonas tenant list --db <path>

xpersonas persona create --db <path> --tenant-id <id> --handle <handle>
xpersonas persona list --db <path>
xpersonas persona import --db <path> --file <persona.json>
xpersonas persona export --db <path> --persona-id <id> --output <file.json>

xpersonas agent start <persona_id> --db <path>
xpersonas agent stop <persona_id> --db <path>
xpersonas agent status --db <path>
xpersonas agent once <persona_id> --dry-run --db <path>

xpersonas product create --db <path> --tenant-id <id> --name <name>
xpersonas product list --db <path>

xpersonas contact list <persona_id> --db <path>
xpersonas contact ready <persona_id> --db <path>

xpersonas serve --db <path> --port 8000
```

---

## Configuration

### LLM setup

xpersonas uses any **OpenAI-compatible API**: OpenAI, Ollama, LM Studio, vLLM, Together AI, Groq, etc. No provider-specific integrations, just the standard API format.

```bash
# Required
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="your-model"

# Optional: custom endpoint (for local LLMs or other providers)
export OPENAI_BASE_URL="http://localhost:11434/v1"
```

Or create a `.env` file:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=your-model
```

### Config hierarchy

Configuration resolves in this order (later overrides earlier):

1. Environment variables
2. `.env` file
3. Tenant config (stored in DB)
4. Persona config (stored in DB)

---

## How it works

### The agent loop

```
┌─────────────────────────────────────────────────────┐
│                    Agent Loop                        │
│                                                     │
│  load_persona → fetch_content → llm_decide ─┐       │
│                                              │       │
│         ┌───────────────────────────────────┘       │
│         │                                           │
│         ▼                                           │
│  ┌─ has text? ──► hydrate_context → generate_content│
│  │                      │                           │
│  │                      ▼                           │
│  │                execute_actions                   │
│  │                      │                           │
│  └─ no text? ──────────┘                           │
│                      │                              │
│                      ▼                              │
│              log_activity → state_cleansing          │
│                                    │                │
│                                    ▼                │
│                              scroll_page → END      │
│                                    │                │
│                                    ▼                │
│                              (next cycle)           │
└─────────────────────────────────────────────────────┘
```

### Anti-detection

The browser automation includes human-like behavior to avoid platform detection:

- **Bezier mouse movement**: cursor follows a curved path, not straight lines
- **Character-by-character typing**: replies are typed with random delays between keystrokes
- **Random delays**: 3-8 seconds between actions, 2-5 seconds between cycles
- **Break logic**: after scrolling ~2500 posts, takes a 10-30 minute break
- **Smooth scrolling**: scrolls with `behavior: smooth`, not instant jumps

### Rate limiting

Three layers of rate limiting:

1. **Per-cycle caps**: max actions per agent cycle (e.g., 5 likes, 2 replies)
2. **Hourly caps**: max actions per hour (e.g., 20 likes, 8 replies)
3. **Daily caps**: max actions per day (e.g., 80 likes, 30 replies)

All limits are configurable per persona in the `engagement.rate_limits` section.

---

## Safety

### Brand mode safeguards

- **Frequency caps**: max product mentions per week per product
- **Account aging**: minimum non-promotional posts before any product mentions
- **Disclosure**: prompt includes FTC disclosure requirements (#ad, #sponsored)
- **Anti-superlative filter**: blocks "best ever", "game changer", etc.
- **Ratio enforcement**: product mentions stay under 10% of total activity

### Audit trail

Every action is logged to `activity_log` with:
- What action was taken (like, reply, quote, repost)
- What post it targeted
- The LLM's reasoning
- Relevance score (0-10)
- Success/failure status

---

## License

[Your license here]
