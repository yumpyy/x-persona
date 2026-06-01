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
