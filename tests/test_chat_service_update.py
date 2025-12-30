import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from poehub.services.chat import ChatService


@pytest.fixture(scope="module", autouse=True)
def mock_red_dependencies():
    """Mock redbot and discord modules for this test module only."""
    mock_modules = {
        "redbot": MagicMock(),
        "redbot.core": MagicMock(),
        "redbot.core.bot": MagicMock(),
        "redbot.core.commands": MagicMock(),
        "discord": MagicMock(),
        "discord.ext": MagicMock(),
        "discord.ext.tasks": MagicMock(),
    }

    with patch.dict(sys.modules, mock_modules):
        yield


@pytest.mark.asyncio
async def test_add_message_updates_timestamp():
    # Setup Mocks
    bot = MagicMock()
    config = MagicMock()
    billing = MagicMock()
    context = MagicMock()
    storage = MagicMock()

    service = ChatService(bot, config, billing, context, storage)

    user_id = 123
    conv_id = "test_conv"

    user_config = MagicMock()
    user_config.conversations = AsyncMock(return_value={})
    user_config.conversations.set = AsyncMock()
    config.user_from_id.return_value = user_config

    storage.create_conversation.return_value = {
        "id": conv_id,
        "messages": [],
        "updated_at": 0
    }
    storage.process_conversation_data.return_value = {
        "id": conv_id,
        "messages": [],
        "updated_at": 0
    }
    storage.prepare_for_storage.return_value = "encrypted_blob"

    unique_key = f"user:{user_id}:{conv_id}"
    await service.add_message_to_conversation(user_config, conv_id, unique_key, "user", "hello")

    call_args = user_config.conversations.set.call_args
    assert call_args is not None
    saved_conversations = call_args[0][0]
    assert conv_id in saved_conversations

    storage.prepare_for_storage.assert_called()
    saved_conv_dict = storage.prepare_for_storage.call_args[0][0]

    assert saved_conv_dict["updated_at"] > 0
    assert time.time() - saved_conv_dict["updated_at"] < 5
