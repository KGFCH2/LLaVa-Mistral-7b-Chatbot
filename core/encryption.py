"""
Chat history encryption and decryption using Fernet (symmetric encryption).

Encrypts sensitive chat data (text messages, images, audio) at rest in the database
using AES-128 encryption with authenticated encryption to ensure data integrity.
"""

import os
import logging
from typing import Optional, Union
from cryptography.fernet import Fernet, InvalidToken
from core.utils import load_config

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption operations fail."""
    pass


class EncryptionKeyError(EncryptionError):
    """Raised when encryption key is missing or invalid."""
    pass


class _EncryptionManager:
    """
    Manages encryption and decryption of sensitive data.

    Uses Fernet (symmetric encryption) with a master key. The key can be:
    1. Loaded from environment variable ENCRYPTION_KEY
    2. Loaded from config file
    3. Generated automatically (not recommended for production)
    """

    def __init__(self):
        """Initialize encryption manager with key from config or environment."""
        self._cipher = None
        self._key = None
        self._load_key()

    def _load_key(self) -> None:
        """
        Load encryption key from environment or config.

        Priority order:
        1. Environment variable ENCRYPTION_KEY
        2. Config file encryption.key field
        3. Auto-generate (warning: only for development)
        """
        try:
            config = load_config()

            # Try environment variable first
            key = os.environ.get("ENCRYPTION_KEY")
            if key:
                logger.info("Using encryption key from ENCRYPTION_KEY environment variable")
                self._key = key.encode() if isinstance(key, str) else key
                self._validate_key()
                self._cipher = Fernet(self._key)
                return

            # Try config file
            if "encryption" in config and "key" in config["encryption"]:
                key = config["encryption"]["key"]
                logger.info("Using encryption key from config file")
                self._key = key.encode() if isinstance(key, str) else key
                self._validate_key()
                self._cipher = Fernet(self._key)
                return

            # Auto-generate for development (not recommended)
            logger.warning("No encryption key found. Generating a new key for this session.")
            logger.warning("This key will not persist across restarts. Use environment variable or config file for production.")
            self._key = Fernet.generate_key()
            self._cipher = Fernet(self._key)

        except InvalidToken:
            raise EncryptionKeyError("Invalid encryption key format. Must be a valid Fernet key.")
        except Exception as e:
            logger.error(f"Failed to load encryption key: {str(e)}")
            raise EncryptionKeyError(f"Failed to initialize encryption: {str(e)}")

    def _validate_key(self) -> None:
        """Validate that the key is a valid Fernet key."""
        try:
            Fernet(self._key)
        except Exception:
            raise InvalidToken("Invalid Fernet key format")

    @property
    def cipher(self) -> Fernet:
        """Get the Fernet cipher instance."""
        if self._cipher is None:
            raise EncryptionError("Encryption not initialized")
        return self._cipher

    def encrypt(self, data: Union[str, bytes]) -> bytes:
        """
        Encrypt data using Fernet symmetric encryption.

        Args:
            data: String or bytes to encrypt

        Returns:
            Encrypted bytes

        Raises:
            EncryptionError: If encryption fails
        """
        try:
            if isinstance(data, str):
                data = data.encode("utf-8")

            encrypted = self.cipher.encrypt(data)
            logger.debug(f"Data encrypted successfully ({len(data)} bytes -> {len(encrypted)} bytes)")
            return encrypted

        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise EncryptionError(f"Failed to encrypt data: {str(e)}")

    def decrypt(self, encrypted_data: Union[str, bytes]) -> str:
        """
        Decrypt data using Fernet symmetric encryption.

        Args:
            encrypted_data: Encrypted bytes or string to decrypt

        Returns:
            Decrypted string

        Raises:
            EncryptionError: If decryption fails or data is tampered
        """
        try:
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode("utf-8")

            decrypted = self.cipher.decrypt(encrypted_data)
            logger.debug(f"Data decrypted successfully ({len(encrypted_data)} bytes -> {len(decrypted)} bytes)")
            return decrypted.decode("utf-8")

        except InvalidToken:
            logger.error("Decryption failed: Invalid token (data may be tampered or corrupted)")
            raise EncryptionError("Failed to decrypt data: Invalid token (data may be tampered or corrupted)")
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise EncryptionError(f"Failed to decrypt data: {str(e)}")

    def decrypt_binary(self, encrypted_data: Union[str, bytes]) -> bytes:
        """
        Decrypt binary data (images, audio).

        Args:
            encrypted_data: Encrypted bytes or string to decrypt

        Returns:
            Decrypted binary data

        Raises:
            EncryptionError: If decryption fails
        """
        try:
            if isinstance(encrypted_data, str):
                encrypted_data = encrypted_data.encode("utf-8")

            decrypted = self.cipher.decrypt(encrypted_data)
            logger.debug(f"Binary data decrypted successfully ({len(encrypted_data)} bytes -> {len(decrypted)} bytes)")
            return decrypted

        except InvalidToken:
            logger.error("Binary decryption failed: Invalid token (data may be tampered)")
            raise EncryptionError("Failed to decrypt binary data: Invalid token")
        except Exception as e:
            logger.error(f"Binary decryption failed: {str(e)}")
            raise EncryptionError(f"Failed to decrypt binary data: {str(e)}")


# Global encryption manager instance
_manager = _EncryptionManager()


def encrypt_text(text: str) -> bytes:
    """
    Encrypt text message for storage.

    Args:
        text: Plain text to encrypt

    Returns:
        Encrypted bytes

    Raises:
        EncryptionError: If encryption fails
    """
    if not text:
        return b""
    return _manager.encrypt(text)


def decrypt_text(encrypted_text: Union[str, bytes]) -> str:
    """
    Decrypt text message from storage.

    Args:
        encrypted_text: Encrypted data

    Returns:
        Decrypted text

    Raises:
        EncryptionError: If decryption fails
    """
    if not encrypted_text:
        return ""
    return _manager.decrypt(encrypted_text)


def encrypt_binary(data: bytes) -> bytes:
    """
    Encrypt binary data (images, audio) for storage.

    Args:
        data: Binary data to encrypt

    Returns:
        Encrypted bytes

    Raises:
        EncryptionError: If encryption fails
    """
    if not data:
        return b""
    return _manager.encrypt(data)


def decrypt_binary(encrypted_data: Union[str, bytes]) -> bytes:
    """
    Decrypt binary data (images, audio) from storage.

    Args:
        encrypted_data: Encrypted data

    Returns:
        Decrypted binary data

    Raises:
        EncryptionError: If decryption fails
    """
    if not encrypted_data:
        return b""
    return _manager.decrypt_binary(encrypted_data)


def is_encryption_available() -> bool:
    """Check if encryption is properly configured and available."""
    try:
        return _manager.cipher is not None
    except Exception:
        return False
