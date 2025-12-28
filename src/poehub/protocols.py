"""Protocol interfaces for PoeHub dependency injection.

Protocols define the expected interface for components, enabling:
- Easy mocking in unit tests
- Swappable implementations (Anti-Corruption Layer pattern)
- Clear documentation of component contracts
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from .models import TokenUsage


@runtime_checkable
class ILLMClient(Protocol):
    """Interface for LLM provider clients.

    Any LLM client implementation must provide these methods.
    Use this protocol for dependency injection in services.
    """

    async def get_models(self, force_refresh: bool = False) -> list[str]:
        """Fetch available models from the provider.

        Args:
            force_refresh: If True, bypass cache and fetch fresh data.

        Returns:
            List of model identifiers.
        """
        ...

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
    ) -> AsyncIterator[str | TokenUsage]:
        """Stream chat completion responses.

        Args:
            model: The model identifier to use.
            messages: List of chat messages in OpenAI format.

        Yields:
            Content strings as they stream in.
            Finally yields a TokenUsage object with usage statistics.
        """
        ...
        yield ""  # pragma: no cover


@runtime_checkable
class IConversationManager(Protocol):
    """Interface for conversation storage management.

    Abstracts the encrypted storage layer for conversations.
    """

    def get_conversation(self, user_id: int, conv_id: str) -> dict[str, Any] | None:
        """Retrieve a conversation by ID.

        Args:
            user_id: The Discord user ID.
            conv_id: The conversation identifier.

        Returns:
            Conversation data dict or None if not found.
        """
        ...

    def save_conversation(
        self, user_id: int, conv_id: str, data: dict[str, Any]
    ) -> None:
        """Save a conversation.

        Args:
            user_id: The Discord user ID.
            conv_id: The conversation identifier.
            data: Conversation data to save.
        """
        ...

    def delete_conversation(self, user_id: int, conv_id: str) -> bool:
        """Delete a conversation.

        Args:
            user_id: The Discord user ID.
            conv_id: The conversation identifier.

        Returns:
            True if deleted, False if not found.
        """
        ...

    def list_conversations(self, user_id: int) -> list[str]:
        """List all conversation IDs for a user.

        Args:
            user_id: The Discord user ID.

        Returns:
            List of conversation identifiers.
        """
        ...


@runtime_checkable
class IEncryption(Protocol):
    """Interface for encryption operations."""

    def encrypt(self, data: str) -> str:
        """Encrypt a string.

        Args:
            data: Plaintext string to encrypt.

        Returns:
            Base64-encoded encrypted string.
        """
        ...

    def decrypt(self, data: str) -> str:
        """Decrypt a string.

        Args:
            data: Base64-encoded encrypted string.

        Returns:
            Decrypted plaintext string.
        """
        ...
