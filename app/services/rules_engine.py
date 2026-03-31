"""Moteur de règles pour le traitement des messages.

Détermine comment un message doit être traité en fonction de règles configurables:
- Filtrage par whitelist/blacklist
- Adaptation du ton selon le contact
- Détection de mots-clés
- Détermination du mode de réponse
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.models.message import Contact, ContactCategory, ResponseMode
from app.utils.logger import app_logger

logger = app_logger


class MessagePriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class RuleResult:
    """Résultat de l'évaluation des règles pour un message."""
    should_process: bool
    response_mode: ResponseMode
    tone: str
    priority: MessagePriority
    reason: str
    alert: bool = False
    use_template: bool = False
    template_response: Optional[str] = None


class RulesEngine:
    """Moteur d'évaluation des règles pour le traitement des messages."""

    # Mots-clés urgents
    URGENT_KEYWORDS = [
        "urgent", "asap", "immédiat", "critique", "important",
        "deadline", "bloqué", "bloquant", "sos", "aide",
    ]

    # Mots-clés de question
    QUESTION_KEYWORDS = [
        "comment", "quand", "pourquoi", "est-ce que", "peux-tu",
        "pouvez-vous", "combien", "où", "quel", "quelle",
    ]

    # Réponses modèles (templates)
    TEMPLATES = {
        "absence": "Je suis actuellement indisponible. Je vous répondrai dès que possible.",
        "recu": "Bien reçu, merci !",
        "rappel": "Je note et je vous rappelle dès que possible.",
    }

    def __init__(
        self,
        whitelist: Optional[list[str]] = None,
        blacklist: Optional[list[str]] = None,
        default_mode: str = "draft_only",
        default_tone: str = "neutral",
        user_name: str = "",
    ):
        self.whitelist = [w.lower() for w in (whitelist or [])]
        self.blacklist = [b.lower() for b in (blacklist or [])]
        self.default_mode = ResponseMode(default_mode)
        self.default_tone = default_tone
        self.user_name = user_name.lower()
        self.templates_enabled = False
        self.active_template: Optional[str] = None

    def evaluate(
        self,
        contact_name: str,
        message_content: str,
        contact: Optional[Contact] = None,
    ) -> RuleResult:
        """Évalue les règles pour un message donné et retourne les instructions."""
        name_lower = contact_name.lower()

        # Anti-boucle: ignorer ses propres messages
        if self.user_name and name_lower == self.user_name:
            return RuleResult(
                should_process=False,
                response_mode=self.default_mode,
                tone=self.default_tone,
                priority=MessagePriority.LOW,
                reason="Message de l'utilisateur lui-même (anti-boucle)",
            )

        # Blacklist: ignorer les contacts blacklistés
        if name_lower in self.blacklist or (contact and contact.blacklisted):
            return RuleResult(
                should_process=False,
                response_mode=self.default_mode,
                tone=self.default_tone,
                priority=MessagePriority.LOW,
                reason=f"Contact blacklisté: {contact_name}",
            )

        # Message vide ou trop court
        content_stripped = message_content.strip()
        if not content_stripped or len(content_stripped) < 2:
            return RuleResult(
                should_process=False,
                response_mode=self.default_mode,
                tone=self.default_tone,
                priority=MessagePriority.LOW,
                reason="Message vide ou trop court",
            )

        # Déterminer le ton selon le contact
        tone = self._determine_tone(contact_name, contact)

        # Déterminer la priorité
        priority = self._determine_priority(content_stripped)

        # Déterminer le mode de réponse
        response_mode = self._determine_response_mode(contact_name, contact)

        # Vérifier si une alerte est nécessaire
        alert = priority == MessagePriority.URGENT

        # Vérifier si on utilise un template
        use_template = False
        template_response = None
        if self.templates_enabled and self.active_template:
            template_response = self.TEMPLATES.get(self.active_template)
            if template_response:
                use_template = True

        # Whitelist: si configurée, ne traiter que les contacts autorisés
        if self.whitelist:
            is_whitelisted = name_lower in self.whitelist or (
                contact and contact.whitelisted
            )
            if not is_whitelisted:
                return RuleResult(
                    should_process=False,
                    response_mode=self.default_mode,
                    tone=tone,
                    priority=priority,
                    reason=f"Contact non whitelisté: {contact_name}",
                    alert=alert,
                )

        return RuleResult(
            should_process=True,
            response_mode=response_mode,
            tone=tone,
            priority=priority,
            reason="Message accepté pour traitement",
            alert=alert,
            use_template=use_template,
            template_response=template_response,
        )

    def _determine_tone(self, contact_name: str, contact: Optional[Contact]) -> str:
        """Détermine le ton approprié selon le contact."""
        if contact:
            if contact.tone and contact.tone != "neutral":
                return contact.tone
            if contact.category == ContactCategory.CLIENT:
                return "professional"
            elif contact.category == ContactCategory.FRIEND:
                return "friendly"
            elif contact.category == ContactCategory.FAMILY:
                return "casual"
            elif contact.category == ContactCategory.WORK:
                return "professional"
        return self.default_tone

    def _determine_priority(self, content: str) -> MessagePriority:
        """Détermine la priorité du message."""
        content_lower = content.lower()

        if any(kw in content_lower for kw in self.URGENT_KEYWORDS):
            return MessagePriority.URGENT

        if "?" in content or any(kw in content_lower for kw in self.QUESTION_KEYWORDS):
            return MessagePriority.HIGH

        if len(content) < 20:
            return MessagePriority.LOW

        return MessagePriority.NORMAL

    def _determine_response_mode(
        self, contact_name: str, contact: Optional[Contact]
    ) -> ResponseMode:
        """Détermine le mode de réponse selon le contact."""
        # Auto-reply uniquement pour les contacts explicitement autorisés
        if contact and contact.auto_reply_enabled:
            return ResponseMode.AUTO_REPLY

        return self.default_mode

    def set_template_mode(self, template_name: Optional[str]):
        """Active/désactive le mode template."""
        if template_name and template_name in self.TEMPLATES:
            self.templates_enabled = True
            self.active_template = template_name
            logger.info("Mode template activé: %s", template_name)
        else:
            self.templates_enabled = False
            self.active_template = None
            logger.info("Mode template désactivé")

    def update_lists(self, whitelist: list[str], blacklist: list[str]):
        """Met à jour les listes blanches et noires."""
        self.whitelist = [w.lower() for w in whitelist]
        self.blacklist = [b.lower() for b in blacklist]
