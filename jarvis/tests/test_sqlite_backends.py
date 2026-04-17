import pytest

from jarvis.bus.bus import MessageBus
from jarvis.bus.schema import BusMessage
from jarvis.bus.sqlite_backend import SqliteBusBackend
from jarvis.core.config import Settings
from jarvis.core.scope import ScopeFilter
from jarvis.memory.memory import MemoryLayer, MemoryRecord
from jarvis.memory.sqlite_backend import SqliteMemory
from jarvis.queue.queue import PersistentQueue
from jarvis.queue.sqlite_backend import SqliteQueueBackend
from jarvis.storage.db import Database


@pytest.fixture
def db(tmp_path) -> Database:
    return Database(tmp_path / "test.sqlite")


async def test_sqlite_bus_message_roundtrip(db):
    scope = ScopeFilter.from_settings(Settings())
    bus = MessageBus(SqliteBusBackend(db, poll_interval=0.01), scope)
    msg = BusMessage(
        from_agent="A", to_agent="B", kind="k", venture="jonction",
        payload={"hello": "world"},
    )
    await bus.send(msg)
    row = db.fetchone("SELECT * FROM bus_messages WHERE to_agent='B'")
    assert row is not None
    assert row["venture"] == "jonction"


async def test_sqlite_queue_idempotency(db):
    q = PersistentQueue(SqliteQueueBackend(db))
    await q.enqueue("k", {"a": 1}, idempotency_key="iso1")
    await q.enqueue("k", {"a": 1}, idempotency_key="iso1")
    row = db.fetchone("SELECT COUNT(*) as n FROM queue_items")
    assert row["n"] == 1


async def test_sqlite_queue_retry_persists_state(db):
    q = PersistentQueue(SqliteQueueBackend(db))
    await q.enqueue("k", {})
    item = await q.dequeue()
    assert item is not None
    await q.retry(item)
    row = db.fetchone("SELECT state, attempts FROM queue_items WHERE id=?", (item.id,))
    assert row["attempts"] == 1
    assert row["state"] == "pending"


def test_sqlite_memory_crud_and_forget(db):
    m = SqliteMemory(db)
    rid = m.write(MemoryRecord(
        key="k", value={"x": 1}, venture="jonction", subject_id="p42"
    ))
    assert m.read(rid) is not None
    assert len(m.query(subject_id="p42")) == 1
    n = m.forget_subject("p42")
    assert n == 1
    assert not m.query(subject_id="p42")


def test_sqlite_memory_expired_gc(db):
    m = SqliteMemory(db)
    m.write(MemoryRecord(
        key="k", value=1, venture="jonction",
        layer=MemoryLayer.EPISODIC, retention_days=1, created_at=0.0,
    ))
    n = m.gc_expired(now=10 * 86400)
    assert n == 1
