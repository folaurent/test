import pytest

from jarvis.memory.memory import Memory, MemoryLayer, MemoryRecord


def test_write_requires_venture():
    m = Memory()
    with pytest.raises(ValueError):
        m.write(MemoryRecord(key="k", value="v"))


def test_write_and_query_by_venture_zone():
    m = Memory()
    m.write(MemoryRecord(key="k1", value="v1", venture="jonction", zone="FR"))
    m.write(MemoryRecord(key="k2", value="v2", venture="jonction", zone="DACH"))
    m.write(MemoryRecord(key="k3", value="v3", venture="deco_pro", zone="FR"))
    assert len(m.query(venture="jonction")) == 2
    assert len(m.query(venture="jonction", zone="FR")) == 1
    assert len(m.query(venture="deco_pro")) == 1


def test_forget_subject_rgpd():
    m = Memory()
    m.write(MemoryRecord(key="x", value="y", venture="jonction", subject_id="prospect_42"))
    m.write(MemoryRecord(key="a", value="b", venture="jonction", subject_id="prospect_42"))
    m.write(MemoryRecord(key="c", value="d", venture="jonction", subject_id="other"))
    n = m.forget_subject("prospect_42")
    assert n == 2
    assert not m.query(subject_id="prospect_42")


def test_export_subject_returns_list():
    m = Memory()
    m.write(MemoryRecord(key="x", value="y", venture="jonction", subject_id="s1"))
    data = m.export_subject("s1")
    assert len(data) == 1
    assert data[0]["key"] == "x"


def test_gc_expired_purges_old():
    m = Memory()
    r = MemoryRecord(
        key="old", value="v", venture="jonction",
        layer=MemoryLayer.EPISODIC, retention_days=1, created_at=0.0,
    )
    m.write(r)
    n = m.gc_expired(now=10 * 86400)
    assert n == 1
