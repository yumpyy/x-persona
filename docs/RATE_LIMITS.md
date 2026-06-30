# Rate Limiting

Rate limits are enforced at three levels. `x_personas/agent/rate_limiter.py`.

## Per-Cycle Caps (hard reset each cycle)

| Action | Cap |
|---|---|
| like | 5 |
| reply | 2 |
| repost | 2 |
| quote | 1 |

## Hourly Caps (rolling 3600s window)

| Action | Cap |
|---|---|
| like | 20 |
| reply | 8 |
| repost | 8 |
| quote | 4 |
| follow | 3 |

## Daily Caps (rolling 86400s window)

| Action | Cap |
|---|---|
| like | 80 |
| reply | 30 |
| repost | 30 |
| quote | 15 |
| follow | 15 |

## Delays

| Delay | Range |
|---|---|
| Between actions | 3-8s random uniform |
| Between scrolls | 5-15s random uniform |
| Reading dwell before acting | 2.5-6s random uniform |

## Implementation

**`RateLimitState`** class persists to `.rate-limits-<persona>.json`:

```json
{
  "entries": [
    {"action": "like", "timestamp": "2026-06-30T12:00:00+00:00"},
    ...
  ]
}
```

- `record(action, timestamp)` — Add entry
- `can_act(action)` → `(bool, reason_or_None)` — Checks hourly + daily caps
- `hourly_count(action)` — Count in last 3600s
- `daily_count(action)` — Count in last 86400s

Rate limits are checked:
1. **In `llm_decide.py`** — `_decisions_to_pending()` checks hourly/daily caps before converting PostDecision → PendingAction
2. **In `log_activity.py`** — Successful actions recorded to RateLimitState

Critique variety policy is separate but enforced in the same node:
- Max 1 critical engagement per cycle
- If recent 10 engagements contain critique → all critical decisions blocked
- Considered critical: disliked topics (section 8 stance), or keyword match in reason/content
