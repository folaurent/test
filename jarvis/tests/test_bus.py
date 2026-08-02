import asyncio

import pytest

from jarvis.bus.bus import InMemoryBusBackend, MessageBus
from jarvis.bus.schema import BusMessage
from jarvis.core.config import Settings
from jarvis.core.scope import ScopeError, ScopeFilter


@pytest.fixture
def bus() -> MessageBus:
    scope = ScopeFilter.from_settings(Settings())
    return MessageBus(InMemoryBusBackend(), scope)


async def test_send_ok(bus):
    msg = BusMessage(
        from_agent="Jarvis",
        to_agent="Builder",
        kind="task.dispatch",
        venture="jonction",
        payload={"intent": "onboard new specialist"},
    )
    await bus.send(msg)  # pas d'exception


async def test_send_blocked_on_tag_sika(bus):
    msg = BusMessage(
        from_agent="X", to_agent="Y", kind="k", venture="sika", payload={}
    )
    with pytest.raises(ScopeError):
        await bus.send(msg)


async def test_send_blocked_on_payload_text(bus):
    msg = BusMessage(
        from_agent="X",
        to_agent="Y",
        kind="k",
        venture="jonction",
        payload={"intent": "fais un résumé sur Parex Lanko"},
    )
    with pytest.raises(ScopeError):
        await bus.send(msg)


async def test_subscription_receives_message():
    scope = ScopeFilter.from_settings(Settings())
    backend = InMemoryBusBackend()
    bus = MessageBus(backend, scope)

    received = []

    async def consumer():
        async for m in bus.subscribe_agent("Builder"):
            received.append(m)
            return

    task = asyncio.create_task(consumer())
    await asyncio.sleep(0.01)
    await bus.send(
        BusMessage(from_agent="Jarvis", to_agent="Builder", kind="ping",
                   venture="jonction", payload={})
    )
    await asyncio.wait_for(task, timeout=1)
    assert received and received[0].kind == "ping"
