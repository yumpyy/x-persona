# Prompt Templates

Two markdown prompt templates live in `x_personas/prompts/`.

---

## `llm_decide_system.md` — System Prompt

**Purpose:** Tells the LLM to roleplay as the persona and decide which posts to engage with.

**Placeholders:**
- `{persona_sections}` — Compiled persona profile (all 14 sections rendered as markdown)
- `{recent_engagements}` — Last 10 successful engagements from activity log

**Key instructions embedded in the template:**
1. Decide LIKE / REPLY / QUOTE per post
2. **Verified account priority** — "The X algorithm places replies from premium accounts at the very top"
3. **Value-driven dwell time** — Prefer posts allowing insightful/technical commentary
4. **Avoid bot-like spans** — Only engage when aligned with interests
5. **Stance & critique policy** — "dislike" stance engagements must be sparing
6. **Variety policy** (critical) — Max 3 of same topic in last 10 engagements; if any critique in last 10, skip all critical posts; max 1 critical decision per cycle; rotate through builder interests
7. Only return posts to engage with — omit ignored posts entirely
8. `action_type` is list (multiple actions per post possible)
9. Content generated separately — only decide WHICH posts
10. Max one decision per unique handle per cycle

---

## `llm_decide_user.md` — User Prompt

**Purpose:** Provides the visible feed posts.

**Placeholder:**
- `{feed_posts}` — Rendered via `_build_feed_text()` with post index, author, text, metrics, status ID, flags

---

## Prompt Assembly (`llm_decide.py`)

```
system = llm_decide_system.md
  .replace("{persona_sections}", _build_persona_text(sections))
  .replace("{recent_engagements}", _build_recent_engagements_text(entries))

user = llm_decide_user.md
  .replace("{feed_posts}", _build_feed_text(posts))
```

Media: Up to 4 image URLs from feed posts appended as `image_url` blocks in user content.

---

## Content Generation Prompting

Content generation (`generate_content.py`) doesn't use template files — prompts are assembled in code:

**System prompt per generation:**
```
"You are an AI that writes social media content matching a specific persona..."
+ _build_persona_text(sections)  # Full persona profile
```

**User prompt per reply/quote:**
1. Action label and target handle
2. Reason for engaging
3. Existing replies (up to 15) for deduplication check
4. CRITICAL DEDUPLICATION CHECK instruction → return `[SKIP]` if saturated
5. Writing samples from source data files (up to 3 files, 600 chars)
6. Recent 15 engagements for repetition avoidance
7. Diversity & spontaneity rule (don't copy-paste templates literally)
8. Technical accuracy & contextual relevance rule
9. Persona voice rule (vocabulary, casing, punctuation, emoji, slang)
10. Up to 2 media URLs from thread context (multimodal)

**Original post generation** adds:
- Time of day context
- Recent original posts (up to 5) for diversity/continuity
- Content buckets from section 4
- Under 140 characters constraint
