from datetime import datetime, timezone
from typing import List
import uuid

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FailureEvent(BaseModel):
    """A single recorded failure."""
    id: str = Field(default_factory=lambda: f"fail_{uuid.uuid4().hex[:12]}")
    timestamp: datetime = Field(default_factory=_now)

    error_category: str
    description: str

    task_type: str
    agent_id: str
    context_pattern: str

    root_cause: str
    resolution: str
    prevention: str

    severity: str = "medium"
    tags: List[str] = Field(default_factory=list)


class WarningResult(BaseModel):
    """A pre-emptive warning retrieved before a task."""
    failure_id: str
    context_pattern: str
    prevention: str
    severity: str
    similarity: float
