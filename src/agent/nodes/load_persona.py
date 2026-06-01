from __future__ import annotations

import re
from pathlib import Path

from src.agent.state import PersonaState


def _extract_table_section(lines: list[str], start: int) -> dict:
    data: dict = {}
    in_table = False
    for i in range(start, len(lines)):
        line = lines[i]
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                in_table = True
                continue
            if re.match(r"^[\s|-]+\|?[\s|-]+$", line):
                continue
            if len(cells) >= 2 and cells[0] and not cells[0].startswith("-"):
                key = cells[0].strip()
                val = cells[1].strip() if len(cells) > 1 else ""
                data[key] = val
        else:
            if in_table:
                break
    return data


def _extract_table_rows(lines: list[str], start: int) -> list[dict]:
    rows: list[dict] = []
    in_table = False
    for i in range(start, len(lines)):
        line = lines[i]
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                in_table = True
                continue
            if re.match(r"^[\s|-]+\|?[\s|-]+$", line):
                continue
            if cells and cells[0] and not cells[0].startswith("-"):
                row: dict = {}
                for j, cell in enumerate(cells):
                    row[f"col{j}"] = cell
                rows.append(row)
        else:
            if in_table:
                break
    return rows


def _parse_section_number(heading: str) -> str | None:
    m = re.match(r"##\s+(\d+(?:[a-z])?)", heading)
    if m:
        return m.group(1)
    return None


def _find_section(lines: list[str], section_num: str) -> tuple[int, int] | None:
    for i, line in enumerate(lines):
        if re.match(rf"#{{2,3}}\s+{section_num}[\.\s)]", line.strip()):
            start = i
            end = len(lines)
            for j in range(i + 1, len(lines)):
                if re.match(r"#{2,3}\s+\d", lines[j].strip()):
                    end = j
                    break
            return start, end
    return None


def _parse_decision_weights(lines: list[str], section_num: str) -> dict[str, float]:
    bounds = _find_section(lines, section_num)
    if not bounds:
        return {}
    table = _extract_table_section(lines, bounds[0] + 1)
    weights: dict[str, float] = {}
    for key, val in table.items():
        try:
            weights[key.strip()] = float(val)
        except (ValueError, TypeError):
            pass
    return weights


def _parse_thresholds(lines: list[str]) -> dict[str, str]:
    bounds = _find_section(lines, "9f")
    if not bounds:
        return {}
    rows = _extract_table_rows(lines, bounds[0] + 1)
    thresholds: dict[str, str] = {}
    for row in rows:
        score_range = row.get("col0", "")
        action = row.get("col1", "")
        if score_range:
            thresholds[score_range] = action
    return thresholds


def _parse_engagement_matrix(lines: list[str]) -> list[dict]:
    bounds = _find_section(lines, "9g")
    if not bounds:
        return []
    rows = _extract_table_rows(lines, bounds[0] + 1)
    matrix: list[dict] = []
    for row in rows:
        condition = row.get("col0", "")
        eng_type = row.get("col1", "")
        if condition:
            matrix.append({"condition": condition, "engagement_type": eng_type})
    return matrix


def _parse_follow_criteria(lines: list[str]) -> dict[str, float]:
    bounds = _find_section(lines, "9i")
    if not bounds:
        return {}
    table = _extract_table_section(lines, bounds[0] + 1)
    criteria: dict[str, float] = {}
    for key, val in table.items():
        try:
            criteria[key.strip()] = float(val)
        except (ValueError, TypeError):
            pass
    return criteria


def _parse_source_data_files(lines: list[str]) -> list[str]:
    bounds = _find_section(lines, "13")
    if not bounds:
        return []
    files: list[str] = []
    for i in range(bounds[0] + 1, bounds[1]):
        line = lines[i].strip()
        m = re.search(r"-\s+(.+\.md)\s*$", line)
        if m:
            files.append(m.group(1).strip())
    return files


def _parse_bucket_breakdown(lines: list[str]) -> dict:
    bounds = _find_section(lines, "4")
    if not bounds:
        return {}
    return _extract_table_section(lines, bounds[0] + 1)


def _parse_reply_matrix(lines: list[str]) -> dict:
    bounds = _find_section(lines, "6")
    if not bounds:
        return {}

    length_matrix: list[dict] = []
    escalation: list[dict] = []
    in_table = False
    in_escalation = False

    for i in range(bounds[0] + 1, bounds[1]):
        line = lines[i]
        if "reply escalation" in line.lower():
            in_escalation = True
            in_table = False
            continue
        if line.startswith("##"):
            break
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells[0] or re.match(r"^[\s|-]+$", line):
                continue
            if not in_escalation:
                if not in_table and len(cells) >= 3 and "situation" in cells[0].lower():
                    in_table = True
                    continue
                if in_table and len(cells) >= 3:
                    length_matrix.append({
                        "situation": cells[0],
                        "length": cells[1],
                        "tone": cells[2] if len(cells) > 2 else "",
                    })
            else:
                if len(cells) >= 2:
                    escalation.append({
                        "trigger": cells[0],
                        "shift": cells[1] if len(cells) > 1 else "",
                    })

    return {
        "baseline_style": "",
        "length_matrix": length_matrix,
        "escalation_triggers": escalation,
    }


def _parse_engagement_triggers(lines: list[str]) -> dict:
    bounds = _find_section(lines, "7")
    if not bounds:
        return {}
    topics: list[dict] = []
    accounts: list[dict] = []
    formats: list[dict] = []

    current = "topics"
    for i in range(bounds[0] + 1, bounds[1]):
        line = lines[i]
        if "accounts they always engage" in line.lower():
            current = "accounts"
            continue
        if "formats they engage most" in line.lower():
            current = "formats"
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells[0] or re.match(r"^[\s|-]+$", line):
                continue
            if current == "topics" and len(cells) >= 3:
                topics.append({
                    "topic": cells[0],
                    "affinity": cells[1] if len(cells) > 1 else "",
                    "why": cells[2] if len(cells) > 2 else "",
                })
            elif current == "accounts" and len(cells) >= 3:
                accounts.append({
                    "account": cells[0],
                    "relationship": cells[1] if len(cells) > 1 else "",
                    "engagement_type": cells[2] if len(cells) > 2 else "",
                })
            elif current == "formats" and len(cells) >= 2:
                formats.append({
                    "format": cells[0],
                    "likelihood": cells[1] if len(cells) > 1 else "",
                })

    return {
        "topics": topics,
        "accounts": accounts,
        "formats": formats,
        "keywords": [(t["topic"], [t["topic"].lower()]) for t in topics],
    }


def _parse_linguistic_profile(lines: list[str]) -> dict:
    bounds = _find_section(lines, "2")
    if not bounds:
        return {}

    result: dict = {
        "vocabulary": [],
        "emoji_usage": [],
        "slang": [],
    }
    in_vocab = False
    in_emoji = False
    in_slang = False

    for i in range(bounds[0] + 1, bounds[1]):
        line = lines[i]
        lower = line.lower()
        if "vocabulary" in lower and line.startswith("|") is False:
            in_vocab = True
            in_emoji = False
            in_slang = False
            continue
        if "emoji usage" in lower:
            in_vocab = False
            in_emoji = True
            in_slang = False
            continue
        if lower.strip().startswith("**slang**") or (lower.startswith("slang") and not line.startswith("|")):
            in_vocab = False
            in_emoji = False
            in_slang = True
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells[0]:
                continue
            if in_vocab and len(cells) >= 3:
                result["vocabulary"].append({
                    "word": cells[0],
                    "meaning": cells[1],
                    "context": cells[2] if len(cells) > 2 else "",
                })
            elif in_emoji and len(cells) >= 3:
                result["emoji_usage"].append({
                    "emoji": cells[0],
                    "meaning": cells[1],
                    "frequency": cells[2] if len(cells) > 2 else "",
                })
            elif in_slang and len(cells) >= 3:
                result["slang"].append({
                    "slang": cells[0],
                    "meaning": cells[1],
                    "when": cells[2] if len(cells) > 2 else "",
                })

    return result


def load_persona(state: PersonaState) -> dict:
    if state.get("persona_sections"):
        return {}

    persona_file = state["persona_file"]
    path = Path(persona_file)
    lines = path.read_text(encoding="utf-8").split("\n")

    sections: dict = {}
    source_data_files: list[str] = []

    identity = _find_section(lines, "1")
    if identity:
        sections["1"] = _extract_table_section(lines, identity[0] + 1)

    sections["2"] = _parse_linguistic_profile(lines)

    pv = _find_section(lines, "3")
    if pv:
        sections["3"] = _extract_table_section(lines, pv[0] + 1)

    sections["4"] = _parse_bucket_breakdown(lines)

    sections["6"] = _parse_reply_matrix(lines)

    sections["7"] = _parse_engagement_triggers(lines)

    stances = _find_section(lines, "8")
    if stances:
        sections["8"] = _extract_table_section(lines, stances[0] + 1)

    sections["9a"] = _parse_decision_weights(lines, "9a")
    sections["9b"] = _parse_decision_weights(lines, "9b")
    sections["9c"] = _parse_decision_weights(lines, "9c")
    sections["9d"] = _parse_decision_weights(lines, "9d")
    sections["9f"] = _parse_thresholds(lines)
    sections["9g"] = _parse_engagement_matrix(lines)

    gh_bounds = _find_section(lines, "9h")
    if gh_bounds:
        guidelines = [g.strip() for g in lines[gh_bounds[0] + 1:gh_bounds[1]] if g.strip() and not g.strip().startswith("##")]
        sections["9h"] = guidelines

    sections["9i"] = _parse_follow_criteria(lines)

    source_data_files = _parse_source_data_files(lines)

    sections["13"] = {"source_files": source_data_files}

    return {
        "persona_sections": sections,
        "source_data_files": source_data_files,
    }
