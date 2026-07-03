# File Artifacts

## Persona Files

### `personas/<name>/persona.md`

The core persona definition. 14 sections parsed by `load_persona.py`.

**Template** at `personas/_template/persona.md` (blank, git-tracked). Also at `persona-struct.md` (root) for legacy access.

**Git status:** ignored (`.gitignore` excludes `personas/*/` but keeps `personas/_template/`).

### Writing Sample Files (`personas/<name>/source/`)

Referenced in section 13 of the persona file. Resolved relative to the persona directory. Raw source data used for content generation voice matching. Up to 2000 chars per file loaded.

---

## Activity Log

### `personas/<name>/activity-log.md`

Markdown table recording all engagements and original posts. The **dedup source** — loaded at cycle start by `history.load_engaged_status_ids()`.

```
| timestamp | action | target | content | score | context |
|---|---|---|---|---|---|
| 2026-06-30T12:00:00Z | like | @user / 123456 | | 7.5 | Interesting technical take [✓] |
| 2026-06-30T12:00:30Z | reply | @user2 / 123457 | nice take! | 8.0 | Worth engaging [✓] |
| 2026-06-30T12:01:00Z | original_post | self | Just shipped a thing | 10.0 | Standalone original tweet published [Afternoon/Evening]. |
```

**Functions in `history.py`:**
- `load_engaged_status_ids(log_file)` → `set[str]` — All status IDs ever engaged
- `load_recent_engagements(log_file, limit=15)` → `list[dict]` — Recent successful engagements for prompt context
- `load_recent_original_posts(log_file, limit=5)` → `list[str]` — Recent original post texts
- `load_engagements_since_last_post(log_file)` → `int` — Count since last original post (for scheduler triggering)

**Git status:** ignored.

---

## Auth State

### `personas/<name>/auth.json`

Playwright storage state — cookies + localStorage for authenticated X sessions.

Resolution order in `runner.py`:
1. If `--auth` flag provided → use that path
2. If `personas/<name>/auth.json` exists → use it
3. If root `auth.json` exists → use it (shared)
4. Fallback → `personas/<name>/auth.json` (new, will be created after login)

**Git status:** ignored.

---

## Rate Limits

### `personas/<name>/rate-limits.json`

Persisted `RateLimitState` entries — all recorded actions with timestamps.

```json
{
  "entries": [
    {"action": "like", "timestamp": "2026-06-30T12:00:00+00:00"},
    {"action": "reply", "timestamp": "2026-06-30T12:00:30+00:00"}
  ]
}
```

**Git status:** ignored.

---

## TUI Settings

### `~/.config/x-personas/settings.json`

Persistent TUI settings (model, intervals, quiet mode). Created on first run, synced by `TUIStore`.

```json
{
  "model": "deepseek-chat",
  "max_daily_engagements": 40,
  "quiet": false,
  "scroll_limit": 2500
}
```

**Git status:** not in repo (user config directory).

---

## Environment

### `.env`

API keys and model overrides. See `.env.example` for template.

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# VLM (optional)
VLM_MODEL=gpt-4o
VLM_API_KEY=
VLM_BASE_URL=
```

**Git status:** ignored.
