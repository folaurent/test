"""Couche de persistance SQLite pour l'application."""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.models.message import (
    ActionLog,
    Contact,
    ContactCategory,
    GeneratedResponse,
    IncomingMessage,
    ResponseStatus,
)
from app.utils.logger import app_logger

logger = app_logger


class Database:
    """Gestionnaire de base de données SQLite thread-safe."""

    def __init__(self, db_path: str = "data/assistant.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, "connection") or self._local.connection is None:
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA journal_mode=WAL")
        return self._local.connection

    @contextmanager
    def _cursor(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_db(self):
        with self._cursor() as cur:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT DEFAULT 'unknown',
                    whitelisted INTEGER DEFAULT 0,
                    blacklisted INTEGER DEFAULT 0,
                    auto_reply_enabled INTEGER DEFAULT 0,
                    tone TEXT DEFAULT 'neutral',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS incoming_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contact_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_group INTEGER DEFAULT 0,
                    group_name TEXT,
                    message_hash TEXT UNIQUE,
                    processed INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS generated_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    incoming_message_id INTEGER NOT NULL,
                    contact_name TEXT NOT NULL,
                    original_message TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    provider TEXT DEFAULT 'mock',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sent_at TIMESTAMP,
                    FOREIGN KEY (incoming_message_id) REFERENCES incoming_messages(id)
                );

                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    details TEXT,
                    level TEXT DEFAULT 'INFO',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_messages_hash ON incoming_messages(message_hash);
                CREATE INDEX IF NOT EXISTS idx_messages_processed ON incoming_messages(processed);
                CREATE INDEX IF NOT EXISTS idx_responses_status ON generated_responses(status);
                CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name);
            """)
        logger.info("Base de données initialisée: %s", self.db_path)

    # --- Contacts ---

    def upsert_contact(self, contact: Contact) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO contacts (name, category, whitelisted, blacklisted, auto_reply_enabled, tone)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                       category=excluded.category,
                       whitelisted=excluded.whitelisted,
                       blacklisted=excluded.blacklisted,
                       auto_reply_enabled=excluded.auto_reply_enabled,
                       tone=excluded.tone""",
                (
                    contact.name,
                    contact.category.value,
                    int(contact.whitelisted),
                    int(contact.blacklisted),
                    int(contact.auto_reply_enabled),
                    contact.tone,
                ),
            )
            return cur.lastrowid

    def get_contact(self, name: str) -> Optional[Contact]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM contacts WHERE name = ?", (name,))
            row = cur.fetchone()
            if row:
                return Contact(
                    id=row["id"],
                    name=row["name"],
                    category=ContactCategory(row["category"]),
                    whitelisted=bool(row["whitelisted"]),
                    blacklisted=bool(row["blacklisted"]),
                    auto_reply_enabled=bool(row["auto_reply_enabled"]),
                    tone=row["tone"],
                    created_at=row["created_at"],
                )
        return None

    def get_all_contacts(self) -> list[Contact]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM contacts ORDER BY name")
            return [
                Contact(
                    id=row["id"],
                    name=row["name"],
                    category=ContactCategory(row["category"]),
                    whitelisted=bool(row["whitelisted"]),
                    blacklisted=bool(row["blacklisted"]),
                    auto_reply_enabled=bool(row["auto_reply_enabled"]),
                    tone=row["tone"],
                    created_at=row["created_at"],
                )
                for row in cur.fetchall()
            ]

    # --- Messages entrants ---

    def message_exists(self, message_hash: str) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "SELECT 1 FROM incoming_messages WHERE message_hash = ?",
                (message_hash,),
            )
            return cur.fetchone() is not None

    def save_incoming_message(self, msg: IncomingMessage) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO incoming_messages
                   (contact_name, content, timestamp, is_group, group_name, message_hash, processed)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    msg.contact_name,
                    msg.content,
                    msg.timestamp.isoformat(),
                    int(msg.is_group),
                    msg.group_name,
                    msg.message_hash,
                    int(msg.processed),
                ),
            )
            return cur.lastrowid

    def mark_message_processed(self, message_id: int):
        with self._cursor() as cur:
            cur.execute(
                "UPDATE incoming_messages SET processed = 1 WHERE id = ?",
                (message_id,),
            )

    def get_recent_messages(self, limit: int = 50) -> list[IncomingMessage]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM incoming_messages ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [
                IncomingMessage(
                    id=row["id"],
                    contact_name=row["contact_name"],
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"])
                    if isinstance(row["timestamp"], str)
                    else row["timestamp"],
                    is_group=bool(row["is_group"]),
                    group_name=row["group_name"],
                    message_hash=row["message_hash"],
                    processed=bool(row["processed"]),
                )
                for row in cur.fetchall()
            ]

    # --- Réponses générées ---

    def save_response(self, resp: GeneratedResponse) -> int:
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO generated_responses
                   (incoming_message_id, contact_name, original_message, response_text, status, provider, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    resp.incoming_message_id,
                    resp.contact_name,
                    resp.original_message,
                    resp.response_text,
                    resp.status.value,
                    resp.provider,
                    resp.timestamp.isoformat(),
                ),
            )
            return cur.lastrowid

    def update_response_status(self, response_id: int, status: ResponseStatus, sent_at: Optional[datetime] = None):
        with self._cursor() as cur:
            if sent_at:
                cur.execute(
                    "UPDATE generated_responses SET status = ?, sent_at = ? WHERE id = ?",
                    (status.value, sent_at.isoformat(), response_id),
                )
            else:
                cur.execute(
                    "UPDATE generated_responses SET status = ? WHERE id = ?",
                    (status.value, response_id),
                )

    def get_pending_responses(self) -> list[GeneratedResponse]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM generated_responses WHERE status IN ('draft', 'approved') ORDER BY timestamp DESC"
            )
            return self._rows_to_responses(cur.fetchall())

    def get_recent_responses(self, limit: int = 50) -> list[GeneratedResponse]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM generated_responses ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return self._rows_to_responses(cur.fetchall())

    def response_exists_for_message(self, incoming_message_id: int) -> bool:
        with self._cursor() as cur:
            cur.execute(
                "SELECT 1 FROM generated_responses WHERE incoming_message_id = ?",
                (incoming_message_id,),
            )
            return cur.fetchone() is not None

    def _rows_to_responses(self, rows) -> list[GeneratedResponse]:
        return [
            GeneratedResponse(
                id=row["id"],
                incoming_message_id=row["incoming_message_id"],
                contact_name=row["contact_name"],
                original_message=row["original_message"],
                response_text=row["response_text"],
                status=ResponseStatus(row["status"]),
                provider=row["provider"],
                timestamp=datetime.fromisoformat(row["timestamp"])
                if isinstance(row["timestamp"], str)
                else row["timestamp"],
                sent_at=datetime.fromisoformat(row["sent_at"])
                if row["sent_at"]
                else None,
            )
            for row in rows
        ]

    # --- Logs ---

    def save_log(self, log: ActionLog):
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO action_logs (action, details, level, timestamp) VALUES (?, ?, ?, ?)",
                (log.action, log.details, log.level, log.timestamp.isoformat()),
            )

    def get_recent_logs(self, limit: int = 100) -> list[ActionLog]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT * FROM action_logs ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            )
            return [
                ActionLog(
                    id=row["id"],
                    action=row["action"],
                    details=row["details"],
                    level=row["level"],
                    timestamp=datetime.fromisoformat(row["timestamp"])
                    if isinstance(row["timestamp"], str)
                    else row["timestamp"],
                )
                for row in cur.fetchall()
            ]
