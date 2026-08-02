"""Schéma strict du bus. Chaque message porte un trace_id."""
from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field

PiiLevel = Literal["none", "low", "medium", "high"]


class BusMessage(BaseModel):
    """Message d'agent à agent."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = Field(default_factory=time.time)
    from_agent: str
    to_agent: str
    kind: str  # ex "task.dispatch", "result.return", "handoff", "escalation"
    venture: str | None = None
    zone: str | None = None
    pii_level: PiiLevel = "none"
    payload: dict[str, Any] = Field(default_factory=dict)


class BusEvent(BaseModel):
    """Évènement non adressé (pub/sub)."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = Field(default_factory=time.time)
    kind: str  # ex "scope_violation", "budget_exceeded", "golden_fail"
    source: str
    venture: str | None = None
    zone: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
