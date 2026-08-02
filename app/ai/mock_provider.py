"""Provider IA mock pour les tests et la simulation."""

import random

from app.ai.base_provider import AIRequest, AIResponse, BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Provider mock qui génère des réponses prédéfinies."""

    RESPONSES = {
        "greeting": [
            "Bonjour ! Comment puis-je vous aider ?",
            "Salut ! Tout va bien, merci !",
            "Hey ! Content d'avoir de tes nouvelles !",
        ],
        "question": [
            "Bonne question, je vais vérifier et te revenir rapidement.",
            "Je m'en occupe et je te tiens au courant.",
            "Laisse-moi regarder ça, je te réponds dans quelques minutes.",
        ],
        "urgent": [
            "Je prends note de l'urgence et m'en occupe immédiatement.",
            "Bien reçu, c'est prioritaire. Je traite ça tout de suite.",
            "Compris, je m'y mets immédiatement.",
        ],
        "default": [
            "Bien reçu, merci pour l'info !",
            "OK, c'est noté.",
            "Merci pour le message, je prends note.",
            "D'accord, je m'en occupe.",
        ],
    }

    @property
    def name(self) -> str:
        return "mock"

    def generate_response(self, request: AIRequest) -> AIResponse:
        content_lower = request.message.lower()

        if any(w in content_lower for w in ["bonjour", "salut", "hello", "hey", "coucou"]):
            category = "greeting"
        elif "?" in request.message or any(
            w in content_lower for w in ["comment", "quand", "pourquoi", "peux-tu", "est-ce"]
        ):
            category = "question"
        elif any(w in content_lower for w in ["urgent", "asap", "immédiat", "critique"]):
            category = "urgent"
        else:
            category = "default"

        response_text = random.choice(self.RESPONSES[category])

        # Adapter le ton
        if request.tone == "professional":
            response_text = response_text.replace("Salut", "Bonjour").replace("Hey", "Bonjour")
        elif request.tone == "casual":
            response_text = response_text.replace("Bonjour", "Salut").replace(
                "Comment puis-je vous aider", "Quoi de neuf"
            )

        return AIResponse(
            text=response_text,
            provider="mock",
            model="mock-v1",
            success=True,
        )

    def is_configured(self) -> bool:
        return True
