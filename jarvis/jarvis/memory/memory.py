"""Mémoire 4 couches avec tags obligatoires.

Couches :
  L1 working (in-context, volatile, expire fin de run)
  L2 episodic (derniers runs, 30 jours)
  L3 semantic (faits stables, vecteurs)
  L4 archive (cold storage, > 90 jours)

Tags obligatoires sur chaque record :
  venture, zone, pii_level, source_trust, retention_days

En Phase 1.1 : stockage mémoire. En Phase 1.3 : Supabase pgvector pour L3.
"""
from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from jarvis.bus.schema import PiiLevel


class MemoryLayer(str, Enum):
    WORKING = "L1_working"
    EPISODIC = "L2_episodic"
    SEMANTIC = "L3_semantic"
    ARCHIVE = "L4_archive"


_DEFAULT_RETENTION = {
    MemoryLayer.WORKING: 0,  # volatile
    MemoryLayer.EPISODIC: 30,
    MemoryLayer.SEMANTIC: 365,
    MemoryLayer.ARCHIVE: 1095,  # 3 ans
}


@dataclass
class MemoryRecord:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    layer: MemoryLayer = MemoryLayer.EPISODIC
    key: str = ""
    value: Any = None
    venture: str = ""
    zone: str = "FR"
    pii_level: PiiLevel = "none"
    source_trust: float = 0.5  # 0=rumeur, 1=officiel vérifié
    retention_days: int = 30
    subject_id: str | None = None  # pour RGPD `/forget`
    created_at: float = field(default_factory=time.time)

    def expired(self, now: float | None = None) -> bool:
        if self.retention_days <= 0 and self.layer != MemoryLayer.WORKING:
            return False
        if self.layer == MemoryLayer.WORKING:
            return True  # working volatile, purgée fin de run
        elapsed = (now or time.time()) - self.created_at
        return elapsed > self.retention_days * 86400


class Memory:
    """Interface mémoire. Backend par défaut : dict. Production : Supabase."""

    def __init__(self) -> None:
        self._by_id: dict[str, MemoryRecord] = {}
        self._index: dict[tuple[str, str], list[str]] = defaultdict(list)  # (venture,zone) → ids

    def write(self, record: MemoryRecord) -> str:
        if not record.venture:
            raise ValueError("memory.write: tag 'venture' obligatoire")
        if record.retention_days == 0 and record.layer != MemoryLayer.WORKING:
            record.retention_days = _DEFAULT_RETENTION[record.layer]
        self._by_id[record.id] = record
        self._index[(record.venture, record.zone)].append(record.id)
        return record.id

    def read(self, rid: str) -> MemoryRecord | None:
        return self._by_id.get(rid)

    def query(
        self,
        *,
        venture: str | None = None,
        zone: str | None = None,
        layer: MemoryLayer | None = None,
        subject_id: str | None = None,
    ) -> list[MemoryRecord]:
        result = list(self._by_id.values())
        if venture:
            result = [r for r in result if r.venture == venture]
        if zone:
            result = [r for r in result if r.zone == zone]
        if layer:
            result = [r for r in result if r.layer == layer]
        if subject_id:
            result = [r for r in result if r.subject_id == subject_id]
        return result

    def forget_subject(self, subject_id: str) -> int:
        """RGPD right-to-erasure. Retourne le nb de records effacés."""
        victims = [r.id for r in self._by_id.values() if r.subject_id == subject_id]
        for rid in victims:
            rec = self._by_id.pop(rid)
            self._index[(rec.venture, rec.zone)].remove(rid)
        return len(victims)

    def export_subject(self, subject_id: str) -> list[dict[str, Any]]:
        """RGPD portability."""
        return [
            {
                "id": r.id,
                "layer": r.layer.value,
                "key": r.key,
                "value": r.value,
                "venture": r.venture,
                "zone": r.zone,
                "pii_level": r.pii_level,
                "created_at": r.created_at,
            }
            for r in self._by_id.values()
            if r.subject_id == subject_id
        ]

    def gc_expired(self, now: float | None = None) -> int:
        victims = [r.id for r in self._by_id.values() if r.expired(now)]
        for rid in victims:
            rec = self._by_id.pop(rid)
            self._index[(rec.venture, rec.zone)].remove(rid)
        return len(victims)
