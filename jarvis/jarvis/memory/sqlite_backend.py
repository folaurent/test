"""Mémoire persistée SQLite. L3 semantic = JSON pour l'instant, pgvector après."""
from __future__ import annotations

import json
import time
from typing import Any

from jarvis.memory.memory import Memory, MemoryLayer, MemoryRecord, _DEFAULT_RETENTION  # type: ignore
from jarvis.storage.db import Database


class SqliteMemory(Memory):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self._db = db

    def write(self, record: MemoryRecord) -> str:
        if not record.venture:
            raise ValueError("memory.write: tag 'venture' obligatoire")
        if record.retention_days == 0 and record.layer != MemoryLayer.WORKING:
            record.retention_days = _DEFAULT_RETENTION[record.layer]
        self._db.execute(
            """INSERT OR REPLACE INTO memory_records
               (id, layer, key, value_json, venture, zone, pii_level,
                source_trust, retention_days, subject_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.id, record.layer.value, record.key,
                json.dumps(record.value, ensure_ascii=False, default=str),
                record.venture, record.zone, record.pii_level,
                record.source_trust, record.retention_days,
                record.subject_id, record.created_at,
            ),
        )
        return record.id

    def _row_to_record(self, row: Any) -> MemoryRecord:
        return MemoryRecord(
            id=row["id"],
            layer=MemoryLayer(row["layer"]),
            key=row["key"],
            value=json.loads(row["value_json"]),
            venture=row["venture"],
            zone=row["zone"],
            pii_level=row["pii_level"],
            source_trust=row["source_trust"],
            retention_days=row["retention_days"],
            subject_id=row["subject_id"],
            created_at=row["created_at"],
        )

    def read(self, rid: str) -> MemoryRecord | None:
        row = self._db.fetchone("SELECT * FROM memory_records WHERE id=?", (rid,))
        return self._row_to_record(row) if row else None

    def query(self, **filters) -> list[MemoryRecord]:
        where = []
        params: list[Any] = []
        if filters.get("venture"):
            where.append("venture=?"); params.append(filters["venture"])
        if filters.get("zone"):
            where.append("zone=?"); params.append(filters["zone"])
        if filters.get("layer"):
            where.append("layer=?")
            layer = filters["layer"]
            params.append(layer.value if isinstance(layer, MemoryLayer) else layer)
        if filters.get("subject_id"):
            where.append("subject_id=?"); params.append(filters["subject_id"])
        sql = "SELECT * FROM memory_records"
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = self._db.fetchall(sql, tuple(params))
        return [self._row_to_record(r) for r in rows]

    def forget_subject(self, subject_id: str) -> int:
        rows = self._db.fetchall(
            "SELECT id FROM memory_records WHERE subject_id=?", (subject_id,)
        )
        self._db.execute(
            "DELETE FROM memory_records WHERE subject_id=?", (subject_id,)
        )
        return len(rows)

    def export_subject(self, subject_id: str) -> list[dict[str, Any]]:
        rows = self._db.fetchall(
            "SELECT * FROM memory_records WHERE subject_id=?", (subject_id,)
        )
        return [
            {
                "id": r["id"], "layer": r["layer"], "key": r["key"],
                "value": json.loads(r["value_json"]),
                "venture": r["venture"], "zone": r["zone"],
                "pii_level": r["pii_level"], "created_at": r["created_at"],
            }
            for r in rows
        ]

    def gc_expired(self, now: float | None = None) -> int:
        now = now or time.time()
        rows = self._db.fetchall("SELECT id, layer, retention_days, created_at FROM memory_records")
        victims = []
        for r in rows:
            layer = MemoryLayer(r["layer"])
            if layer == MemoryLayer.WORKING:
                victims.append(r["id"])
            elif r["retention_days"] > 0 and (now - r["created_at"]) > r["retention_days"] * 86400:
                victims.append(r["id"])
        for rid in victims:
            self._db.execute("DELETE FROM memory_records WHERE id=?", (rid,))
        return len(victims)
