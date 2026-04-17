"""Message bus — interface. Implémentation Supabase branchée en Phase 1.3.

En Phase 1.1 : backend local async asyncio.Queue pour dev/tests.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Protocol

from jarvis.bus.schema import BusEvent, BusMessage
from jarvis.core.scope import ScopeError, ScopeFilter
from jarvis.observability.audit import audit
from jarvis.observability.logger import get_logger

logger = get_logger(__name__)

Handler = Callable[[BusMessage], Awaitable[None]]


class MessageBusBackend(Protocol):
    async def publish_message(self, msg: BusMessage) -> None: ...
    async def publish_event(self, evt: BusEvent) -> None: ...
    async def subscribe_agent(self, agent: str) -> AsyncIterator[BusMessage]: ...
    async def subscribe_events(self, kind: str | None = None) -> AsyncIterator[BusEvent]: ...


class InMemoryBusBackend:
    def __init__(self) -> None:
        self._agent_q: dict[str, asyncio.Queue[BusMessage]] = defaultdict(
            asyncio.Queue
        )
        self._event_subs: list[asyncio.Queue[BusEvent]] = []

    async def publish_message(self, msg: BusMessage) -> None:
        await self._agent_q[msg.to_agent].put(msg)

    async def publish_event(self, evt: BusEvent) -> None:
        for q in self._event_subs:
            await q.put(evt)

    async def subscribe_agent(self, agent: str) -> AsyncIterator[BusMessage]:
        q = self._agent_q[agent]
        while True:
            msg = await q.get()
            yield msg

    async def subscribe_events(self, kind: str | None = None) -> AsyncIterator[BusEvent]:
        q: asyncio.Queue[BusEvent] = asyncio.Queue()
        self._event_subs.append(q)
        try:
            while True:
                evt = await q.get()
                if kind is None or evt.kind == kind:
                    yield evt
        finally:
            self._event_subs.remove(q)


class MessageBus:
    """Façade bus + scope filter obligatoire."""

    def __init__(self, backend: MessageBusBackend, scope: ScopeFilter) -> None:
        self._backend = backend
        self._scope = scope

    async def send(self, msg: BusMessage) -> None:
        tag_v = self._scope.check_tag(msg.venture)
        if tag_v:
            audit(
                "scope_violation",
                trace_id=msg.trace_id,
                source="bus_tag",
                term=tag_v.term,
                agent=msg.to_agent,
            )
            raise ScopeError(f"scope_violation venture={tag_v.term}")

        text_blob = " ".join(
            str(v) for v in msg.payload.values() if isinstance(v, (str, int, float))
        )
        if text_blob:
            try:
                self._scope.assert_clean(text_blob, source="bus_payload")
            except ScopeError:
                audit(
                    "scope_violation",
                    trace_id=msg.trace_id,
                    source="bus_payload",
                    agent=msg.to_agent,
                )
                raise

        await self._backend.publish_message(msg)
        logger.info(
            "bus.send",
            trace_id=msg.trace_id,
            from_=msg.from_agent,
            to=msg.to_agent,
            kind=msg.kind,
        )

    async def emit(self, evt: BusEvent) -> None:
        await self._backend.publish_event(evt)
        logger.info("bus.event", kind=evt.kind, source=evt.source, trace_id=evt.trace_id)

    def subscribe_agent(self, agent: str) -> AsyncIterator[BusMessage]:
        return self._backend.subscribe_agent(agent)

    def subscribe_events(self, kind: str | None = None) -> AsyncIterator[BusEvent]:
        return self._backend.subscribe_events(kind)
