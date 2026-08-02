"""Contrôleur applicatif - fait le lien entre l'UI et la logique métier.

Sépare proprement l'UI de la logique pour faciliter les tests et la maintenance.
"""

from typing import Callable, Optional

from app.ai.provider_factory import AIProviderFactory
from app.automation.whatsapp_controller import WhatsAppController
from app.models.message import GeneratedResponse, IncomingMessage
from app.services.message_processor import MessageProcessor
from app.services.rules_engine import RulesEngine
from app.storage.database import Database
from app.utils.logger import app_logger
from config.settings import AppSettings

logger = app_logger


class AppController:
    """Contrôleur principal de l'application."""

    def __init__(self, settings: AppSettings):
        self.settings = settings

        # Initialisation des composants
        self.db = Database(settings.db_path)

        self.whatsapp = WhatsAppController(
            simulation_mode=settings.simulation_mode
        )

        self.rules_engine = RulesEngine(
            whitelist=settings.whitelist,
            blacklist=settings.blacklist,
            default_mode=settings.response_mode,
            default_tone=settings.default_tone,
            user_name=settings.whatsapp_user_name,
        )

        ai_provider = AIProviderFactory.create(
            settings.ai_provider,
            api_key=self._get_api_key(settings),
            model=self._get_model(settings),
        )

        self.processor = MessageProcessor(
            db=self.db,
            whatsapp=self.whatsapp,
            rules_engine=self.rules_engine,
            ai_provider=ai_provider,
            system_prompt=settings.system_prompt,
            response_delay=settings.response_delay,
            poll_interval=settings.poll_interval,
        )

        # Callbacks UI
        self._on_log: Optional[Callable] = None
        self._last_contact: Optional[str] = None

    def _get_api_key(self, settings: AppSettings) -> Optional[str]:
        if settings.ai_provider == "openai":
            return settings.openai_api_key
        elif settings.ai_provider == "anthropic":
            return settings.anthropic_api_key
        return None

    def _get_model(self, settings: AppSettings) -> Optional[str]:
        if settings.ai_provider == "openai":
            return settings.openai_model
        elif settings.ai_provider == "anthropic":
            return settings.anthropic_model
        return None

    def set_ui_callbacks(
        self,
        on_new_message: Optional[Callable] = None,
        on_response_ready: Optional[Callable] = None,
        on_status_change: Optional[Callable] = None,
        on_alert: Optional[Callable] = None,
        on_log: Optional[Callable] = None,
    ):
        """Configure les callbacks de l'UI."""
        self._on_log = on_log

        def wrapped_new_message(msg: IncomingMessage):
            self._last_contact = msg.contact_name
            if on_new_message:
                on_new_message(msg)

        self.processor.on_new_message = wrapped_new_message
        self.processor.on_response_ready = on_response_ready
        self.processor.on_status_change = on_status_change
        self.processor.on_alert = on_alert

    def _log(self, text: str):
        logger.info(text)
        if self._on_log:
            self._on_log(text)

    # --- Contrôle de la surveillance ---

    def start_monitoring(self):
        # Tenter la connexion WhatsApp
        connected = self.whatsapp.connect()
        if not connected:
            self._log("WhatsApp Desktop non détecté ou non connecté")
        else:
            self._log("WhatsApp Desktop connecté")

        self.processor.start()

    def stop_monitoring(self):
        self.processor.stop()

    def pause_monitoring(self):
        self.processor.pause()

    def resume_monitoring(self):
        self.processor.resume()

    def emergency_stop(self):
        self.processor.emergency_stop()

    def is_paused(self) -> bool:
        return self.processor.is_paused

    # --- Actions sur les réponses ---

    def approve_response(self, response_id: int) -> bool:
        result = self.processor.approve_and_send(response_id)
        return result

    def ignore_response(self, response_id: int):
        self.processor.ignore_response(response_id)

    def retry_last_contact(self):
        if self._last_contact:
            self.processor.retry_read(self._last_contact)
        else:
            self._log("Aucun contact récent pour relecture")

    # --- Paramètres ---

    def set_simulation_mode(self, enabled: bool):
        self.whatsapp.simulation_mode = enabled
        self._log(f"Simulation: {'activée' if enabled else 'désactivée'}")

    def set_response_mode(self, mode: str):
        self.rules_engine.default_mode = __import__(
            "app.models.message", fromlist=["ResponseMode"]
        ).ResponseMode(mode)
        self._log(f"Mode réponse: {mode}")

    def set_ai_provider(self, provider_name: str):
        api_key = self._get_api_key(self.settings)
        model = self._get_model(self.settings)
        self.processor.change_ai_provider(provider_name, api_key, model)

    def set_default_tone(self, tone: str):
        self.rules_engine.default_tone = tone

    def set_response_delay(self, delay: int):
        self.processor.response_delay = max(1, delay)

    def set_system_prompt(self, prompt: str):
        self.processor.system_prompt = prompt

    def update_lists(self, whitelist: list[str], blacklist: list[str]):
        self.rules_engine.update_lists(whitelist, blacklist)
        self._log(
            f"Listes mises à jour - Whitelist: {len(whitelist)}, "
            f"Blacklist: {len(blacklist)}"
        )

    def get_current_settings(self) -> dict:
        """Retourne les paramètres actuels pour l'UI."""
        return {
            "response_mode": self.rules_engine.default_mode.value,
            "ai_provider": self.processor.ai_provider.name,
            "default_tone": self.rules_engine.default_tone,
            "response_delay": self.processor.response_delay,
            "simulation_mode": self.whatsapp.simulation_mode,
            "system_prompt": self.processor.system_prompt,
            "whitelist": self.rules_engine.whitelist,
            "blacklist": self.rules_engine.blacklist,
        }
