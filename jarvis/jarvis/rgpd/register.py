"""Registre article 30 RGPD — liste des traitements.

Chaque nouvelle activité de traitement (outreach campagne, ingestion de
données prospect, etc.) DOIT être déclarée ici avant d'être exécutée.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

import yaml

LegalBasis = Literal[
    "consent", "contract", "legal_obligation", "vital_interests",
    "public_task", "legitimate_interests",
]


@dataclass
class ProcessingRecord:
    id: str
    purpose: str
    data_categories: list[str]  # ex ["nom", "email", "secteur", "signaux_pro"]
    data_subjects: list[str]    # ex ["prospects_b2b_fr"]
    recipients: list[str]       # ex ["anthropic(ZDR)", "supabase_eu"]
    retention_days: int
    legal_basis: LegalBasis
    zone: str
    security_measures: list[str] = field(
        default_factory=lambda: ["encryption_rest", "encryption_transit", "audit_trail"]
    )
    cross_border_transfers: list[str] = field(default_factory=list)
    dpa_signed: bool = False
    created_at: float = field(default_factory=time.time)


class Art30Register:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or Path("config/rgpd_register.yml")
        self._records: dict[str, ProcessingRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        data = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        for rid, fields in data.items():
            self._records[rid] = ProcessingRecord(id=rid, **fields)

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        out = {
            r.id: {k: v for k, v in asdict(r).items() if k != "id"}
            for r in self._records.values()
        }
        self._path.write_text(
            yaml.safe_dump(out, allow_unicode=True, sort_keys=True),
            encoding="utf-8",
        )

    def register(self, record: ProcessingRecord) -> None:
        if not record.dpa_signed and "anthropic" in " ".join(record.recipients).lower():
            # DPA Anthropic doit être signé avant traitement PII
            raise ValueError(
                f"register: DPA Anthropic non signé pour traitement {record.id}"
            )
        self._records[record.id] = record
        self.save()

    def list(self) -> list[ProcessingRecord]:
        return list(self._records.values())

    def get(self, rid: str) -> ProcessingRecord | None:
        return self._records.get(rid)
