"""Factory pour la création des providers IA."""

from app.ai.anthropic_provider import AnthropicProvider
from app.ai.base_provider import BaseAIProvider
from app.ai.mock_provider import MockAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.utils.logger import app_logger

logger = app_logger


class AIProviderFactory:
    """Factory pour instancier le bon provider IA selon la configuration."""

    _providers: dict[str, type[BaseAIProvider]] = {
        "mock": MockAIProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
    }

    @classmethod
    def create(
        cls,
        provider_name: str,
        api_key: str | None = None,
        model: str | None = None,
    ) -> BaseAIProvider:
        """Crée et retourne une instance du provider demandé."""
        if provider_name not in cls._providers:
            logger.warning(
                "Provider '%s' inconnu, utilisation du mock", provider_name
            )
            return MockAIProvider()

        provider_class = cls._providers[provider_name]

        if provider_name == "mock":
            return MockAIProvider()
        elif provider_name == "openai":
            return OpenAIProvider(api_key=api_key, model=model or "gpt-4o")
        elif provider_name == "anthropic":
            return AnthropicProvider(
                api_key=api_key, model=model or "claude-sonnet-4-20250514"
            )

        return MockAIProvider()

    @classmethod
    def available_providers(cls) -> list[str]:
        return list(cls._providers.keys())
