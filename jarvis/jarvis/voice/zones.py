"""Profils de ton par zone. Point de départ, affiné par spécialistes zonaux."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ZoneCode = Literal[
    "FR", "DACH", "UK", "US", "CA", "IT", "ES", "PT",
    "BENELUX", "NORDICS", "JP", "KR", "CN",
]


@dataclass(frozen=True)
class Zone:
    code: ZoneCode
    formality: Literal["very_high", "high", "medium", "medium_low", "low"]
    addressing: str
    notes: str
    send_hours_local: tuple[int, int] = (8, 18)


_ZONES: dict[str, Zone] = {
    "FR": Zone(
        code="FR",
        formality="medium",
        addressing="Vouvoiement B2B par défaut, tutoiement si signal (créa/startup/ils tutoient en premier)",
        notes="Chaleur OK, pas trop familier avant signal clair.",
    ),
    "DACH": Zone(
        code="DACH",
        formality="high",
        addressing="Sie + Herr/Frau + Nachname",
        notes="Direct mais respectueux. Pas de blagues avant 3-4 échanges. Titre académique (Dr.) si dispo.",
    ),
    "UK": Zone(
        code="UK",
        formality="medium_low",
        addressing="First name + Hi",
        notes="Dry humour OK, self-deprecating accueilli, éviter enthousiasme américain.",
    ),
    "US": Zone(
        code="US",
        formality="low",
        addressing="First name immédiat + Hey",
        notes="Direct, énergie, active voice, CTA clair.",
    ),
    "CA": Zone(
        code="CA",
        formality="medium",
        addressing="First name, bilingue FR/EN selon préférence",
        notes="Plus poli que US. Éviter 'Hey' en ouverture pro.",
    ),
    "IT": Zone(
        code="IT",
        formality="medium",
        addressing="tu + prénom rapide, relation avant transaction",
        notes="Relationnel d'abord. 1-2 phrases de 'prise de contact' acceptables.",
    ),
    "ES": Zone(
        code="ES",
        formality="medium",
        addressing="tú + prénom rapide",
        notes="Relationnel avant transactionnel.",
    ),
    "PT": Zone(
        code="PT",
        formality="medium",
        addressing="tu + prénom rapide (PT-PT plus formel que BR)",
        notes="Relationnel avant transactionnel.",
    ),
    "BENELUX": Zone(
        code="BENELUX",
        formality="medium_low",
        addressing="First name, NL plus direct, BE plus nuancé",
        notes="Très pragmatiques, zéro fluff.",
    ),
    "NORDICS": Zone(
        code="NORDICS",
        formality="low",
        addressing="First name, tutoiement équivalent",
        notes="Direct, court, pas de small talk, sincérité > chaleur.",
    ),
    "JP": Zone(
        code="JP",
        formality="very_high",
        addressing="Nom+San, titres formels, très indirect",
        notes="Patience, jamais de hard sell, passer par présentations. Spécialiste natif quasi obligatoire.",
    ),
    "KR": Zone(
        code="KR",
        formality="very_high",
        addressing="Titres hiérarchiques, indirect",
        notes="Hiérarchie clé. Spécialiste natif requis.",
    ),
    "CN": Zone(
        code="CN",
        formality="very_high",
        addressing="Titre + nom de famille",
        notes="Canaux WeChat, relation longue. Spécialiste natif requis.",
    ),
}


def zone_profile(code: str) -> Zone:
    return _ZONES.get(code.upper(), _ZONES["FR"])


def all_zones() -> list[Zone]:
    return list(_ZONES.values())
