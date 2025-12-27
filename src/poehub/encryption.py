"""Encryption helpers for PoeHub.

Uses Fernet symmetric encryption (via `cryptography`) to encrypt JSON payloads.
"""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional, Union

from cryptography.fernet import Fernet


class EncryptionHelper:
    """Helper for encrypting and decrypting JSON-serializable payloads."""

    def __init__(self, key: Optional[Union[str, bytes]] = None) -> None:
        """Initialize the encryption helper.

        Args:
            key: Base64-encoded Fernet key. If None, generates a new key.
        """
        if key is None:
            # Generate a new key
            self._key = Fernet.generate_key()
        else:
            # Use provided key
            if isinstance(key, str):
                self._key = key.encode()
            else:
                self._key = key
        
        self.cipher = Fernet(self._key)
    
    def get_key(self) -> str:
        """Return the encryption key as a base64-encoded string."""
        return self._key.decode()
    
    def encrypt(self, data: Any) -> Optional[str]:
        """Encrypt data with JSON serialization.

        Args:
            data: Data to encrypt (must be JSON-serializable).

        Returns:
            Base64-encoded encrypted payload, or None if `data` is None.
        """
        if data is None:
            return None
        
        # Convert to JSON string
        json_str = json.dumps(data)
        
        # Encrypt
        encrypted = self.cipher.encrypt(json_str.encode())
        
        # Return as base64 string
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> Any:
        """Decrypt data with JSON deserialization.

        Args:
            encrypted_data: Base64-encoded encrypted payload.

        Returns:
            The decrypted JSON value, or None if decryption fails.
        """
        if encrypted_data is None:
            return None
        
        try:
            # Decode from base64
            encrypted = base64.b64decode(encrypted_data.encode())
            
            # Decrypt
            decrypted = self.cipher.decrypt(encrypted)
            
            # Parse JSON
            return json.loads(decrypted.decode())
        except Exception:  # noqa: BLE001 - corrupted payloads happen
            return None
    
    def encrypt_dict(self, data_dict: Dict[str, Any]) -> Dict[str, str]:
        """Encrypt all values in a dictionary."""
        if not data_dict:
            return {}
        
        return {key: self.encrypt(value) for key, value in data_dict.items()}
    
    def decrypt_dict(self, encrypted_dict: Dict[str, str]) -> Dict[str, Any]:
        """Decrypt all values in a dictionary."""
        if not encrypted_dict:
            return {}
        
        return {key: self.decrypt(value) for key, value in encrypted_dict.items()}


def generate_key() -> str:
    """Generate a new Fernet encryption key."""
    return Fernet.generate_key().decode()

