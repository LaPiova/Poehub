"""Conversation state management for PoeHub."""

from __future__ import annotations

import logging
import time
from typing import Any

from ...core.encryption import EncryptionHelper

log = logging.getLogger("red.poehub.services.conversation.storage")


class ConversationStorageService:
    """Manages conversation state and encryption/decryption."""

    def __init__(self, encryption: EncryptionHelper) -> None:
        self.encryption = encryption

    def process_conversation_data(self, data: Any) -> dict[str, Any] | None:
        """Decrypt and validate conversation data.

        Args:
            data: Stored conversation payload; may be an encrypted string or a
                raw dict (backwards compatibility).

        Returns:
            The decoded conversation dict, or None if invalid/decryption failed.
        """
        if data is None:
            return None

        # Decrypt if it's a string (encrypted)
        if isinstance(data, str):
            try:
                decrypted = self.encryption.decrypt(data)
                if decrypted is None:
                    log.error("Failed to decrypt conversation data")
                    return None
                return decrypted
            except Exception as exc:  # noqa: BLE001 - corrupted payloads happen
                log.warning("Error decrypting conversation: %s", exc)
                return None

        # Return as is if it's already a dict
        return data

    def prepare_for_storage(self, conversation: dict[str, Any]) -> str:
        """Encrypt conversation data for storage."""
        return self.encryption.encrypt(conversation)

    def create_conversation(
        self, conv_id: str, title: str | None = None
    ) -> dict[str, Any]:
        """Create a new initialized conversation structure."""
        return {
            "id": conv_id,
            "created_at": time.time(),
            "updated_at": time.time(),
            "messages": [],
            "title": title or f"Conversation {conv_id}",
        }

    def add_message(
        self,
        conversation: dict[str, Any],
        role: str,
        content: str | list[dict[str, Any]],
        max_history: int = 50,
    ) -> dict[str, Any]:
        """Append a message and enforce the history limit.

        Args:
            conversation: Conversation dict to update in-place.
            role: OpenAI role ("user", "assistant", "system").
            content: Either a plain string or an OpenAI-Vision content array.
            max_history: Maximum number of messages to retain.

        Returns:
            The updated conversation dict.
        """
        if "messages" not in conversation:
            conversation["messages"] = []

        conversation["messages"].append(
            {"role": role, "content": content, "timestamp": time.time()}
        )

        # Prune old messages to avoid context window issues
        if len(conversation["messages"]) > max_history:
            conversation["messages"] = conversation["messages"][-max_history:]

        conversation["updated_at"] = time.time()

        return conversation

    def clear_messages(self, conversation: dict[str, Any]) -> dict[str, Any]:
        """Clear all messages from the conversation."""
        conversation["messages"] = []
        return conversation

    def get_api_messages(self, conversation: dict[str, Any]) -> list[dict[str, Any]]:
        """Return messages formatted for the OpenAI/Poe API."""
        if not conversation or "messages" not in conversation:
            return []

        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in conversation["messages"]
        ]

    def get_title(self, conversation: dict[str, Any], default: str) -> str:
        """Safely get title."""
        return conversation.get("title", default)

    def get_message_count(self, conversation: dict[str, Any]) -> int:
        """Safely get message count."""
        return len(conversation.get("messages", []))
