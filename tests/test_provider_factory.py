"""Tests unitaires pour la factory de providers."""

from app.ai.mock_provider import MockAIProvider
from app.ai.openai_provider import OpenAIProvider
from app.ai.anthropic_provider import AnthropicProvider
from app.ai.provider_factory import AIProviderFactory


class TestProviderFactory:
    def test_create_mock(self):
        provider = AIProviderFactory.create("mock")
        assert isinstance(provider, MockAIProvider)

    def test_create_openai(self):
        provider = AIProviderFactory.create("openai", api_key="test-key")
        assert isinstance(provider, OpenAIProvider)

    def test_create_anthropic(self):
        provider = AIProviderFactory.create("anthropic", api_key="test-key")
        assert isinstance(provider, AnthropicProvider)

    def test_unknown_provider_falls_back_to_mock(self):
        provider = AIProviderFactory.create("unknown_provider")
        assert isinstance(provider, MockAIProvider)

    def test_available_providers(self):
        providers = AIProviderFactory.available_providers()
        assert "mock" in providers
        assert "openai" in providers
        assert "anthropic" in providers
