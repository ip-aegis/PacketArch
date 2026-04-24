# PacketArch — OT Traffic Simulation Platform
# Copyright (c) 2026 Rocky Smith <rocky.d.smith@proton.me>
# Licensed under GPL-3.0. See LICENSE at the repo root.
"""Encryption utilities for storing sensitive data like API keys."""

import base64
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_encryption_key() -> bytes:
    """Get or generate the encryption key."""
    if settings.encryption_key:
        # Use provided key (should be base64-encoded 32-byte key)
        return base64.urlsafe_b64decode(settings.encryption_key)
    else:
        # Derive key from secret_key using PBKDF2
        # This is deterministic, so the same secret_key always produces the same encryption key
        salt = b"packetarch_salt_v1"  # Static salt for key derivation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        key = kdf.derive(settings.secret_key.encode())
        return base64.urlsafe_b64encode(key)


def _get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    key = _get_encryption_key()
    return Fernet(key)


def encrypt_value(value: str) -> str:
    """Encrypt a string value.

    Args:
        value: Plain text value to encrypt

    Returns:
        Base64-encoded encrypted value
    """
    if not value:
        return ""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt an encrypted string value.

    Args:
        encrypted_value: Base64-encoded encrypted value

    Returns:
        Decrypted plain text value
    """
    if not encrypted_value:
        return ""
    try:
        fernet = _get_fernet()
        decoded = base64.urlsafe_b64decode(encrypted_value.encode())
        decrypted = fernet.decrypt(decoded)
        return decrypted.decode()
    except Exception:
        # Return empty string if decryption fails
        return ""


def generate_encryption_key() -> str:
    """Generate a new random encryption key.

    Returns:
        Base64-encoded 32-byte key suitable for ENCRYPTION_KEY env var
    """
    key = Fernet.generate_key()
    return key.decode()
