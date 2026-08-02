"""Configuration centralisée de l'application."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


@dataclass
class AppSettings:
    """Paramètres globaux de l'application."""

    # Général
    app_name: str = "WhatsApp Desktop Assistant"
    debug: bool = False

    # Mode de réponse: draft_only, manual_validation, auto_reply
    response_mode: str = "draft_only"

    # Délai avant réponse (secondes)
    response_delay: int = 5

    # Intervalle de surveillance (secondes)
    poll_interval: int = 3

    # Provider IA: openai, anthropic, mock
    ai_provider: str = "mock"

    # Clés API (chargées depuis .env)
    openai_api_key: Optional[str] = field(default=None, repr=False)
    anthropic_api_key: Optional[str] = field(default=None, repr=False)

    # Modèles IA
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Prompt système par défaut
    system_prompt: str = (
        "Tu es un assistant personnel. Réponds de manière naturelle, "
        "concise et adaptée au contexte du message reçu. "
        "Adapte ton ton selon les instructions supplémentaires."
    )

    # Ton par défaut
    default_tone: str = "neutral"

    # Listes de contacts
    whitelist: list = field(default_factory=list)
    blacklist: list = field(default_factory=list)

    # Base de données
    db_path: str = "data/assistant.db"

    # Mode simulation (pas d'envoi réel)
    simulation_mode: bool = True

    # Nom de l'utilisateur WhatsApp (pour anti-boucle)
    whatsapp_user_name: str = ""

    def __post_init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.simulation_mode = os.getenv("SIMULATION_MODE", "true").lower() == "true"
        self.whatsapp_user_name = os.getenv("WHATSAPP_USER_NAME", "")

        env_provider = os.getenv("AI_PROVIDER")
        if env_provider:
            self.ai_provider = env_provider

        env_mode = os.getenv("RESPONSE_MODE")
        if env_mode:
            self.response_mode = env_mode

        # S'assurer que le répertoire data existe
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)


# Instance globale
settings = AppSettings()
