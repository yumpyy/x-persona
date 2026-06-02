from __future__ import annotations

from pathlib import Path


def load_engaged_status_ids(log_file: str) -> set[str]:
    path = Path(log_file)
    if not path.exists():
        return set()

    ids: set[str] = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("| timestamp") or line.startswith("|---"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 4:
            target = parts[3]
            if " / " in target:
                status_id = target.split(" / ")[-1].strip()
                check_id = status_id.split()[0] if " " in status_id else status_id
                if check_id.isdigit():
                    ids.add(check_id)
    return ids


def load_recent_original_posts(log_file: str, limit: int = 5) -> list[str]:
    path = Path(log_file)
    if not path.exists():
        return []

    posts: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        # Read backwards
        for line in reversed(lines):
            line = line.strip()
            if not line or line.startswith("| timestamp") or line.startswith("|---"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 5:
                action = parts[2]
                content = parts[4]
                if action == "original_post" and content:
                    posts.append(content)
                    if len(posts) >= limit:
                        break
    except Exception:
        pass
    return posts


def load_engagements_since_last_post(log_file: str) -> int:
    path = Path(log_file)
    if not path.exists():
        return 0

    count = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        # Read backwards
        for line in reversed(lines):
            line = line.strip()
            if not line or line.startswith("| timestamp") or line.startswith("|---"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                action = parts[2]
                context = parts[6]
                
                # If we encounter an original post, we stop counting!
                if action == "original_post":
                    break
                
                # Check if it was a successful engagement (concluding with [✓])
                if action in ("like", "reply", "quote", "repost") and "[✓]" in context:
                    count += 1
    except Exception:
        pass
    return count


def load_recent_engagements(log_file: str, limit: int = 15) -> list[dict]:
    path = Path(log_file)
    if not path.exists():
        return []

    engagements: list[dict] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        # Read backwards
        for line in reversed(lines):
            line = line.strip()
            if not line or line.startswith("| timestamp") or line.startswith("|---"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 7:
                timestamp = parts[1]
                action = parts[2]
                target = parts[3]
                content = parts[4]
                score = parts[5]
                context = parts[6]
                
                # Check if it was a successful engagement (concluding with [✓])
                if action in ("like", "reply", "quote", "repost") and "[✓]" in context:
                    clean_context = context.replace("[✓]", "").strip()
                    engagements.append({
                        "timestamp": timestamp,
                        "action": action,
                        "target": target,
                        "content": content,
                        "score": score,
                        "context": clean_context
                    })
                    if len(engagements) >= limit:
                        break
    except Exception:
        pass
    return engagements
