"""
Encryption helper for PoeHub Cog
Uses cryptography.fernet for secure data encryption
"""

from cryptography.fernet import Fernet
import base64
import json
from typing import Any, Dict


class EncryptionHelper:
    """Helper class for encrypting and decrypting data using Fernet symmetric encryption"""
    
    def __init__(self, key: str = None):
        """
        Initialize the encryption helper.
        
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
        """
        Get the encryption key as a string.
        
        Returns:
            str: Base64-encoded encryption key
        """
        return self._key.decode()
    
    def encrypt(self, data: Any) -> str:
        """
        Encrypt data. Automatically handles JSON serialization.
        
        Args:
            data: Data to encrypt (must be JSON-serializable)
            
        Returns:
            str: Encrypted data as base64 string
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
        """
        Decrypt data. Automatically handles JSON deserialization.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Original data (JSON-deserialized)
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
        except Exception as e:
            # If decryption fails, return None
            return None
    
    def encrypt_dict(self, data_dict: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt all values in a dictionary.
        
        Args:
            data_dict: Dictionary with values to encrypt
            
        Returns:
            Dictionary with encrypted values
        """
        if not data_dict:
            return {}
        
        return {key: self.encrypt(value) for key, value in data_dict.items()}
    
    def decrypt_dict(self, encrypted_dict: Dict[str, str]) -> Dict[str, Any]:
        """
        Decrypt all values in a dictionary.
        
        Args:
            encrypted_dict: Dictionary with encrypted values
            
        Returns:
            Dictionary with decrypted values
        """
        if not encrypted_dict:
            return {}
        
        return {key: self.decrypt(value) for key, value in encrypted_dict.items()}


def generate_key() -> str:
    """
    Generate a new Fernet encryption key.
    
    Returns:
        str: Base64-encoded encryption key
    """
    return Fernet.generate_key().decode()

