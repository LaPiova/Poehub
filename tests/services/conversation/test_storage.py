from unittest.mock import MagicMock

import pytest

from poehub.core.encryption import EncryptionHelper
from poehub.services.conversation.storage import ConversationStorageService


class TestConversationStorageService:
    @pytest.fixture
    def manager(self):
        encryption = EncryptionHelper()
        return ConversationStorageService(encryption)

    def test_create_conversation(self, manager):
        conv = manager.create_conversation("test_id", "Test Title")
        assert conv["id"] == "test_id"
        assert conv["title"] == "Test Title"
        assert conv["messages"] == []
        assert "created_at" in conv

    def test_add_message(self, manager):
        conv = manager.create_conversation("test_id")
        manager.add_message(conv, "user", "Hello")
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Hello"

    def test_add_message_history_pruning(self, manager):
        conv = manager.create_conversation("test_id")
        max_history = 5

        for i in range(10):
            manager.add_message(conv, "user", f"msg {i}", max_history=max_history)

        assert len(conv["messages"]) == max_history
        # Should contain the last messages (5 to 9)
        assert conv["messages"][0]["content"] == "msg 5"
        assert conv["messages"][-1]["content"] == "msg 9"

    def test_clear_messages(self, manager):
        conv = manager.create_conversation("test_id")
        manager.add_message(conv, "user", "Hello")
        manager.clear_messages(conv)
        assert len(conv["messages"]) == 0

    def test_get_api_messages(self, manager):
        conv = manager.create_conversation("test_id")
        manager.add_message(conv, "user", "Hello")
        manager.add_message(conv, "assistant", "Hi there")

        api_msgs = manager.get_api_messages(conv)
        assert len(api_msgs) == 2
        # API messages shouldn't have extra fields like timestamp
        assert "timestamp" not in api_msgs[0]
        assert api_msgs[0] == {"role": "user", "content": "Hello"}

    def test_process_conversation_data_encrypted(self, manager):
        # Create a real conversation dict
        conv = {"id": "123", "messages": []}
        # Encrypt it
        encrypted = manager.prepare_for_storage(conv)
        assert isinstance(encrypted, str)

        # Process it back
        decrypted = manager.process_conversation_data(encrypted)
        assert decrypted == conv

    def test_process_conversation_data_raw(self, manager):
        conv = {"id": "123", "messages": []}
        # Should handle raw dicts (backward compatibility)
        processed = manager.process_conversation_data(conv)
        assert processed == conv

    def test_process_conversation_data_none(self, manager):
        assert manager.process_conversation_data(None) is None

    def test_encryption_failure(self, manager):
        # Mock encryption helper to fail
        manager.encryption = MagicMock()
        manager.encryption.decrypt.return_value = None

        assert manager.process_conversation_data("garbage") is None
