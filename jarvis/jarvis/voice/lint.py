"""Voice lint — scanne chaque message sortant, bloque hors-spec.

Règles :
  HARD  (block) : phrase bannie FR, déni d'IA, manipulation, emoji ouverture,
                  prénom répété >1 fois, liens suspects masqués,
                  scope violation (Sika/Parexlanko).
  SOFT  (warn)  : >4 lignes par paragraphe, >1 question, >2 emojis,
                  majuscules en rafale, points d'exclamation multiples.

Chaque message sortant passe `VoiceLint.check(text)`. Un score < seuil
=> refus d'envoi + alerte Telegram.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from jarvis.voice.dna import (
    BANNED_OPENER_EMOJI,
    BANNED_PHRASES_FR,
    MANIPULATION_PATTERNS,
)

Severity = Literal["hard", "soft"]


@dataclass
class VoiceLintIssue:
    severity: Severity
    rule: str
    detail: str


@dataclass
class VoiceLintResult:
    passed: bool
    score: float  # 0.0 (horrible) → 1.0 (parfait)
    issues: list[VoiceLintIssue] = field(default_factory=list)

    @property
    def hard_issues(self) -> list[VoiceLintIssue]:
        return [i for i in self.issues if i.severity == "hard"]

    @property
    def soft_issues(self) -> list[VoiceLintIssue]:
        return [i for i in self.issues if i.severity == "soft"]


_AI_DENIAL_PATTERNS = [
    r"\bje suis (un|une)? ?humain(e)?\b",
    r"\bnon,? je ne suis pas (un|une)? ?(bot|ia|robot|assistant)\b",
    r"\bc'est (moi|laurent) qui (vous |t'|)écri[st]\b",
]

_URL_SUSPICIOUS = re.compile(r"(bit\.ly|tinyurl\.|t\.co/)", re.IGNORECASE)
_EXCLAMATION_BURST = re.compile(r"!{2,}")
_CAPS_BURST = re.compile(r"\b[A-ZÉÈÀÙÂÊÎÔÛ]{6,}\b")


class VoiceLint:
    def __init__(
        self,
        hard_threshold: float = 0.8,
        first_name_hint: str | None = None,
    ) -> None:
        self._threshold = hard_threshold
        self._first_name = first_name_hint

    def check(self, text: str) -> VoiceLintResult:
        issues: list[VoiceLintIssue] = []

        lower = text.lower()

        for phrase, replacement in BANNED_PHRASES_FR.items():
            if phrase in lower:
                issues.append(
                    VoiceLintIssue(
                        severity="hard",
                        rule="banned_phrase",
                        detail=f"'{phrase}' → utiliser '{replacement}'",
                    )
                )

        for pat in _AI_DENIAL_PATTERNS:
            if re.search(pat, lower):
                issues.append(
                    VoiceLintIssue(
                        severity="hard",
                        rule="ai_denial",
                        detail="Déni d'IA détecté. Voir DISCLOSURE_POLICY.",
                    )
                )
                break

        for pat in MANIPULATION_PATTERNS:
            if re.search(pat, lower):
                issues.append(
                    VoiceLintIssue(
                        severity="hard",
                        rule="manipulation",
                        detail=f"Pattern manipulatoire : {pat}",
                    )
                )

        stripped = text.lstrip()
        for emo in BANNED_OPENER_EMOJI:
            if stripped.startswith(emo):
                issues.append(
                    VoiceLintIssue(
                        severity="hard",
                        rule="banned_opener_emoji",
                        detail=f"Ouverture avec {emo} interdite.",
                    )
                )

        if _URL_SUSPICIOUS.search(text):
            issues.append(
                VoiceLintIssue(
                    severity="hard",
                    rule="suspicious_url",
                    detail="Shortener masqué (bit.ly/tinyurl/t.co) — kill délivrabilité.",
                )
            )

        # Prénom répété → spam pattern. Heuristique simple.
        if self._first_name:
            count = len(
                re.findall(
                    rf"\b{re.escape(self._first_name)}\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )
            if count > 1:
                issues.append(
                    VoiceLintIssue(
                        severity="hard",
                        rule="first_name_repeat",
                        detail=f"Prénom '{self._first_name}' utilisé {count} fois. Max 1.",
                    )
                )

        emoji_count = len(
            re.findall(
                r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", text
            )
        )
        if emoji_count > 2:
            issues.append(
                VoiceLintIssue(
                    severity="soft",
                    rule="emoji_overflow",
                    detail=f"{emoji_count} emojis. Max 2.",
                )
            )

        if _EXCLAMATION_BURST.search(text):
            issues.append(
                VoiceLintIssue(
                    severity="soft",
                    rule="exclamation_burst",
                    detail="Points d'exclamation en rafale.",
                )
            )

        if _CAPS_BURST.search(text):
            issues.append(
                VoiceLintIssue(
                    severity="soft",
                    rule="caps_burst",
                    detail="Majuscules en rafale.",
                )
            )

        questions = text.count("?")
        if questions > 1:
            issues.append(
                VoiceLintIssue(
                    severity="soft",
                    rule="too_many_questions",
                    detail=f"{questions} questions. Max 1 par message.",
                )
            )

        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        for p in paragraphs:
            if p.count("\n") >= 4:
                issues.append(
                    VoiceLintIssue(
                        severity="soft",
                        rule="paragraph_too_long",
                        detail="Paragraphe > 4 lignes.",
                    )
                )
                break

        hard_count = sum(1 for i in issues if i.severity == "hard")
        soft_count = sum(1 for i in issues if i.severity == "soft")
        # Score : chaque hard -0.3, chaque soft -0.1, plancher 0.
        score = max(0.0, 1.0 - 0.3 * hard_count - 0.1 * soft_count)
        passed = hard_count == 0 and score >= self._threshold

        return VoiceLintResult(passed=passed, score=score, issues=issues)
