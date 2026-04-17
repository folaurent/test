"""Queue backend SQLite avec idempotency + backoff persistants."""
from __future__ import annotations

import json
import time

from jarvis.queue.queue import QueueItem
from jarvis.storage.db import Database


class SqliteQueueBackend:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def push(self, item: QueueItem) -> None:
        if item.idempotency_key:
            existing = self._db.fetchone(
                "SELECT id FROM queue_items WHERE idempotency_key=?",
                (item.idempotency_key,),
            )
            if existing is not None:
                return
        self._db.execute(
            """INSERT INTO queue_items
               (id, kind, payload_json, enqueued_at, idempotency_key, attempts,
                max_attempts, next_attempt_at, state)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')""",
            (
                item.id, item.kind,
                json.dumps(item.payload, ensure_ascii=False, default=str),
                item.enqueued_at, item.idempotency_key, item.attempts,
                item.max_attempts, item.next_attempt_at,
            ),
        )

    async def pop(self) -> QueueItem | None:
        now = time.time()
        row = self._db.fetchone(
            """SELECT * FROM queue_items
               WHERE state='pending' AND next_attempt_at<=?
               ORDER BY enqueued_at ASC LIMIT 1""",
            (now,),
        )
        if row is None:
            return None
        self._db.execute(
            "UPDATE queue_items SET state='inflight' WHERE id=?", (row["id"],)
        )
        return QueueItem(
            id=row["id"], kind=row["kind"],
            payload=json.loads(row["payload_json"]),
            enqueued_at=row["enqueued_at"],
            idempotency_key=row["idempotency_key"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            next_attempt_at=row["next_attempt_at"],
        )

    async def ack(self, item_id: str) -> None:
        self._db.execute(
            "UPDATE queue_items SET state='done' WHERE id=?", (item_id,)
        )

    async def nack(self, item: QueueItem, delay_s: float) -> None:
        item.attempts += 1
        item.next_attempt_at = time.time() + delay_s
        if item.attempts >= item.max_attempts:
            self._db.execute(
                "UPDATE queue_items SET state='dead', attempts=? WHERE id=?",
                (item.attempts, item.id),
            )
        else:
            self._db.execute(
                """UPDATE queue_items
                   SET state='pending', attempts=?, next_attempt_at=?
                   WHERE id=?""",
                (item.attempts, item.next_attempt_at, item.id),
            )
