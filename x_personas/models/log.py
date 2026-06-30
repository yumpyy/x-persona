from typing import Optional

from pydantic import BaseModel


class ActivityLogEntry(BaseModel):
    timestamp: str
    action: str
    target: str
    content: Optional[str] = None
    score: float
    context: str


class ActivityLog(BaseModel):
    entries: list[ActivityLogEntry]
    activity_log_file: str
