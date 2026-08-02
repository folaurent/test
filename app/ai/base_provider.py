"""Interface abstraite pour les providers IA."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class AIRequest:
    """Requête vers le provider IA."""
    message: str
    contact_name: str
    system_prompt: str
    tone: str = "neutral"
    context: Optional[str] = None


@dataclass
class AIResponse:
    """Réponse du provider IA."""
    text: str
    provider: str
    model: str
    success: bool = True
    error: Optional[str] = None


class BaseAIProvider(ABC):
    """Interface abstraite pour tous les providers IA."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nom du provider."""

    @abstractmethod
    def generate_response(self, request: AIRequest) -> AIResponse:
        """Génère une réponse à partir d'un message."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Vérifie si le provider est correctement configuré."""

    def _build_system_message(self, request: AIRequest) -> str:
        """Construit le message système avec les instructions de ton."""
        tone_instructions = {
            "neutral": "Réponds de manière neutre et professionnelle.",
            "professional": "Adopte un ton très professionnel et formel.",
            "friendly": "Réponds de manière amicale et chaleureuse, comme à un ami.",
            "casual": "Réponds de manière décontractée et naturelle.",
            "formal": "Utilise un ton très formel et respectueux.",
        }

        tone_instruction = tone_instructions.get(request.tone, tone_instructions["neutral"])

        return f"""{request.system_prompt}

Instructions supplémentaires:
- Contact: {request.contact_name}
- Ton demandé: {tone_instruction}
- Réponds uniquement au message, sans ajouter de contexte inutile.
- Ne te présente pas, ne dis pas que tu es une IA.
- Sois concis et naturel."""
