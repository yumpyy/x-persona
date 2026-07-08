"""Generate reply/quote text using LLM with writing samples."""

from __future__ import annotations

from xpersonas.agent.state import AgentState
from xpersonas.core.models import GeneratedText


def _load_writing_samples(state: AgentState) -> str:
    """Load writing samples from source data files."""
    samples = state.get("source_data_samples", [])
    return "\n---\n".join(samples[:3]) if samples else ""


def _build_recent_context(state: AgentState) -> str:
    """Build context from recent engagements for dedup."""
    actions = state.get("executed_actions", [])
    recent = actions[-15:] if len(actions) > 15 else actions
    if not recent:
        return ""
    lines = []
    for a in recent:
        if a.get("success") and a.get("action", {}).get("content"):
            lines.append(f"- {a['action']['content'][:200]}")
    return "\n".join(lines) if lines else ""


async def generate_content(state: AgentState, config=None) -> dict:
    """Generate reply/quote text for pending actions."""
    from xpersonas.core.config import resolve_llm_config

    persona = state.get("persona_config", {})
    pending = state.get("pending_actions", [])
    thread_contexts = state.get("thread_contexts", {})

    text_actions = [a for a in pending if a.get("action_type") in ("reply", "quote") and not a.get("content")]
    if not text_actions:
        return {}

    llm_config = resolve_llm_config(persona)
    writing_samples = _load_writing_samples(state)
    recent_context = _build_recent_context(state)

    identity = persona.get("identity", {})
    personality = persona.get("personality", {})
    reply_style = persona.get("reply_style", {})

    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=llm_config.model,
            api_key=llm_config.api_key,
            base_url=llm_config.base_url or None,
            temperature=0.8,
        )
        structured_llm = llm.with_structured_output(GeneratedText)
    except Exception as e:
        return {"error": str(e)}

    updated_pending = list(pending)

    for action in text_actions:
        post_id = action["target_id"]
        replies = thread_contexts.get(post_id, [])
        existing_text = "\n".join(f"- @{r.author_handle}: {r.text[:150]}" for r in replies[:10])

        system_prompt = (
            f"You are {identity.get('display_name', 'a user')} (@{identity.get('handle', '')}).\n"
            f"Personality: {', '.join(personality.get('core_traits', []))}\n"
            f"Reply style: {reply_style.get('baseline', 'natural, conversational')}\n"
            f"Never do: {', '.join(personality.get('never', []))}\n"
            f"\nYour writing samples:\n{writing_samples}\n"
            f"\nCRITICAL RULES:\n"
            f"- Match the persona's vocabulary, tone, and style exactly\n"
            f"- Be concise (2-4 sentences typical)\n"
            f"- Do NOT repeat points already made in the thread\n"
            f"- Do NOT use superlatives or marketing language\n"
            f"- Be genuine and helpful, not promotional\n"
        )

        user_prompt = f"Post you're responding to: {action.get('reason', '')}\n"
        if existing_text:
            user_prompt += f"\nExisting replies in thread:\n{existing_text}\n"
        if recent_context:
            user_prompt += f"\nYour recent engagements (avoid repeating):\n{recent_context}\n"
        user_prompt += f"\nWrite a {'reply' if action['action_type'] == 'reply' else 'quote'} in your voice."

        try:
            response = await structured_llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
            if response.text and response.text.strip() != "[SKIP]":
                for i, a in enumerate(updated_pending):
                    if a["target_id"] == post_id and a["action_type"] == action["action_type"] and not a.get("content"):
                        updated_pending[i] = {**a, "content": response.text.strip()}
                        break
        except Exception:
            continue

    return {"pending_actions": updated_pending}
