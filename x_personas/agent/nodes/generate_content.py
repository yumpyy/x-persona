from __future__ import annotations

from pathlib import Path
from typing import Any
from langchain_core.runnables import RunnableConfig

from x_personas.agent.config import get_llm
from x_personas.agent.log import log
from x_personas.agent.nodes.llm_decide import _build_persona_text
from x_personas.agent.state import PersonaState
from x_personas.models.engagement import ActionType, GeneratedText


def _build_system_text(sections: dict[str, Any]) -> str:
    """Build the LLM system prompt by prefixing core guidelines to the compiled persona text."""
    return (
        "You are an AI that writes social media content matching a specific persona. "
        "Never break character or acknowledge being an AI.\n\n"
    ) + _build_persona_text(sections)


def _extract_mutual_handles(sections: dict[str, Any]) -> set[str]:
    """Extract a cleaned set of lowercase usernames representing close mutuals or friends."""
    mutuals: set[str] = set()
    accounts = sections.get("7", {}).get("accounts", [])
    for acc in accounts:
        handle = acc.get("account", "").strip().lower().replace("@", "")
        rel = acc.get("relationship", "").strip().lower()
        if handle and ("friend" in rel or "mutual" in rel):
            mutuals.add(handle)
    return mutuals


async def generate_content(state: PersonaState, config: RunnableConfig | None = None) -> dict[str, Any]:
    """Generate high-quality persona-conforming content for pending replies or quotes.

    Performs semantic deduplication against existing thread replies, implements
    reply-to-reply chaining when close mutuals are active, and incorporates multimodal
    media context when images are present.
    """
    sections = state.get("persona_sections", {})
    pending = state.get("pending_actions", [])
    source_files = state.get("source_data_files", [])
    llm_config = state.get("llm_config", {})
    vlm_config = state.get("vlm_config")
    thread_contexts = state.get("thread_contexts", {})

    text_actions = [a for a in pending if a.action_type in (ActionType.REPLY, ActionType.QUOTE)]
    if not text_actions:
        return {"pending_actions": pending, "_routing_target": "execute_actions"}

    mutual_handles = _extract_mutual_handles(sections)
    log(f"generate_content: extracted close mutual handles: {mutual_handles}")

    source_samples: list[str] = []
    for sf in source_files:
        try:
            path = Path(sf)
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                source_samples.append(text[:2000])
        except (OSError, UnicodeDecodeError) as err:
            log(f"generate_content: failed to load source sample '{sf}': {err}")

    gen_cfg = vlm_config if vlm_config else dict(llm_config)
    gen_cfg = dict(gen_cfg)
    gen_cfg["temperature"] = 0.8  # Increase creativity and diversity for replies/quotes
    llm = get_llm(gen_cfg)
    structured = llm.with_structured_output(GeneratedText)
    system_prompt = _build_system_text(sections)

    log(f"generate_content: generating {len(text_actions)} texts via LLM")

    filtered_pending = list(pending)

    for action in text_actions:
        if action.content is not None:
            continue

        status_id = action.target_status_id
        action_label = "reply" if action.action_type == ActionType.REPLY else "quote tweet"

        # --- Reply-to-Reply Chaining Check ---
        post_data = thread_contexts.get(status_id)
        replies_text = ""
        is_chained = False
        original_author = action.target_handle

        if post_data and post_data.replies:
            # Check if any reply is by a close mutual
            for reply in post_data.replies:
                rep_handle = reply.handle.lower().replace("@", "")
                if rep_handle in mutual_handles:
                    # Pivot the reply target status ID directly to the mutual's comment
                    log(f"  [CHAINING] Found mutual's reply by @{reply.handle} in thread. Chaining reply target: {status_id} -> {reply.status_id}")
                    action.target_status_id = reply.status_id
                    action.target_handle = reply.handle
                    is_chained = True
                    break

            # Format the top 15 replies for the semantic deduplication context
            lines = []
            for i, r in enumerate(post_data.replies[:15], 1):
                lines.append(f"  Reply {i} by @{r.handle}: \"{r.text}\"")
            replies_text = "\n".join(lines)

        log(f"generate_content: generating {action_label} for @{action.target_handle} id={action.target_status_id}")

        parts = [f"Write a {action_label} to @{action.target_handle}."]
        if is_chained:
            parts.append(f"Note: You are replying directly to @{action.target_handle}'s comment in the thread, in response to the original post by @{original_author}.")

        parts.append(f"\nReason for engaging: {action.reason}")

        if replies_text:
            parts.append(f"\nHere are the existing replies on the thread:\n{replies_text}")
            parts.append("\nCRITICAL DEDUPLICATION CHECK: Read the existing replies carefully. Your generated text MUST NOT repeat or duplicate any point, argument, joke, or phrasing already present in the existing replies. Ensure your reply is completely unique. If the thread is saturated with similar comments or no fresh, character-conforming angle remains, return exactly the word [SKIP].")
        else:
            parts.append("\nCRITICAL: If the target post is inappropriate or no fresh, character-conforming angle remains, return exactly the word [SKIP].")

        if source_samples:
            parts.append("\nReference writing samples:\n" + "\n\n".join(s[:600] for s in source_samples[:3]))

        # Load and append recent engagements to ensure variety in reply content
        recent_engagements = []
        log_file = state.get("activity_log_file", "")
        if log_file:
            from x_personas.agent.history import load_recent_engagements
            recent_engagements = load_recent_engagements(log_file, limit=15)
        
        if recent_engagements:
            from x_personas.agent.nodes.llm_decide import _build_recent_engagements_text
            recent_text = _build_recent_engagements_text(recent_engagements)
            parts.append(
                f"\n\nCRITICAL REPETITION AVOIDANCE RULE:\n"
                f"Here are your own recent successful engagements (actions you took and what you wrote):\n"
                f"{recent_text}\n"
                f"You MUST NOT repeat the same arguments, concepts, criticisms, themes, vocabulary, or sentence patterns "
                f"as the ones you have written in your recent replies listed above. Ensure this reply is completely fresh, "
                f"distinct, and addresses a different aspect or uses a completely different phrasing."
            )

        parts.append(
            "\n\nCRITICAL DIVERSITY & SPONTANEITY RULE: Read the 'common reply templates' (or trigger/typical response tables) in the persona profile above if any. "
            "DO NOT copy-paste or repeat those exact template phrases literally across multiple replies! "
            "Every single reply must be custom-written, highly spontaneous, and unique. Treat templates purely as stylistic inspiration "
            "for the brevity, vibe, and tone, never as exact copy-paste text or repetitive macros."
        )
        parts.append(
            "\n\nCRITICAL TECHNICAL ACCURACY & CONTEXTUAL RELEVANCE RULE:\n"
            "1. Read the target post's code, technology, and programming language/topic very carefully.\n"
            "2. Your reply/quote must be highly relevant and technically accurate to the specific topic discussed. "
            "Only mention specialized jargon, stances, or vocabulary from your persona profile when they make complete technical and contextual sense "
            "in the context of the target post's specific technology, language, or domain.\n"
            "3. For example, do not force specialized theoretical concepts onto standard procedural or imperative posts unless they fit contextually, "
            "and do not force low-level concepts onto high-level web posts unless it makes perfect sense for your character's stance. "
            "Avoid blind keyword matching. Write a natural, technically coherent reply that a real, highly capable human developer or expert in that niche would write."
        )
        parts.append("\n\nCRITICAL: Follow the persona's profile exactly — match vocabulary, casing, punctuation, and especially the emoji/slang rules from the profile above.")

        user_prompt = "\n".join(parts)

        user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]

        # Inject media context if present and VLM is configured
        if vlm_config and post_data and post_data.media_urls:
            for url in post_data.media_urls[:2]:
                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": url}
                })

        log(f"generate_content: system ({len(system_prompt)} chars), user ({len(user_content)} blocks)")

        try:
            result: GeneratedText = structured.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ])
            content = result.text.strip()

            if content == "[SKIP]" or content.startswith("[SKIP]"):
                log(f"generate_content: LLM requested [SKIP] for @{action.target_handle} id={action.target_status_id}")
                action.content = "[SKIP]"
                if action in filtered_pending:
                    filtered_pending.remove(action)
            else:
                action.content = content
                log(f"generate_content: response ({len(content)} chars): {content}")
        except Exception as e:
            log(f"generate_content: LLM generation error for @{action.target_handle}: {e}")
            # Robust boundary protection: skip the action if content generation fails
            if action in filtered_pending:
                filtered_pending.remove(action)

    return {
        "pending_actions": filtered_pending,
        "_routing_target": "execute_actions",
    }


async def generate_original_post(
    sections: dict[str, Any],
    llm_config: dict[str, Any],
    time_of_day: str,
    recent_posts: list[str],
    prompt: str = "",
) -> str:
    """Generate a completely new original standalone tweet conforming to the persona's content buckets, tone rules, current time of day, and recent posting history."""
    creative_config = dict(llm_config)
    creative_config["temperature"] = 0.85  # Higher creativity for original standalone posts
    llm = get_llm(creative_config)
    structured = llm.with_structured_output(GeneratedText)
    system_prompt = _build_system_text(sections)

    buckets = sections.get("4", {})
    buckets_text = ""
    if isinstance(buckets, dict):
        buckets_text = "\n".join(f"- {k}: {v}" for k, v in buckets.items())

    recent_text = ""
    if recent_posts:
        recent_list = "\n".join(f"- \"{p}\"" for p in recent_posts)
        recent_text = f"\nYour recent original posts:\n{recent_list}\n"

    user_prompt = (
        f"The current time of day is: {time_of_day}.\n"
        "Draft a brand new original standalone tweet in your voice.\n"
        "It must not be a reply or a quote. It must be a new post representing one of your content buckets:\n"
        f"{buckets_text}\n"
        f"{recent_text}\n"
        + (f"USER TOPIC GUIDANCE: {prompt}\n\n" if prompt else "")
        + "GUIDELINES FOR TIME-OF-DAY, DIVERSITY, AND CONTINUITY:\n"
        "- TIME-OF-DAY ALIGNMENT: Align the theme of your post with the time of day. For example, morning tweets might touch on morning routines, early starts, or starting the day; afternoon/evening tweets on core daytime topics, professional work, or daytime hobbies; and late-night tweets on late-night thoughts, winding down, or reflections.\n"
        "- CONTINUITY: Read your recent original posts above. If you recently posted about an ongoing activity, project, book, or hobby, you may post a continuation (e.g., progress update, new discovery, or next step) to maintain natural narrative threads.\n"
        "- DIVERSITY: Choose a topic or bucket that is DIFFERENT from your most recent post to keep your feed interesting and cover all aspects of your defined persona (e.g., balance professional, hobby, and personal thoughts if applicable).\n\n"
        "Follow your persona's profile exactly — match vocabulary, casing, punctuation, and emoji/slang rules.\n"
        "Keep it extremely minimal, quiet, direct, and short (under 140 characters). Do not write any explanations, just the tweet text."
    )

    result = await structured.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    return result.text.strip()
