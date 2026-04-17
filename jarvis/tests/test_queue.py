import pytest

from jarvis.queue.queue import InMemoryQueueBackend, PersistentQueue


async def test_enqueue_dequeue():
    q = PersistentQueue(InMemoryQueueBackend())
    await q.enqueue("email.send", {"to": "a@b.c"})
    item = await q.dequeue()
    assert item is not None
    assert item.kind == "email.send"


async def test_idempotency_dedup():
    q = PersistentQueue(InMemoryQueueBackend())
    await q.enqueue("email.send", {"to": "a@b.c"}, idempotency_key="k1")
    await q.enqueue("email.send", {"to": "a@b.c"}, idempotency_key="k1")
    item1 = await q.dequeue()
    item2 = await q.dequeue()
    assert item1 is not None
    assert item2 is None  # déduplication


async def test_retry_backoff():
    q = PersistentQueue(InMemoryQueueBackend())
    await q.enqueue("email.send", {"to": "a@b.c"})
    item = await q.dequeue()
    assert item is not None
    item.attempts = 0
    await q.retry(item)
    # nack repush avec delay, item pas immédiatement dispo
    item2 = await q.dequeue()
    # avec backoff 2s, l'item ne revient pas tout de suite
    assert item2 is None
