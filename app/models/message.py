"""Modèles de données pour les messages et contacts."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MessageDirection(Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"


class ResponseStatus(Enum):
    PENDING = "pending"
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    IGNORED = "ignored"
    ERROR = "error"


class ResponseMode(Enum):
    DRAFT_ONLY = "draft_only"
    MANUAL_VALIDATION = "manual_validation"
    AUTO_REPLY = "auto_reply"


class ContactCategory(Enum):
    UNKNOWN = "unknown"
    CLIENT = "client"
    FRIEND = "friend"
    FAMILY = "family"
    WORK = "work"


@dataclass
class Contact:
    name: str
    category: ContactCategory = ContactCategory.UNKNOWN
    whitelisted: bool = False
    blacklisted: bool = False
    auto_reply_enabled: bool = False
    tone: str = "neutral"
    id: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class IncomingMessage:
    contact_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_group: bool = False
    group_name: Optional[str] = None
    message_hash: Optional[str] = None
    id: Optional[int] = None
    processed: bool = False


@dataclass
class GeneratedResponse:
    incoming_message_id: int
    contact_name: str
    original_message: str
    response_text: str
    status: ResponseStatus = ResponseStatus.DRAFT
    provider: str = "mock"
    timestamp: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    id: Optional[int] = None


@dataclass
class ActionLog:
    action: str
    details: str
    level: str = "INFO"
    timestamp: datetime = field(default_factory=datetime.now)
    id: Optional[int] = None
