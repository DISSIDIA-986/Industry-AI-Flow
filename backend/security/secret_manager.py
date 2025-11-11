"""Secret management utilities (encryption and hashing helpers)."""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Iterable, List, Optional

from cryptography.fernet import Fernet, InvalidToken


class SecretManager:
    """Provides Fernet-based decryption and constant-time hash verification."""

    def __init__(
        self,
        *,
        encryption_key: Optional[str] = None,
        hash_salt: Optional[str] = None,
        hash_iterations: int = 120_000,
    ) -> None:
        self._fernet: Optional[Fernet] = None
        if encryption_key:
            key = encryption_key.strip()
            if key:
                self._fernet = Fernet(key.encode())
        self.hash_salt = (hash_salt or "").encode()
        self.hash_iterations = hash_iterations

    def decrypt(self, token: str) -> Optional[str]:
        """Decrypt a fernet token, returning None on failure."""
        if not token or not self._fernet:
            return None
        try:
            decrypted = self._fernet.decrypt(token.encode())
            return decrypted.decode()
        except (InvalidToken, ValueError):
            return None

    def decrypt_list(self, csv_tokens: str) -> List[str]:
        """Decrypt a comma-separated list of tokens."""
        values: List[str] = []
        for chunk in csv_tokens.split(","):
            token = chunk.strip()
            if not token:
                continue
            decrypted = self.decrypt(token)
            if decrypted:
                values.append(decrypted)
        return values

    def hash_value(self, value: str) -> str:
        """Create a salted PBKDF2 hash for the given value."""
        if not value:
            return ""
        if self.hash_salt:
            digest = hashlib.pbkdf2_hmac(
                "sha256", value.encode(), self.hash_salt, self.hash_iterations
            )
        else:
            digest = hashlib.sha256(value.encode()).digest()
        return base64.b16encode(digest).decode()

    def verify_hash(self, value: str, expected_hash_hex: str) -> bool:
        """Constant-time comparison between computed and expected hash."""
        computed = self.hash_value(value)
        return bool(expected_hash_hex) and hmac.compare_digest(
            computed.lower(), expected_hash_hex.strip().lower()
        )

    def verify_against_hashes(self, value: str, hashes: Iterable[str]) -> bool:
        for candidate in hashes:
            if self.verify_hash(value, candidate):
                return True
        return False
