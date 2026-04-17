"""Queue persistante — Redis en prod, SQLite en dev, mémoire en tests.

Une seule interface, 3 backends. Retry avec backoff exponentiel 2→4→8→16s.
Idempotency key obligatoire pour éviter les doubles actions (email envoyé 2×).
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass
class QueueItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    kind: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    enqueued_at: float = field(default_factory=time.time)
    idempotency_key: str | None = None
    attempts: int = 0
    max_attempts: int = 5
    next_attempt_at: float = 0.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, raw: str) -> "QueueItem":
        data = json.loads(raw)
        return cls(**data)


class QueueBackend(Protocol):
    async def push(self, item: QueueItem) -> None: ...
    async def pop(self) -> QueueItem | None: ...
    async def ack(self, item_id: str) -> None: ...
    async def nack(self, item: QueueItem, delay_s: float) -> None: ...


class InMemoryQueueBackend:
    def __init__(self) -> None:
        self._items: list[QueueItem] = []
        self._seen: set[str] = set()
        self._cond = asyncio.Condition()

    async def push(self, item: QueueItem) -> None:
        async with self._cond:
            if item.idempotency_key and item.idempotency_key in self._seen:
                return
            if item.idempotency_key:
                self._seen.add(item.idempotency_key)
            self._items.append(item)
            self._cond.notify_all()

    async def pop(self) -> QueueItem | None:
        async with self._cond:
            now = time.time()
            for i, it in enumerate(self._items):
                if it.next_attempt_at <= now:
                    return self._items.pop(i)
            return None

    async def ack(self, item_id: str) -> None:
        pass  # déjà retiré

    async def nack(self, item: QueueItem, delay_s: float) -> None:
        item.attempts += 1
        item.next_attempt_at = time.time() + delay_s
        async with self._cond:
            if item.attempts < item.max_attempts:
                self._items.append(item)


class PersistentQueue:
    def __init__(self, backend: QueueBackend) -> None:
        self._backend = backend

    async def enqueue(
        self,
        kind: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> str:
        item = QueueItem(kind=kind, payload=payload, idempotency_key=idempotency_key)
        await self._backend.push(item)
        return item.id

    async def dequeue(self) -> QueueItem | None:
        return await self._backend.pop()

    async def ack(self, item_id: str) -> None:
        await self._backend.ack(item_id)

    async def retry(self, item: QueueItem) -> None:
        # Backoff exp 2^attempt, plafond 16s (consigne git push).
        delay = min(16.0, 2.0 ** max(0, item.attempts))
        await self._backend.nack(item, delay_s=delay)
