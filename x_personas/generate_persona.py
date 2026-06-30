from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from x_personas.agent.config import get_llm

load_dotenv()

PERSONA_TEMPLATE = """# x persona — identity & behavior doc

last updated: {date}

source data: {source_file}

---

## 1. identity & metadata

| field | value |
|---|---|
| handle | {handle} |
| display name | {display_name} |
| bio | {bio} |
| occupation | {occupation} |
| education | {education} |
| location | {location} |
| follower count | {followers} |
| following count | {following} |
| account age | — |
| verified | {verified} |
| pinned tweet | — |

---

## 2. linguistic profile

**primary language:** {primary_lang}
**secondary language:** {secondary_lang}
**code-mixing pattern:** {code_mixing}

**vocabulary:**
{vocab_table}

**emoji usage:**
{emoji_table}

**spelling & grammar quirks:**
{quirks}

**slang:**
{slang_table}

---

## 3. personality & vibe

**core traits:** {traits}

**humor style:** {humor}

**overall vibe:** {vibe}

**never:**
{never_list}

---

## 4. content buckets

{buckets_table}

typical bucket breakdown: {bucket_breakdown}

---

## 5. posting behavior

**original posts:**
{posting_behavior}

**repost & quote tweet behavior:**
{repost_behavior}

---

## 6. reply behavior

**baseline style:** {reply_baseline}

**reply length matrix:**
{reply_matrix}

**reply escalation:**
{reply_escalation}

**argumentative tendency:** {arg_tendency}

**common reply templates:**
{reply_templates}

---

## 7. engagement triggers

**topics that make them stop scrolling:**
{trigger_topics}

**accounts they always engage:**
{trigger_accounts}

**formats they engage most:**
{trigger_formats}

---

## 8. topic stances

{stances_table}

---

## 9. decision engine — feed engagement scoring

### 9a. topic affinity weights

| topic category | weight (0-10) |
{affinity_weights}

### 9b. account relationship weights

| relationship type | weight (0-10) |
|---|---|
| mutual / mutual+close | 10 |
| mutual | 7 |
| admired / reference account | 6 |
| followed but no interaction | 4 |
| stranger | 2 |
| brand / org | 1 |

### 9c. format affinity weights

| post format | weight (0-10) |
{format_weights}

### 9d. recency bonus

| post age | bonus |
|---|---|
| < 1 hour | +3 |
| 1-6 hours | +2 |
| 6-24 hours | +1 |
| > 24 hours | +0 |

### 9e. scoring formula

```
score = (topic_affinity * 0.4) + (account_relationship * 0.3) + (format_affinity * 0.2) + (recency_bonus * 0.1)
```

### 9f. engagement decision thresholds

| score range | action |
|---|---|
| 8-10 | quote tweet + like |
| 6-7.9 | reply + like |
| 4-5.9 | like only |
| 2-3.9 | scroll past, maybe read |
| 0-1.9 | ignore completely |

### 9g. engagement type matrix

| condition | engagement type |
{engagement_matrix}

### 9h. reply generation guidelines

when composing a reply, the persona must:
1. match linguistic profile exactly — code-mix ratio, slang, emoji pattern, casing
2. match typical reply length for this persona
3. stay in character — never express views contradictory to topic stances
4. vary responses — never copy-paste engagement; each reply must feel spontaneous
5. maintain relationship awareness — talk to mutuals differently than strangers
6. never break character or acknowledge being an ai

### 9i. follow decision

**follow criteria:**
| signal | weight |
|---|---|
| topic overlap with persona's interests | 0.4 |
| mutual connections (followed by mutuals) | 0.3 |
| posting frequency & quality | 0.2 |
| bio similarity to persona's reference accounts | 0.1 |

**follow thresholds:**
| score | action |
|---|---|
| 7+ | follow immediately |
| 5-6.9 | observe — engage first, follow after 2+ interactions |
| 3-4.9 | skip |
| <3 | block if spam, else ignore |

**follow limits per session:**
- max follows per hour: 3
- max follows per day: 15

**never follow:**
{never_follow}

---

## 10. reference accounts

{reference_accounts}

---

## 11. current context

**building:** {building}
**learning:** {learning}
**experiencing:** {experiencing}
**upcoming:** {upcoming}

---

## 12. tone rules for all generated content

{tone_rules}

---

## 13. source data & history

the following files contain raw post and reply history. use them as reference for:
- past interaction patterns
- recurring topics and phrases
- relationship dynamics with specific accounts
- authentic language samples to replicate

source files:
- {source_file}

---

## 14. activity log

all persona actions are logged to a per-persona activity log file with the following schema:

| field | description |
|---|---|
| timestamp | iso 8601 |
| action | post / reply / quote_tweet / repost / like / follow / unfollow |
| target | handle or post id |
| content | full text of what was posted/replied |
| score | decision engine score that triggered this action |
| context | brief note on why the action was taken |

activity log file: {activity_log}
"""


def parse_source_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    posts_match = re.search(r"<posts>\s*\n(.*?)\n\s*</posts>", text, re.DOTALL)
    replies_match = re.search(r"<replies>\s*\n(.*?)\n\s*</replies>", text, re.DOTALL)

    posts_text = posts_match.group(1).strip() if posts_match else ""
    replies_text = replies_match.group(1).strip() if replies_match else ""

    posts: list[str] = []
    for line in posts_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("<") and not line.endswith(">"):
            posts.append(line)

    replies: list[str] = []
    for line in replies_text.split("\n"):
        line = line.strip()
        if line and not line.startswith("<") and not line.endswith(">"):
            replies.append(line)

    handle = ""
    display_name = ""
    bio = ""
    followers = ""
    following = ""

    for line in text.split("\n"):
        line = line.strip()
        m = re.match(r"@(\w+)", line)
        if m and not handle:
            handle = m.group(1)
        m = re.match(r"Joined (\w+ \d+)", line)
        if not followers and "Following" in line:
            m2 = re.search(r"([\d,]+)\s*Following", line)
            if m2:
                following = m2.group(1)
        if not followers and "Followers" in line:
            m2 = re.search(r"([\d,]+K?)\s*Followers", line)
            if m2:
                followers = m2.group(1)

    if not display_name:
        for line in text.split("\n"):
            line = line.strip()
            if line and not line.startswith("@") and not line.startswith("<") and not line.startswith("Joined") and not any(x in line.lower() for x in ["following", "followers", "repost", "image", "quote"]):
                if len(line) < 40:
                    display_name = line
                    break

    return {
        "handle": handle,
        "display_name": display_name or handle,
        "bio": bio or "",
        "followers": followers or "",
        "following": following or "",
        "posts": posts,
        "replies": replies,
        "raw_text": text,
    }


def build_llm_prompt(source_data: dict) -> str:
    posts_sample = "\n".join(source_data["posts"][:30])
    replies_sample = "\n".join(source_data["replies"][:30])

    return f"""You are a persona analyst. Given raw X/Twitter posts and replies from a real account, fill out the persona template.

Account handle: @{source_data["handle"]}
Display name: {source_data["display_name"]}

=== POSTS (authored by this account) ===
{posts_sample}

=== REPLIES (authored by this account) ===
{replies_sample}

Fill out the persona-struct.md template below. Be specific — extract actual words, phrases, topics, and patterns from the data. Return ONLY the filled-out fields in this exact format (no markdown code fences, no extra text):

HANDLE=@{source_data["handle"]}
DISPLAY_NAME={source_data["display_name"]}
BIO=
OCCUPATION=
EDUCATION=
LOCATION=
VERIFIED=no
PRIMARY_LANG=
SECONDARY_LANG=
CODE_MIXING=
TRAITS=3-5 adjectives describing personality
HUMOR=humor style description
VIBE=overall vibe description

NEVER_LIST=comma separated list of things this persona never does. extract from data patterns

BUCKET_BREAKDOWN=description like "mostly replies (~50%), original posts (~20%)"

POSTING_BEHAVIOR=2-3 sentences about how they post (length, media, threads)
REPOST_BEHAVIOR=1-2 sentences about repost/quote patterns

REPLY_BASELINE=how replies differ from posts
ARG_TENDENCY=low/medium/high

BUILDING=
LEARNING=
EXPERIENCING=
UPCOMING=

Now, for each of the following sections, provide pipe-delimited table content (one per line, starting with | and ending with |):

=== VOCAB_TABLE ===
| word/phrase | meaning | context |
One row per vocabulary item found in the data.

=== EMOJI_TABLE ===
| emoji | meaning/when used | frequency |
One row per emoji found.

=== QUIRKS ===
Bullet list of spelling and grammar quirks (lowercase? punctuation? abbreviations? sentence length?)
- one per line

=== SLANG_TABLE ===
| slang | meaning | when to use |
One row per slang term found.

=== BUCKETS_TABLE ===
| bucket | freq % | what it looks like | example phrase |
4-5 rows covering their main content types.

=== REPLY_MATRIX ===
| situation | typical length | tone |
One row per situation observed.

=== REPLY_ESCALATION ===
| trigger | shift |
One row per trigger pattern found.

=== REPLY_TEMPLATES ===
| trigger | typical response |
One row per pattern found.

=== TRIGGER_TOPICS ===
| topic | affinity | why |
One row per topic that gets their engagement.

=== TRIGGER_ACCOUNTS ===
| account | relationship | engagement type |
One row per account they engage with.

=== TRIGGER_FORMATS ===
| format | engagement likelihood |
One row per format type.

=== STANCES_TABLE ===
| topic | stance | intensity | nuance |
One row per topic stance found.

=== AFFINITY_WEIGHTS ===
| topic category | weight (0-10) |
One row per topic (weight derived from engagement frequency).

=== FORMAT_WEIGHTS ===
| post format | weight (0-10) |
One row per format type.

=== ENGAGEMENT_MATRIX ===
| condition | engagement type |
Derive from observed patterns in the data.

=== REFERENCE_ACCOUNTS ===
| account | why admired | what they borrow |
From accounts they interact with or mention.

=== NEVER_FOLLOW ===
Bullet list of account types this persona would never follow.
- one per line

=== TONE_RULES ===
Numbered list of tone rules.
1. one per line"""


def parse_llm_output(output: str) -> dict:
    fields: dict[str, str] = {}
    current_section = ""
    section_lines: dict[str, list[str]] = {}

    for line in output.split("\n"):
        line = line.rstrip()
        if line.startswith("===") and line.endswith("==="):
            current_section = line.strip("= ")
            section_lines[current_section] = []
        elif current_section:
            section_lines[current_section].append(line)
        elif "=" in line and not line.startswith("|"):
            parts = line.split("=", 1)
            key = parts[0].strip()
            val = parts[1].strip() if len(parts) > 1 else ""
            fields[key] = val

    for section_name, lines in section_lines.items():
        fields[section_name] = "\n".join(lines)

    return fields


def fill_template(source_data: dict, fields: dict, source_path: str) -> str:
    from datetime import date
    today = date.today().isoformat()
    source_name = Path(source_path).name
    handle = fields.get("HANDLE", f"@{source_data['handle']}").lstrip("@")

    def fmt_table(key: str, header: str | None = None) -> str:
        val = fields.get(key, "")
        lines = [l for l in val.split("\n") if l.strip()]
        if not lines:
            return header or ""
        result = ""
        if header:
            result = header + "\n"
        for l in lines:
            if not l.startswith("|"):
                l = f"| {l} |"
            result += l + "\n"
        return result

    def fmt_bullets(key: str) -> str:
        val = fields.get(key, "")
        lines = [l.strip("- ").strip() for l in val.split("\n") if l.strip()]
        if not lines:
            return "- "
        return "\n".join(f"- {l}" for l in lines)

    def fmt_flat(key: str, default: str = "") -> str:
        return fields.get(key, default) or default

    personality = fields.get("TRAITS", "curious, observant")
    humor = fields.get("HUMOR", "dry, understated")
    vibe = fields.get("VIBE", "")

    return PERSONA_TEMPLATE.format(
        date=today,
        source_file=source_name,
        handle=handle,
        display_name=fields.get("DISPLAY_NAME", source_data["display_name"]),
        bio=fmt_flat("BIO"),
        occupation=fmt_flat("OCCUPATION"),
        education=fmt_flat("EDUCATION"),
        location=fmt_flat("LOCATION"),
        followers=source_data.get("followers", ""),
        following=source_data.get("following", ""),
        verified=fmt_flat("VERIFIED", "no"),
        primary_lang=fmt_flat("PRIMARY_LANG", "English"),
        secondary_lang=fmt_flat("SECONDARY_LANG", ""),
        code_mixing=fmt_flat("CODE_MIXING", "none"),
        vocab_table=fmt_table("VOCAB_TABLE"),
        emoji_table=fmt_table("EMOJI_TABLE"),
        quirks=fmt_bullets("QUIRKS"),
        slang_table=fmt_table("SLANG_TABLE"),
        traits=personality,
        humor=humor,
        vibe=vibe,
        never_list=fmt_bullets("NEVER_LIST"),
        buckets_table=fmt_table("BUCKETS_TABLE", "| bucket | freq % | what it looks like | example phrase |\n|---|---|---|---|"),
        bucket_breakdown=fmt_flat("BUCKET_BREAKDOWN", "original posts / replies / reposts / quote tweets"),
        posting_behavior=fmt_flat("POSTING_BEHAVIOR", "—"),
        repost_behavior=fmt_flat("REPOST_BEHAVIOR", "—"),
        reply_baseline=fmt_flat("REPLY_BASELINE", "—"),
        reply_matrix=fmt_table("REPLY_MATRIX", "| situation | typical length | tone |\n|---|---|---|"),
        reply_escalation=fmt_table("REPLY_ESCALATION", "| trigger | shift |\n|---|---|"),
        arg_tendency=fmt_flat("ARG_TENDENCY", "medium"),
        reply_templates=fmt_table("REPLY_TEMPLATES", "| trigger | typical response |\n|---|---|"),
        trigger_topics=fmt_table("TRIGGER_TOPICS", "| topic | affinity | why |\n|---|---|---|"),
        trigger_accounts=fmt_table("TRIGGER_ACCOUNTS", "| account | relationship | engagement type |\n|---|---|---|"),
        trigger_formats=fmt_table("TRIGGER_FORMATS", "| format | engagement likelihood |\n|---|---|"),
        stances_table=fmt_table("STANCES_TABLE", "| topic | stance | intensity | nuance |\n|---|---|---|---|"),
        affinity_weights=fmt_table("AFFINITY_WEIGHTS", ""),
        format_weights=fmt_table("FORMAT_WEIGHTS", ""),
        engagement_matrix=fmt_table("ENGAGEMENT_MATRIX", "| condition | engagement type |\n|---|---|"),
        reference_accounts=fmt_table("REFERENCE_ACCOUNTS", "| account | why admired | what they borrow |\n|---|---|---|") or "| account | why admired | what they borrow |\n|---|---|---|",
        never_follow=fmt_bullets("NEVER_FOLLOW"),
        building=fmt_flat("BUILDING"),
        learning=fmt_flat("LEARNING"),
        experiencing=fmt_flat("EXPERIENCING"),
        upcoming=fmt_flat("UPCOMING"),
        tone_rules=fmt_bullets("TONE_RULES") or "1. ",
        activity_log=f"{handle}-activity-log.md",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a persona-struct.md from raw source data")
    parser.add_argument("source", help="Path to source data file (e.g. purusha-persona.md)")
    parser.add_argument("--output", "-o", default=None, help="Output path (default: <handle>-persona-struct.md)")
    parser.add_argument("--model", default=None, help="LLM model name (defaults to OPENAI_MODEL env var or gpt-4o-mini)")
    parser.add_argument("--dry-run", action="store_true", help="Show prompt without calling LLM")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Source file not found: {args.source}", file=sys.stderr)
        sys.exit(1)

    source_data = parse_source_file(source_path)
    print(f"Parsed: @{source_data['handle']} — {len(source_data['posts'])} posts, {len(source_data['replies'])} replies")

    output_path = args.output or f"{source_data['handle']}-persona-struct.md"

    if args.dry_run:
        prompt = build_llm_prompt(source_data)
        print(f"\n=== LLM PROMPT ({len(prompt)} chars) ===\n")
        print(prompt[:3000] + "...\n")
        print(f"Would write to: {output_path}")
        return

    llm_config = {}
    if args.model:
        llm_config["model"] = args.model
    llm = get_llm(llm_config)

    prompt = build_llm_prompt(source_data)

    print("Analyzing with LLM...")
    response = llm.invoke([
        {"role": "user", "content": prompt},
    ])
    output = response.content.strip()

    fields = parse_llm_output(output)
    filled = fill_template(source_data, fields, args.source)

    Path(output_path).write_text(filled, encoding="utf-8")
    print(f"Wrote persona to: {output_path}")


if __name__ == "__main__":
    main()
