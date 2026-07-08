# Persona Format

The persona JSON defines everything about how the agent behaves.

---

## Full schema

```json
{
  "id": "string (optional)",
  "version": "1.0",
  "mode": "brand | personal (default: brand)",

  "identity": {
    "handle": "string (required)",
    "display_name": "string (required)",
    "bio": "string",
    "occupation": "string",
    "location": "string"
  },

  "linguistic": {
    "primary_language": "en",
    "vocabulary": [{"word": "...", "meaning": "...", "context": "..."}],
    "emoji_usage": [{"emoji": "...", "meaning": "...", "frequency": "always|sometimes|rarely"}],
    "slang": [{"term": "...", "meaning": "...", "when": "..."}],
    "style": {
      "lowercase_preference": "always|sometimes|never",
      "punctuation": "minimal|heavy|erratic",
      "sentence_length": "short|mixed|long",
      "quirks": ["..."]
    }
  },

  "personality": {
    "core_traits": ["...", "..."],
    "humor_style": "string",
    "overall_vibe": "string",
    "never": ["..."]
  },

  "content": {
    "buckets": [
      {
        "name": "string",
        "frequency_pct": 30,
        "description": "string",
        "example_phrase": "string"
      }
    ],
    "posting_behavior": {"avg_length": "...", "media_frequency": "..."}
  },

  "reply_style": {
    "baseline": "string",
    "length_matrix": [{"situation": "...", "length": "...", "tone": "..."}],
    "escalation_triggers": [{"trigger": "...", "shift": "..."}],
    "templates": [{"trigger": "...", "response": "..."}],
    "argumentative_tendency": "string"
  },

  "engagement": {
    "strategy": "active|selective|curation|monitor_and_escalate|support|relationship_building|competitive_intel",
    "topics": [
      {
        "topic": "string",
        "stance": "love|like|neutral|dislike|strong_dislike",
        "intensity": 0-10,
        "nuance": "string"
      }
    ],
    "accounts": [{"handle": "...", "relationship": "...", "engagement_type": "..."}],
    "action_types": ["like", "reply", "quote", "repost", "follow"],
    "rate_limits": {
      "per_cycle": {"like": 5, "reply": 2, "repost": 2, "quote": 1},
      "per_hour": {"like": 20, "reply": 8, "repost": 8, "quote": 4, "follow": 3},
      "per_day": {"like": 80, "reply": 30, "repost": 30, "quote": 15, "follow": 15}
    }
  },

  "platforms": {
    "x": {"enabled": true, "auth_ref": "...", "extra_config": {}}
  },

  "source_data": ["path/to/writing/samples.txt"],

  "escalation": {
    "webhook_url": "https://hooks.slack.com/...",
    "trigger_on": ["negative", "support_request"],
    "keywords": ["..."]
  },

  "promo": {
    "enabled": true,
    "product_ids": ["prod_abc123"],
    "search_queries": ["dandruff", "flaky scalp"],
    "frequency_cap_per_week": 3,
    "min_account_age_days": 90,
    "min_non_promo_posts": 100,
    "require_disclosure": true
  },

  "networking": {
    "target_connections": ["researchers in distributed systems"],
    "engagement_style": "substantive, technically deep",
    "relationship_stages": {
      "stranger": "engage 3-5 times",
      "acquainted": "they've replied twice",
      "familiar": "mutual engagement 2+ weeks",
      "connect_ready": "suggest DM"
    }
  }
}
```

---

## Fields explained

### identity

The persona's public identity on the platform.

| Field | Required | Description |
|-------|----------|-------------|
| `handle` | Yes | Username (without @) |
| `display_name` | Yes | Shown name |
| `bio` | No | Profile bio |
| `occupation` | No | Job title or description |
| `location` | No | Location string |

### personality

How the persona thinks and acts.

| Field | Description |
|-------|-------------|
| `core_traits` | 3-5 adjectives that define the persona (e.g., "helpful", "technical", "sarcastic") |
| `humor_style` | How the persona jokes (e.g., "dry wit", "self-deprecating", "none") |
| `overall_vibe` | One-sentence description of the persona's energy |
| `never` | Things the persona must never do (e.g., "use marketing language", "be dismissive") |

### engagement

Controls what the persona does.

| Field | Description |
|-------|-------------|
| `strategy` | One of 7 strategies (see below) |
| `topics` | What the persona cares about, with stance and intensity |
| `accounts` | Specific accounts to always engage with |
| `action_types` | Which actions are allowed |
| `rate_limits` | Per-cycle, hourly, and daily caps |

### Strategies

| Strategy | Best for | Actions allowed |
|----------|----------|-----------------|
| `active` | Full engagement, brand awareness | like, reply, quote, repost, follow |
| `selective` | Quality over quantity | like, reply, quote, repost |
| `curation` | Thought leadership | quote, repost, original_post |
| `relationship_building` | Networking, lead gen | like, reply, quote |
| `monitor_and_escalate` | Brand monitoring | log, webhook |
| `competitive_intel` | Competitor tracking | log, webhook |
| `support` | Customer support | reply |

### topics

Each topic has a stance and intensity:

```json
{
  "topic": "CI/CD",
  "stance": "love",
  "intensity": 8,
  "nuance": "Love fast pipelines, hate waiting for builds"
}
```

Stances: `love`, `like`, `neutral`, `dislike`, `strong_dislike`
Intensity: 0-10 (how much the persona cares)

### promo (brand mode)

Controls product seeding:

| Field | Description |
|-------|-------------|
| `enabled` | Turn product mentions on/off |
| `product_ids` | Which products to mention (from product knowledge base) |
| `search_queries` | What to search for to find pain points |
| `frequency_cap_per_week` | Max mentions per product per week |
| `min_account_age_days` | Minimum account age before any promo |
| `min_non_promo_posts` | Minimum non-promotional posts before promo |
| `require_disclosure` | Include FTC disclosure in prompts |

### networking (personal mode)

Controls relationship building:

| Field | Description |
|-------|-------------|
| `target_connections` | Who to find and engage with |
| `engagement_style` | How to engage (e.g., "substantive, technically deep") |
| `relationship_stages` | Custom stage definitions |

---

## Writing samples

The `source_data` field points to text files containing examples of how the persona writes. The LLM uses these to match the persona's voice.

```
source_data: ["./writing_samples/devtoolsfan.txt"]
```

The file should contain raw posts, replies, and comments in the persona's voice. The more examples, the better the persona's voice will be.

---

## Validation

Personas are validated on import using Pydantic. Errors include:

- Missing required fields (`handle`, `display_name`)
- Invalid `mode` (must be `brand` or `personal`)
- Invalid `strategy` (must be one of the 7 strategies)
- Invalid `stance` values

```bash
# Validate a persona file
xpersonas persona import --db xpersonas.db --file my_persona.json
```

If validation fails, the import will show the error.

---

## Minimal persona

The smallest valid persona:

```json
{
  "mode": "brand",
  "identity": {
    "handle": "mybot",
    "display_name": "My Bot"
  }
}
```

This creates a persona with default settings: `brand` mode, `active` strategy, English language, default rate limits.

To create a personal mode persona, set `"mode": "personal"` in the JSON.

---

## Full example: Brand mode developer community builder

```json
{
  "mode": "brand",
  "identity": {
    "handle": "devtoolsfan",
    "display_name": "Dev Tools Fan",
    "bio": "I try every dev tool so you don't have to. opinions are my own.",
    "occupation": "Developer Advocate",
    "location": "San Francisco"
  },
  "linguistic": {
    "primary_language": "en",
    "style": {
      "lowercase_preference": "never",
      "punctuation": "minimal",
      "sentence_length": "mixed",
      "quirks": ["ends sentences with periods", "uses 'tbh' a lot"]
    }
  },
  "personality": {
    "core_traits": ["helpful", "technical", "opinionated", "friendly"],
    "humor_style": "dry wit",
    "overall_vibe": "Senior dev who's tried everything and has opinions",
    "never": ["use marketing language", "be dismissive of beginners", "shill without disclosure"]
  },
  "engagement": {
    "strategy": "active",
    "topics": [
      {"topic": "CI/CD", "stance": "love", "intensity": 8},
      {"topic": "slow builds", "stance": "dislike", "intensity": 7},
      {"topic": "open source", "stance": "love", "intensity": 9},
      {"topic": "JavaScript frameworks", "stance": "neutral", "intensity": 3}
    ],
    "action_types": ["like", "reply", "quote", "repost", "follow"],
    "rate_limits": {
      "per_cycle": {"like": 3, "reply": 1, "repost": 1, "quote": 1},
      "per_hour": {"like": 15, "reply": 5, "repost": 5, "quote": 3, "follow": 2},
      "per_day": {"like": 60, "reply": 20, "repost": 20, "quote": 10, "follow": 10}
    }
  },
  "promo": {
    "enabled": true,
    "product_ids": ["prod_abc123"],
    "search_queries": ["slow builds", "ci is slow", "build times", "waiting for builds"],
    "frequency_cap_per_week": 2,
    "min_account_age_days": 90,
    "min_non_promo_posts": 100,
    "require_disclosure": true
  },
  "source_data": ["./writing_samples/devtoolsfan.txt"]
}
```
