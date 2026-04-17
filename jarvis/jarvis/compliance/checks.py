"""Compliance — check-list bloquante par zone avant chaque campagne outreach.

Couvre :
  FR/UE : RGPD, LCEN, base légale (intérêt légitime B2B ou consentement)
  DE/AT/CH : UWG (DE), DSG (CH) — consentement explicite quasi-requis en B2C,
            B2B intérêt légitime mais plus strict
  UK : PECR + GDPR UK
  US : CAN-SPAM + lois état (CCPA, SHIELD, etc.)
  CA : CASL (consentement opt-in requis)
  APAC : patchwork

Chaque campagne : passer `ComplianceAgent.run(zone, campaign)`. Si résultat
n'est pas all_green → refus jusqu'à résolution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jarvis.rgpd.register import ProcessingRecord


@dataclass
class ComplianceCheck:
    id: str
    label: str
    required: bool = True
    passed: bool = False
    detail: str = ""


@dataclass
class ComplianceResult:
    zone: str
    checks: list[ComplianceCheck]

    @property
    def all_green(self) -> bool:
        return all(c.passed or not c.required for c in self.checks)

    @property
    def failed(self) -> list[ComplianceCheck]:
        return [c for c in self.checks if c.required and not c.passed]

    def as_telegram_card(self) -> str:
        lines = [f"✅ Compliance `{self.zone}`" if self.all_green else f"⛔ Compliance `{self.zone}`"]
        for c in self.checks:
            icon = "✅" if c.passed else ("⛔" if c.required else "⚠️")
            lines.append(f"{icon} {c.label}" + (f" — {c.detail}" if c.detail else ""))
        return "\n".join(lines)


def _common_checks(campaign: dict[str, Any]) -> list[ComplianceCheck]:
    return [
        ComplianceCheck(
            id="legal_basis_declared",
            label="Base légale déclarée (intérêt légitime / consentement)",
            passed=bool(campaign.get("legal_basis")),
        ),
        ComplianceCheck(
            id="art30_registered",
            label="Registre article 30 à jour pour ce traitement",
            passed=bool(campaign.get("art30_id")),
        ),
        ComplianceCheck(
            id="opt_out_link",
            label="Lien opt-out fonctionnel sur chaque message",
            passed=bool(campaign.get("opt_out_link")),
        ),
        ComplianceCheck(
            id="sender_identity",
            label="Identification expéditeur + adresse physique (CAN-SPAM/LCEN)",
            passed=bool(campaign.get("sender_identity")),
        ),
        ComplianceCheck(
            id="frequency_cap",
            label="Frequency cap configuré (max 2 relances, break-up)",
            passed=bool(campaign.get("frequency_cap")),
        ),
        ComplianceCheck(
            id="send_hours_local",
            label="Heures d'envoi locales 8h-18h, jamais WE/férié",
            passed=bool(campaign.get("send_hours_local")),
        ),
        ComplianceCheck(
            id="dpa_providers",
            label="DPA signés avec tous les providers (Anthropic ZDR, email, storage)",
            passed=bool(campaign.get("dpa_providers")),
        ),
    ]


_ZONE_EXTRA: dict[str, list[dict[str, Any]]] = {
    "DACH": [
        {"id": "dach_b2b_check", "label": "UWG §7 respecté (B2B intérêt légitime doc.)", "required": True},
        {"id": "dach_impressum", "label": "Mentions légales Impressum complètes", "required": True},
    ],
    "UK": [
        {"id": "uk_pecr", "label": "PECR : opt-in B2C, soft opt-in B2B documenté", "required": True},
    ],
    "US": [
        {"id": "us_can_spam", "label": "CAN-SPAM : opt-out 10j, header truthful, subject honnête", "required": True},
        {"id": "us_state_check", "label": "Lois état destinataire vérifiées (CCPA, etc.)", "required": True},
    ],
    "CA": [
        {"id": "ca_casl", "label": "CASL : consentement explicite opt-in OBLIGATOIRE", "required": True},
    ],
    "FR": [
        {"id": "fr_lcen", "label": "LCEN : mention commerciale + identifiant expéditeur clair", "required": True},
        {"id": "fr_b2b_legitimate", "label": "Intérêt légitime B2B documenté (CNIL)", "required": True},
    ],
}


class ComplianceAgent:
    """Stateless. Check-list déterministe, Opus 4.7 en renfort pour revue."""

    def run(self, zone: str, campaign: dict[str, Any]) -> ComplianceResult:
        zone_u = zone.upper()
        checks = _common_checks(campaign)
        for extra in _ZONE_EXTRA.get(zone_u, []):
            checks.append(
                ComplianceCheck(
                    id=extra["id"],
                    label=extra["label"],
                    required=extra.get("required", True),
                    passed=bool(campaign.get(extra["id"])),
                )
            )
        return ComplianceResult(zone=zone_u, checks=checks)

    def blocker_reasons(self, result: ComplianceResult) -> list[str]:
        return [c.id for c in result.failed]

    def suggest_record(self, zone: str, campaign: dict[str, Any]) -> ProcessingRecord:
        return ProcessingRecord(
            id=campaign.get("id", "unknown"),
            purpose=campaign.get("purpose", "outreach B2B"),
            data_categories=campaign.get(
                "data_categories", ["nom", "email", "entreprise", "secteur", "signaux_pro"]
            ),
            data_subjects=campaign.get("data_subjects", [f"prospects_b2b_{zone.lower()}"]),
            recipients=campaign.get(
                "recipients", ["anthropic(ZDR)", "supabase_eu", "resend"]
            ),
            retention_days=campaign.get("retention_days", 365),
            legal_basis=campaign.get("legal_basis", "legitimate_interests"),
            zone=zone,
            cross_border_transfers=campaign.get("cross_border_transfers", []),
            dpa_signed=bool(campaign.get("dpa_providers")),
        )
