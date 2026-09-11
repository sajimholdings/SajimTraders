"""
========================================================================================
        SAJIM TRADERS — CREDENTIAL VAULT (core/credential_vault.py)
========================================================================================
Encrypts/decrypts client MT5 passwords at rest using Fernet (symmetric AES).

Key derivation: a stable 32-byte Fernet key is derived via SHA-256 from
CREDENTIAL_ENCRYPTION_KEY (if set) or, as a fallback, SUPABASE_SERVICE_ROLE_KEY.
Both the API (Render) and the bridge supervisor (Windows host) must share the same
env, so they derive the same key.
"""

import os
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("CredentialVault")


def _fernet_key() -> bytes:
    secret = os.environ.get("CREDENTIAL_ENCRYPTION_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not secret:
        return b""
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())


def encrypt_password(plaintext: str) -> str:
    """Encrypt a plaintext password. Returns '' if no key is configured."""
    key = _fernet_key()
    if not key or not plaintext:
        return ""
    return Fernet(key).encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a stored password. Returns '' on failure or missing key."""
    key = _fernet_key()
    if not key or not ciphertext:
        return ""
    try:
        return Fernet(key).decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError, Exception) as e:
        logger.warning(f"Failed to decrypt credential: {type(e).__name__}")
        return ""
