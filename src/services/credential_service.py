"""Store application secrets in Windows Credential Manager via keyring."""
from __future__ import annotations

import keyring


SERVICE_NAME = "KorailKTXDesktop"


class CredentialService:
    def get(self, key: str) -> str:
        return keyring.get_password(SERVICE_NAME, key) or ""

    def set(self, key: str, value: str) -> None:
        if value:
            keyring.set_password(SERVICE_NAME, key, value)
        else:
            self.delete(key)

    def delete(self, key: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, key)
        except keyring.errors.PasswordDeleteError:
            pass
