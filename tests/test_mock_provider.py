"""Tests unitaires pour le provider mock."""

from app.ai.base_provider import AIRequest
from app.ai.mock_provider import MockAIProvider


class TestMockProvider:
    def setup_method(self):
        self.provider = MockAIProvider()

    def test_name(self):
        assert self.provider.name == "mock"

    def test_is_configured(self):
        assert self.provider.is_configured() is True

    def test_greeting_response(self):
        request = AIRequest(
            message="Bonjour !",
            contact_name="Alice",
            system_prompt="",
            tone="neutral",
        )
        response = self.provider.generate_response(request)
        assert response.success is True
        assert response.text != ""
        assert response.provider == "mock"

    def test_question_response(self):
        request = AIRequest(
            message="Comment configurer le serveur ?",
            contact_name="Bob",
            system_prompt="",
            tone="neutral",
        )
        response = self.provider.generate_response(request)
        assert response.success is True
        assert response.text != ""

    def test_urgent_response(self):
        request = AIRequest(
            message="URGENT: le site est down !",
            contact_name="Admin",
            system_prompt="",
            tone="professional",
        )
        response = self.provider.generate_response(request)
        assert response.success is True
        assert response.text != ""

    def test_default_response(self):
        request = AIRequest(
            message="Le rapport est prêt",
            contact_name="Collègue",
            system_prompt="",
            tone="neutral",
        )
        response = self.provider.generate_response(request)
        assert response.success is True
        assert response.text != ""

    def test_professional_tone(self):
        request = AIRequest(
            message="Bonjour",
            contact_name="Client",
            system_prompt="",
            tone="professional",
        )
        response = self.provider.generate_response(request)
        # Le ton professionnel ne devrait pas contenir "Salut" ou "Hey"
        assert "Hey" not in response.text
