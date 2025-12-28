"""Protocol interfaces for PoeHub dependency injection.

Protocols define the expected interface for components, enabling:
- Easy mocking in unit tests
- Swappable implementations (Anti-Corruption Layer pattern)
- Clear documentation of component contracts
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from ..models import TokenUsage


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
class IConversationStorageService(Protocol):
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


@runtime_checkable
class IChatService(Protocol):
    """Interface for Chat Service."""

    async def stream_response(
        self,
        ctx: Any,
        messages: list[dict[str, Any]],
        model: str,
        target_channel: Any = None,
        save_to_conv: tuple[int, str] | None = None,
        billing_guild: Any = None,
    ) -> None:
        """Stream response to Discord."""
        ...

    async def get_response(
        self,
        messages: list[dict[str, Any]],
        model: str,
        billing_guild: Any = None,
    ) -> str:
        """Get a complete response string (non-streaming)."""
        ...

    async def send_split_message(self, destination: Any, content: str) -> None:
        """Send a long message to Discord, splitting if necessary."""
        ...


@runtime_checkable
class IContextService(Protocol):
    """Interface for Context Service."""

    async def get_active_conversation_id(self, user_id: int) -> str: ...
    async def get_user_system_prompt(self, user_id: int) -> str | None: ...


@runtime_checkable
class ISummarizerService(Protocol):
    """Interface for Summarizer Service."""

    async def summarize_messages(
        self,
        messages: list[Any],  # list[MessageData]
        user_id: int,
        model: str,
        billing_guild: Any = None,
    ) -> AsyncIterator[str]:
        """Generate a summary, yielding progress updates and final result."""
        ...
        yield ""


@runtime_checkable
class IPoeHub(Protocol):
    """Interface for the main PoeHub cog."""

    bot: Any
    config: Any
    conversation_manager: IConversationStorageService | None
    chat_service: IChatService
    context_service: IContextService
    summarizer: ISummarizerService | None
    allow_dummy_mode: bool

    # UI Helpers
    async def _build_model_select_options(
        self, query: str | None = None
    ) -> list[Any]: ...
    async def _build_config_embed(
        self, ctx: Any, owner_mode: bool, dummy_state: bool, lang: str
    ) -> Any: ...
