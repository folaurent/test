"""Provider IA Anthropic (Claude)."""

from typing import Optional

from app.ai.base_provider import AIRequest, AIResponse, BaseAIProvider
from app.utils.logger import app_logger

logger = app_logger


class AnthropicProvider(BaseAIProvider):
    """Provider utilisant l'API Anthropic Claude."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key
        self._model = model
        self._client = None

    @property
    def name(self) -> str:
        return "anthropic"

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "Le package 'anthropic' n'est pas installé. "
                    "Installez-le avec: pip install anthropic"
                )
        return self._client

    def generate_response(self, request: AIRequest) -> AIResponse:
        try:
            client = self._get_client()
            system_message = self._build_system_message(request)

            response = client.messages.create(
                model=self._model,
                max_tokens=500,
                system=system_message,
                messages=[
                    {"role": "user", "content": request.message},
                ],
            )

            text = response.content[0].text.strip()
            return AIResponse(
                text=text,
                provider="anthropic",
                model=self._model,
                success=True,
            )

        except Exception as e:
            logger.error("Erreur Anthropic: %s", e)
            return AIResponse(
                text="",
                provider="anthropic",
                model=self._model,
                success=False,
                error=str(e),
            )

    def is_configured(self) -> bool:
        return bool(self._api_key)
