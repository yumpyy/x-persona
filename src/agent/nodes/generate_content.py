from __future__ import annotations

from pathlib import Path
from typing import Any
from langchain_core.runnables import RunnableConfig

from src.agent.config import get_llm
from src.agent.log import log
from src.agent.nodes.llm_decide import _build_persona_text
from src.agent.state import PersonaState
from src.models.engagement import ActionType, GeneratedText


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

    llm = get_llm(llm_config)
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

        parts.append("\n\nCRITICAL: Follow the persona's profile exactly — match vocabulary, casing, punctuation, and especially the emoji/slang rules from the profile above.")

        user_prompt = "\n".join(parts)

        user_content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]

        # Inject media context if present to allow multimodal evaluation
        if post_data and post_data.media_urls:
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
) -> str:
    """Generate a completely new original standalone tweet conforming to the persona's content buckets, tone rules, current time of day, and recent posting history."""
    llm = get_llm(llm_config)
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
        "GUIDELINES FOR TIME-OF-DAY, DIVERSITY, AND CONTINUITY:\n"
        "- If it is Morning: Talk about waking up early, going for a run (e.g., a 2km run), weather, how you feel waking early, or gym beginner progress.\n"
        "- If it is Afternoon/Evening: Talk about daytime engineering topics: FPGAs, microcontrollers, low-level coding, category theory, abstract algebra, classic programming books, or deadpan OOP/Java slander.\n"
        "- If it is Late Night: Talk about late-night coding, fatigue, category theory math, pulling all-nighters, or sleeping.\n"
        "- CONTINUITY: Read your recent original posts above. If you recently posted about a classic book you are reading (e.g., SICP or K&R C), today you should post about an interesting fact from the book, what you learned today, how much you completed, or your progress.\n"
        "- DIVERSITY: Choose a topic/bucket that is DIFFERENT from your most recent post to keep your feed interesting and cover all aspects of your life (fitness, books, category theory, hardware).\n"
        "- FITNESS SPECIFIC: If posting about the gym or running, write honest, beginner updates. Include the philosophy that doing a little bit (e.g., 15 minutes of workout) is far better than doing nothing at all.\n\n"
        "Follow your persona's profile exactly — match vocabulary, casing, punctuation, and emoji/slang rules.\n"
        "Keep it extremely minimal, quiet, direct, and short (under 140 characters). Do not write any explanations, just the tweet text."
    )

    result = await structured.ainvoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    return result.text.strip()
