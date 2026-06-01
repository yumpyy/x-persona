from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.agent.log import log
from src.agent.rate_limiter import RateLimitState
from src.agent.state import PersonaState


def _format_entry(timestamp: str, action: str, target: str, content: str | None, score: float, context: str) -> str:
    content_str = content.replace("\n", " ") if content else ""
    return f"| {timestamp} | {action} | {target} | {content_str} | {score:.1f} | {context} |"


def _init_log_file(path: Path) -> None:
    if not path.exists():
        header = "| timestamp | action | target | content | score | context |\n|---|---|---|---|---|---|\n"
        path.write_text(header, encoding="utf-8")


def log_activity(state: PersonaState) -> dict:
    log_file = state.get("activity_log_file", "activity-log.md")
    executed = state.get("executed_actions", [])
    path = Path(log_file)
    _init_log_file(path)

    rl = RateLimitState(state.get("rate_limit_file"))
    timestamp = datetime.now(timezone.utc).isoformat()

    entries: list[str] = []
    for ex in executed:
        action_label = ex.action.action_type.value if hasattr(ex.action.action_type, 'value') else str(ex.action.action_type)
        success_mark = "\u2713" if ex.success else "\u2717"
        target = f"@{ex.action.target_handle} / {ex.action.target_status_id}"
        content = ex.action.content
        score = ex.action.score
        context = f"{ex.action.reason} [{success_mark}]"

        entry = _format_entry(timestamp, action_label, target, content, score, context)
        entries.append(entry)

        if ex.success:
            rl.record(action_label, timestamp)

    if entries:
        with open(str(path), "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(entry + "\n")
        log(f"log: wrote {len(entries)} entries to {path.name}")
    else:
        log(f"log: nothing to write (no executed actions)")

    rl.save()

    return {}
