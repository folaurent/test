"""Audit trail exhaustif. Chaque action sensible y passe.

En Phase 1.1 : backend mémoire + JSONL fichier. En Phase 1.3 : miroir Supabase.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from threading import Lock
from typing import Any

_AUDIT_LOG_PATH = Path(os.getenv("JARVIS_AUDIT_PATH", "logs/audit.jsonl"))
_LOCK = Lock()


def audit(event: str, **fields: Any) -> str:
    """Log un évènement d'audit. Retourne le trace_id.

    Écrit en JSONL sur disque + miroir SQLite si dispo.
    """
    trace_id = fields.pop("trace_id", None) or str(uuid.uuid4())
    ts = time.time()
    record = {
        "trace_id": trace_id,
        "ts": ts,
        "event": event,
        **fields,
    }
    with _LOCK:
        _AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    try:
        from jarvis.storage.db import get_db

        db = get_db()
        db.execute(
            "INSERT INTO audit_log (trace_id, ts, event, fields_json) VALUES (?, ?, ?, ?)",
            (trace_id, ts, event, json.dumps(fields, ensure_ascii=False, default=str)),
        )
    except Exception:
        # Audit fichier reste la source de vérité minimale.
        pass
    return trace_id
