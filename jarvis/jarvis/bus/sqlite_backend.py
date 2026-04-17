"""Bus backend SQLite. Polling simple, suffisant pour Phase 1.2."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from jarvis.bus.schema import BusEvent, BusMessage
from jarvis.storage.db import Database


class SqliteBusBackend:
    def __init__(self, db: Database, poll_interval: float = 0.05) -> None:
        self._db = db
        self._poll = poll_interval

    async def publish_message(self, msg: BusMessage) -> None:
        self._db.execute(
            """INSERT INTO bus_messages
               (trace_id, ts, from_agent, to_agent, kind, venture, zone, pii_level, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                msg.trace_id, msg.ts, msg.from_agent, msg.to_agent, msg.kind,
                msg.venture, msg.zone, msg.pii_level,
                json.dumps(msg.payload, ensure_ascii=False, default=str),
            ),
        )

    async def publish_event(self, evt: BusEvent) -> None:
        self._db.execute(
            """INSERT INTO bus_events
               (trace_id, ts, kind, source, venture, zone, payload_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                evt.trace_id, evt.ts, evt.kind, evt.source, evt.venture, evt.zone,
                json.dumps(evt.payload, ensure_ascii=False, default=str),
            ),
        )

    async def subscribe_agent(self, agent: str) -> AsyncIterator[BusMessage]:
        while True:
            row = self._db.fetchone(
                """SELECT * FROM bus_messages
                   WHERE to_agent=? AND delivered=0
                   ORDER BY id ASC LIMIT 1""",
                (agent,),
            )
            if row is None:
                await asyncio.sleep(self._poll)
                continue
            self._db.execute(
                "UPDATE bus_messages SET delivered=1 WHERE id=?", (row["id"],)
            )
            yield BusMessage(
                trace_id=row["trace_id"], ts=row["ts"],
                from_agent=row["from_agent"], to_agent=row["to_agent"],
                kind=row["kind"], venture=row["venture"], zone=row["zone"],
                pii_level=row["pii_level"] or "none",
                payload=json.loads(row["payload_json"]),
            )

    async def subscribe_events(self, kind: str | None = None) -> AsyncIterator[BusEvent]:
        last_id = 0
        while True:
            if kind:
                rows = self._db.fetchall(
                    "SELECT * FROM bus_events WHERE id>? AND kind=? ORDER BY id ASC LIMIT 50",
                    (last_id, kind),
                )
            else:
                rows = self._db.fetchall(
                    "SELECT * FROM bus_events WHERE id>? ORDER BY id ASC LIMIT 50",
                    (last_id,),
                )
            if not rows:
                await asyncio.sleep(self._poll)
                continue
            for row in rows:
                last_id = row["id"]
                yield BusEvent(
                    trace_id=row["trace_id"], ts=row["ts"], kind=row["kind"],
                    source=row["source"], venture=row["venture"], zone=row["zone"],
                    payload=json.loads(row["payload_json"]),
                )
