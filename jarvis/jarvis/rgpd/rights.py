"""Droits RGPD exercés : erasure, portabilité, rectification, opposition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jarvis.memory.memory import Memory
from jarvis.observability.audit import audit


@dataclass
class RgpdResponse:
    subject_id: str
    action: str
    records_affected: int
    payload: Any | None = None


class RgpdRights:
    def __init__(self, memory: Memory) -> None:
        self._memory = memory

    def forget(self, subject_id: str) -> RgpdResponse:
        n = self._memory.forget_subject(subject_id)
        audit("rgpd_forget", subject_id=subject_id, records=n)
        return RgpdResponse(subject_id, "forget", n)

    def export(self, subject_id: str) -> RgpdResponse:
        data = self._memory.export_subject(subject_id)
        audit("rgpd_export", subject_id=subject_id, records=len(data))
        return RgpdResponse(subject_id, "export", len(data), payload=data)
