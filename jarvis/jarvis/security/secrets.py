"""SecretStore — chiffrement symétrique Fernet au repos.

Les secrets sont chiffrés avec `SECRETS_MASTER_KEY`. Jamais loggés en clair.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class SecretStore:
    def __init__(self, master_key: bytes | str) -> None:
        if isinstance(master_key, str):
            master_key = master_key.encode()
        if not master_key:
            raise ValueError("SecretStore: SECRETS_MASTER_KEY vide")
        self._fernet = Fernet(master_key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as e:
            raise ValueError("SecretStore: token invalide") from e

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode()
