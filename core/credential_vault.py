"""
========================================================================================
        SAJIM TRADERS — CREDENTIAL VAULT (core/credential_vault.py)
========================================================================================
Encrypts/decrypts client MT5 passwords at rest using Fernet (symmetric AES).

Key derivation: a stable 32-byte Fernet key is derived via SHA-256 from the dedicated
CREDENTIAL_ENCRYPTION_KEY env var. It is REQUIRED for encryption — there is no silent
fallback, and encrypt_password raises CredentialVaultError when it is missing.
Both the API (Render) and the bridge supervisor (Windows host) must share the same
CREDENTIAL_ENCRYPTION_KEY so they derive the same key.

Backward compatibility: rows encrypted before this change used a key derived from
SUPABASE_SERVICE_ROLE_KEY. decrypt_password tries the dedicated key first and then
that legacy key, so existing rows keep working. Re-save (re-connect) those accounts to
re-encrypt them under the dedicated key; the legacy path can then be removed.
"""

import os
import base64
import hashlib
import logging
from typing import List

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("CredentialVault")


class CredentialVaultError(RuntimeError):
    """Raised when credentials cannot be encrypted (e.g. missing encryption key)."""


def _derive(secret: str) -> bytes:
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())


def _fernet_key() -> bytes:
    secret = os.environ.get("CREDENTIAL_ENCRYPTION_KEY", "")
    return _derive(secret) if secret else b""


def _decryption_keys() -> List[bytes]:
    keys = []
    primary = _fernet_key()
    if primary:
        keys.append(primary)
    legacy_secret = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if legacy_secret:
        legacy = _derive(legacy_secret)
        if legacy not in keys:
            keys.append(legacy)
    return keys


def is_configured() -> bool:
    return bool(_fernet_key())


def encrypt_password(plaintext: str) -> str:
    """Encrypt a plaintext password. Raises CredentialVaultError if no key is configured."""
    if not plaintext:
        raise CredentialVaultError("Cannot encrypt an empty password")
    key = _fernet_key()
    if not key:
        raise CredentialVaultError("CREDENTIAL_ENCRYPTION_KEY is not configured")
    return Fernet(key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a stored password. Returns '' on failure or missing key."""
    if not ciphertext:
        return ""
    for key in _decryption_keys():
        try:
            return Fernet(key).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError):
            continue
        except Exception as e:
            logger.warning(f"Failed to decrypt credential: {type(e).__name__}")
            return ""
    logger.warning("Failed to decrypt credential: no configured key matched")
    return ""
