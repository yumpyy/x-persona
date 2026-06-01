from __future__ import annotations

from pathlib import Path

from src.agent.config import get_llm
from src.agent.log import log
from src.agent.nodes.llm_decide import _build_persona_text
from src.agent.state import PersonaState
from src.models.engagement import ActionType, GeneratedText


def _build_system_text(sections: dict) -> str:
    return "You are an AI that writes social media content matching a specific persona. Never break character or acknowledge being an AI.\n\n" + _build_persona_text(sections)


async def generate_content(state: PersonaState, config=None) -> dict:
    sections = state.get("persona_sections", {})
    pending = state.get("pending_actions", [])
    source_files = state.get("source_data_files", [])
    llm_config = state.get("llm_config", {})

    text_actions = [a for a in pending if a.action_type in (ActionType.REPLY, ActionType.QUOTE)]
    if not text_actions:
        return {"pending_actions": pending, "_routing_target": "execute_actions"}

    source_samples: list[str] = []
    for sf in source_files:
        try:
            text = Path(sf).read_text(encoding="utf-8")
            source_samples.append(text[:2000])
        except Exception:
            pass

    llm = get_llm(llm_config)
    structured = llm.with_structured_output(GeneratedText)
    system_prompt = _build_system_text(sections)

    log(f"generate_content: generating {len(text_actions)} texts via LLM")

    for action in text_actions:
        if action.content is not None:
            continue

        action_label = "reply" if action.action_type == ActionType.REPLY else "quote tweet"
        log(f"generate_content: generating {action_label} for @{action.target_handle} id={action.target_status_id}")

        parts = [f"Write a {action_label} to @{action.target_handle}."]
        parts.append(f"\nReason for engaging: {action.reason}")
        if source_samples:
            parts.append("\nReference writing samples:\n" + "\n\n".join(s[:600] for s in source_samples[:3]))
        parts.append("\n\nWrite in the persona's natural voice. Be concise and spontaneous.")

        user_prompt = "\n".join(parts)

        log(f"generate_content: system ({len(system_prompt)} chars), user ({len(user_prompt)} chars)")

        try:
            result: GeneratedText = structured.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
            content = result.text.strip()
            action.content = content
            log(f"generate_content: response ({len(content)} chars): {content}")
        except Exception as e:
            log(f"generate_content: LLM error for @{action.target_handle}: {e}")

    return {
        "pending_actions": pending,
        "_routing_target": "execute_actions",
    }
