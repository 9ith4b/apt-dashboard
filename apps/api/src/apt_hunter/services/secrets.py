import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from apt_hunter.config import get_settings


class SecretConfigurationError(RuntimeError):
    pass


def _fernet() -> Fernet:
    configured = get_settings().ai_secrets_key
    if configured is None or len(configured.get_secret_value()) < 32:
        raise SecretConfigurationError(
            "APT_HUNTER_AI_SECRETS_KEY must be configured with at least 32 characters"
        )
    digest = hashlib.sha256(configured.get_secret_value().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    if not value:
        raise ValueError("Secret cannot be empty")
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise SecretConfigurationError(
            "The stored model credential cannot be decrypted with the configured key"
        ) from exc
