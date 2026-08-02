"""SQLite persistence. Swap vers Supabase plus tard via même interface.

Tables :
  bus_messages, bus_events         — bus
  queue_items                      — queue persistante
  memory_records                   — mémoire 4 couches
  audit_log                        — audit trail
  agents                           — registre spécialistes
  eval_runs                        — historique évals
  scope_violations                 — compteur périmètre
  voice_lint_blocks                — compteur voice
  builds                           — historique Builder
  campaigns, conversations         — CRM-lite
  rgpd_register, rgpd_requests     — RGPD
"""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

_LOCK = threading.Lock()
_DB_SINGLETON: "Database | None" = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS bus_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id TEXT NOT NULL,
  ts REAL NOT NULL,
  from_agent TEXT NOT NULL,
  to_agent TEXT NOT NULL,
  kind TEXT NOT NULL,
  venture TEXT,
  zone TEXT,
  pii_level TEXT,
  payload_json TEXT NOT NULL,
  delivered INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_bus_msg_to ON bus_messages(to_agent, delivered);
CREATE INDEX IF NOT EXISTS idx_bus_msg_trace ON bus_messages(trace_id);

CREATE TABLE IF NOT EXISTS bus_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id TEXT NOT NULL,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,
  source TEXT NOT NULL,
  venture TEXT,
  zone TEXT,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bus_evt_kind ON bus_events(kind, ts);

CREATE TABLE IF NOT EXISTS queue_items (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  enqueued_at REAL NOT NULL,
  idempotency_key TEXT UNIQUE,
  attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 5,
  next_attempt_at REAL NOT NULL DEFAULT 0,
  state TEXT NOT NULL DEFAULT 'pending'   -- pending | done | dead
);
CREATE INDEX IF NOT EXISTS idx_q_next ON queue_items(state, next_attempt_at);

CREATE TABLE IF NOT EXISTS memory_records (
  id TEXT PRIMARY KEY,
  layer TEXT NOT NULL,
  key TEXT NOT NULL,
  value_json TEXT NOT NULL,
  venture TEXT NOT NULL,
  zone TEXT NOT NULL DEFAULT 'FR',
  pii_level TEXT NOT NULL DEFAULT 'none',
  source_trust REAL NOT NULL DEFAULT 0.5,
  retention_days INTEGER NOT NULL,
  subject_id TEXT,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mem_vz ON memory_records(venture, zone);
CREATE INDEX IF NOT EXISTS idx_mem_subj ON memory_records(subject_id);
CREATE INDEX IF NOT EXISTS idx_mem_layer ON memory_records(layer);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id TEXT,
  ts REAL NOT NULL,
  event TEXT NOT NULL,
  fields_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_log(event, ts);

CREATE TABLE IF NOT EXISTS agents (
  name TEXT PRIMARY KEY,
  venture TEXT NOT NULL,
  zone TEXT NOT NULL DEFAULT 'FR',
  human_facing INTEGER NOT NULL DEFAULT 0,
  autonomy INTEGER NOT NULL DEFAULT 0,
  charter_json TEXT NOT NULL,
  probation_until REAL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS eval_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent TEXT NOT NULL,
  ts REAL NOT NULL,
  passed INTEGER NOT NULL,
  total INTEGER NOT NULL,
  score REAL NOT NULL,
  report_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_eval_agent ON eval_runs(agent, ts);

CREATE TABLE IF NOT EXISTS scope_violations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  trace_id TEXT,
  source TEXT NOT NULL,
  term TEXT NOT NULL,
  agent TEXT,
  excerpt TEXT
);

CREATE TABLE IF NOT EXISTS voice_lint_blocks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  trace_id TEXT,
  agent TEXT,
  rules_json TEXT NOT NULL,
  score REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS builds (
  plan_id TEXT PRIMARY KEY,
  ts REAL NOT NULL,
  intent TEXT NOT NULL,
  summary TEXT,
  status TEXT NOT NULL,    -- drafted | approved | rejected | executed | failed
  plan_json TEXT NOT NULL,
  approved_by TEXT,
  executed_at REAL,
  cost_estimated_eur REAL,
  cost_real_eur REAL
);

CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  subject_id TEXT NOT NULL,             -- prospect/contact
  venture TEXT NOT NULL,
  zone TEXT NOT NULL,
  channel TEXT NOT NULL,                -- email | linkedin | whatsapp | telegram | sms
  state TEXT NOT NULL,                  -- cold | engaged | qualifying | hot | cold_opt_out | won | lost
  last_message_at REAL,
  messages_sent INTEGER NOT NULL DEFAULT 0,
  relances_count INTEGER NOT NULL DEFAULT 0,
  opt_out INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  memory_ref TEXT
);
CREATE INDEX IF NOT EXISTS idx_conv_state ON conversations(state, zone);
CREATE INDEX IF NOT EXISTS idx_conv_subject ON conversations(subject_id);

CREATE TABLE IF NOT EXISTS campaigns (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  venture TEXT NOT NULL,
  zone TEXT NOT NULL,
  status TEXT NOT NULL,                 -- drafted | approved | live | paused | done
  created_at REAL NOT NULL,
  plan_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rgpd_register (
  id TEXT PRIMARY KEY,
  record_json TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS rgpd_requests (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  subject_id TEXT NOT NULL,
  action TEXT NOT NULL,     -- forget | export | rectify
  records_affected INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL       -- done | partial | failed
);
"""


class Database:
    def __init__(self, path: str | Path = "data/jarvis.sqlite") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            self._path,
            check_same_thread=False,
            isolation_level=None,  # autocommit
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._conn.execute("PRAGMA synchronous=NORMAL;")
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, params)

    def executemany(self, sql: str, params_seq) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.executemany(sql, params_seq)

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, params).fetchall())

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(sql, params).fetchone()

    def close(self) -> None:
        self._conn.close()


def get_db(path: str | Path | None = None) -> Database:
    global _DB_SINGLETON
    with _LOCK:
        if _DB_SINGLETON is None or path is not None:
            _DB_SINGLETON = Database(path or "data/jarvis.sqlite")
        return _DB_SINGLETON


def reset_db_for_tests() -> None:
    global _DB_SINGLETON
    with _LOCK:
        if _DB_SINGLETON is not None:
            _DB_SINGLETON.close()
        _DB_SINGLETON = None
