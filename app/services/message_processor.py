"""Service principal de traitement des messages.

Orchestre le flux complet:
1. Détection de nouveaux messages
2. Évaluation des règles
3. Génération de réponse IA
4. Gestion du cycle de vie de la réponse
"""

import threading
import time
from datetime import datetime
from typing import Callable, Optional

from app.ai.base_provider import AIRequest, BaseAIProvider
from app.ai.provider_factory import AIProviderFactory
from app.automation.whatsapp_controller import WhatsAppController
from app.models.message import (
    ActionLog,
    GeneratedResponse,
    IncomingMessage,
    ResponseMode,
    ResponseStatus,
)
from app.services.rules_engine import RulesEngine
from app.storage.database import Database
from app.utils.hashing import compute_message_hash
from app.utils.logger import app_logger

logger = app_logger


class MessageProcessor:
    """Processeur principal de messages WhatsApp."""

    def __init__(
        self,
        db: Database,
        whatsapp: WhatsAppController,
        rules_engine: RulesEngine,
        ai_provider: BaseAIProvider,
        system_prompt: str = "",
        response_delay: int = 5,
        poll_interval: int = 3,
        on_new_message: Optional[Callable] = None,
        on_response_ready: Optional[Callable] = None,
        on_status_change: Optional[Callable] = None,
        on_alert: Optional[Callable] = None,
    ):
        self.db = db
        self.whatsapp = whatsapp
        self.rules_engine = rules_engine
        self.ai_provider = ai_provider
        self.system_prompt = system_prompt
        self.response_delay = response_delay
        self.poll_interval = poll_interval

        # Callbacks UI
        self.on_new_message = on_new_message
        self.on_response_ready = on_response_ready
        self.on_status_change = on_status_change
        self.on_alert = on_alert

        # État
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    def start(self):
        """Démarre la surveillance des messages."""
        if self._running:
            logger.warning("Le processeur est déjà en cours d'exécution")
            return

        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Surveillance des messages démarrée")
        self._log_action("START", "Surveillance démarrée")
        self._notify_status("running")

    def stop(self):
        """Arrête la surveillance des messages."""
        self._running = False
        self._paused = False
        if self._thread:
            self._thread.join(timeout=10)
            self._thread = None
        logger.info("Surveillance des messages arrêtée")
        self._log_action("STOP", "Surveillance arrêtée")
        self._notify_status("stopped")

    def pause(self):
        """Met en pause la surveillance."""
        self._paused = True
        logger.info("Surveillance en pause")
        self._log_action("PAUSE", "Surveillance en pause")
        self._notify_status("paused")

    def resume(self):
        """Reprend la surveillance."""
        self._paused = False
        logger.info("Surveillance reprise")
        self._log_action("RESUME", "Surveillance reprise")
        self._notify_status("running")

    def emergency_stop(self):
        """Arrêt d'urgence immédiat."""
        logger.warning("ARRÊT D'URGENCE activé")
        self._running = False
        self._paused = False
        self._log_action("EMERGENCY_STOP", "Arrêt d'urgence activé", level="WARNING")
        self._notify_status("emergency_stopped")

    def change_ai_provider(self, provider_name: str, api_key: str = None, model: str = None):
        """Change le provider IA à chaud."""
        self.ai_provider = AIProviderFactory.create(provider_name, api_key, model)
        logger.info("Provider IA changé: %s", provider_name)
        self._log_action("PROVIDER_CHANGE", f"Provider changé vers: {provider_name}")

    def approve_and_send(self, response_id: int) -> bool:
        """Approuve et envoie une réponse en attente."""
        responses = self.db.get_pending_responses()
        target = None
        for r in responses:
            if r.id == response_id:
                target = r
                break

        if not target:
            logger.warning("Réponse #%d non trouvée", response_id)
            return False

        return self._send_response(target)

    def ignore_response(self, response_id: int):
        """Ignore une réponse proposée."""
        self.db.update_response_status(response_id, ResponseStatus.IGNORED)
        logger.info("Réponse #%d ignorée", response_id)
        self._log_action("IGNORE", f"Réponse #{response_id} ignorée")

    def retry_read(self, contact_name: str) -> Optional[IncomingMessage]:
        """Retente la lecture du dernier message d'un contact."""
        logger.info("Relecture du message pour: %s", contact_name)
        return self._read_and_process_message(contact_name)

    # --- Boucle principale ---

    def _run_loop(self):
        """Boucle principale de surveillance."""
        while self._running:
            if self._paused:
                time.sleep(1)
                continue

            try:
                self._poll_messages()
            except Exception as e:
                logger.error("Erreur dans la boucle de surveillance: %s", e)
                self._log_action("ERROR", f"Erreur surveillance: {e}", level="ERROR")

            time.sleep(self.poll_interval)

    def _poll_messages(self):
        """Vérifie les nouveaux messages."""
        # Vérifier la connexion WhatsApp
        if not self.whatsapp.is_connected:
            if not self.whatsapp.connect():
                return

        # Détecter les conversations non lues
        unread = self.whatsapp.detect_unread_conversations()
        if not unread:
            return

        for contact_name in unread:
            try:
                self._read_and_process_message(contact_name)
            except Exception as e:
                logger.error("Erreur traitement message de %s: %s", contact_name, e)

    def _read_and_process_message(self, contact_name: str) -> Optional[IncomingMessage]:
        """Lit et traite un message d'un contact."""
        # Ouvrir la conversation
        if not self.whatsapp.open_conversation(contact_name):
            logger.warning("Impossible d'ouvrir la conversation: %s", contact_name)
            return None

        # Lire le dernier message
        detected = self.whatsapp.read_last_message(contact_name)
        if not detected:
            logger.warning("Aucun message lu pour: %s", contact_name)
            return None

        # Vérifier le contenu
        if not detected.content or not detected.content.strip():
            logger.warning("Message vide détecté pour: %s", contact_name)
            return None

        # Anti-doublon via hash
        msg_hash = compute_message_hash(detected.contact_name, detected.content)
        if self.db.message_exists(msg_hash):
            logger.debug("Message déjà traité (hash: %s)", msg_hash[:16])
            return None

        # Sauvegarder le message entrant
        incoming = IncomingMessage(
            contact_name=detected.contact_name,
            content=detected.content,
            is_group=detected.is_group,
            group_name=detected.group_name,
            message_hash=msg_hash,
        )
        msg_id = self.db.save_incoming_message(incoming)
        incoming.id = msg_id

        logger.info(
            "Nouveau message de %s: %s",
            detected.contact_name,
            detected.content[:80],
        )

        # Notifier l'UI
        if self.on_new_message:
            self.on_new_message(incoming)

        # Évaluer les règles
        contact = self.db.get_contact(detected.contact_name)
        rule_result = self.rules_engine.evaluate(
            detected.contact_name, detected.content, contact
        )

        if not rule_result.should_process:
            logger.info("Message ignoré: %s", rule_result.reason)
            self.db.mark_message_processed(msg_id)
            self._log_action("SKIP", f"{detected.contact_name}: {rule_result.reason}")
            return incoming

        # Alerte si nécessaire
        if rule_result.alert and self.on_alert:
            self.on_alert(detected.contact_name, detected.content)

        # Générer la réponse
        if rule_result.use_template and rule_result.template_response:
            response_text = rule_result.template_response
            provider_name = "template"
        else:
            ai_request = AIRequest(
                message=detected.content,
                contact_name=detected.contact_name,
                system_prompt=self.system_prompt,
                tone=rule_result.tone,
            )
            ai_response = self.ai_provider.generate_response(ai_request)

            if not ai_response.success:
                logger.error("Échec IA: %s", ai_response.error)
                self._log_action(
                    "AI_ERROR",
                    f"Échec génération pour {detected.contact_name}: {ai_response.error}",
                    level="ERROR",
                )
                return incoming

            response_text = ai_response.text
            provider_name = ai_response.provider

        # Déterminer le statut initial selon le mode
        if rule_result.response_mode == ResponseMode.AUTO_REPLY:
            initial_status = ResponseStatus.APPROVED
        elif rule_result.response_mode == ResponseMode.MANUAL_VALIDATION:
            initial_status = ResponseStatus.DRAFT
        else:
            initial_status = ResponseStatus.DRAFT

        # Sauvegarder la réponse
        response = GeneratedResponse(
            incoming_message_id=msg_id,
            contact_name=detected.contact_name,
            original_message=detected.content,
            response_text=response_text,
            status=initial_status,
            provider=provider_name,
        )
        resp_id = self.db.save_response(response)
        response.id = resp_id

        self.db.mark_message_processed(msg_id)

        logger.info(
            "Réponse générée pour %s [%s]: %s",
            detected.contact_name,
            initial_status.value,
            response_text[:80],
        )
        self._log_action(
            "RESPONSE_GENERATED",
            f"{detected.contact_name}: {response_text[:100]}",
        )

        # Notifier l'UI
        if self.on_response_ready:
            self.on_response_ready(response)

        # Auto-envoi si approuvé
        if initial_status == ResponseStatus.APPROVED:
            time.sleep(self.response_delay)
            self._send_response(response)

        return incoming

    def _send_response(self, response: GeneratedResponse) -> bool:
        """Envoie une réponse via WhatsApp."""
        # Anti-doublon d'envoi
        if response.status == ResponseStatus.SENT:
            logger.warning("Réponse #%d déjà envoyée", response.id)
            return False

        # Ouvrir la conversation
        if not self.whatsapp.open_conversation(response.contact_name):
            logger.error(
                "Impossible d'ouvrir la conversation pour envoi: %s",
                response.contact_name,
            )
            self.db.update_response_status(response.id, ResponseStatus.ERROR)
            return False

        # Délai de sécurité
        time.sleep(max(1, self.response_delay))

        # Envoyer
        success = self.whatsapp.send_message(response.response_text)
        if success:
            self.db.update_response_status(
                response.id, ResponseStatus.SENT, sent_at=datetime.now()
            )
            logger.info("Réponse envoyée à %s", response.contact_name)
            self._log_action(
                "SENT",
                f"Réponse envoyée à {response.contact_name}: {response.response_text[:80]}",
            )
            return True
        else:
            self.db.update_response_status(response.id, ResponseStatus.ERROR)
            logger.error("Échec envoi à %s", response.contact_name)
            self._log_action(
                "SEND_ERROR",
                f"Échec envoi à {response.contact_name}",
                level="ERROR",
            )
            return False

    def _log_action(self, action: str, details: str, level: str = "INFO"):
        """Enregistre une action dans la base de données."""
        try:
            self.db.save_log(ActionLog(action=action, details=details, level=level))
        except Exception as e:
            logger.error("Erreur log action: %s", e)

    def _notify_status(self, status: str):
        """Notifie l'UI d'un changement de statut."""
        if self.on_status_change:
            self.on_status_change(status)
