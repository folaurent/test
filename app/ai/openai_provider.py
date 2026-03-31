"""Provider IA OpenAI."""

from typing import Optional

from app.ai.base_provider import AIRequest, AIResponse, BaseAIProvider
from app.utils.logger import app_logger

logger = app_logger


class OpenAIProvider(BaseAIProvider):
    """Provider utilisant l'API OpenAI."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self._api_key = api_key
        self._model = model
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError(
                    "Le package 'openai' n'est pas installé. "
                    "Installez-le avec: pip install openai"
                )
        return self._client

    def generate_response(self, request: AIRequest) -> AIResponse:
        try:
            client = self._get_client()
            system_message = self._build_system_message(request)

            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": request.message},
                ],
                max_tokens=500,
                temperature=0.7,
            )

            text = response.choices[0].message.content.strip()
            return AIResponse(
                text=text,
                provider="openai",
                model=self._model,
                success=True,
            )

        except Exception as e:
            logger.error("Erreur OpenAI: %s", e)
            return AIResponse(
                text="",
                provider="openai",
                model=self._model,
                success=False,
                error=str(e),
            )

    def is_configured(self) -> bool:
        return bool(self._api_key)
