import time
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.asyncio
async def test_auto_clear_loop_logic():
    # Mocking the Cog instance
    cog = MagicMock()

    # Config Setup
    user_id = 12345
    conv_id = "inactive_conv"
    now = time.time()
    old_time = now - (3 * 60 * 60)  # 3 hours ago

    # Mock conversation data (decrypted)
    conv_data = {
        "id": conv_id,
        "updated_at": old_time,
        "messages": [{"role": "user", "content": "hi"}],
        "created_at": old_time
    }

    # Mock encrypted data
    enc_data = "encrypted_blob"

    # Mock all_users return
    cog.config.all_users = AsyncMock(return_value={
        user_id: {"conversations": {conv_id: enc_data}}
    })

    # Mock conversation manager
    cog.conversation_manager.process_conversation_data.return_value = conv_data
    cog.conversation_manager.prepare_for_storage.return_value = "new_encrypted_blob"

    # Mock chat service
    cog.chat_service = AsyncMock()

    # Mock user config setter
    user_config_mock = MagicMock()
    user_config_mock.conversations.set = AsyncMock()
    cog.config.user_from_id.return_value = user_config_mock

    from poehub.poehub import PoeHub

    # We can invoke the method directly if we patch time
    await PoeHub._auto_clear_loop.coro(cog)

    # Verify clear_messages was called
    cog.conversation_manager.clear_messages.assert_called_with(conv_data)

    # Verify storage update
    cog.config.user_from_id.assert_called_with(user_id)
    user_config_mock.conversations.set.assert_awaited()

    # Verify memory clear
    cog.chat_service._clear_conversation_memory.assert_awaited_with(user_id, conv_id)


@pytest.mark.asyncio
async def test_auto_clear_skips_active():
    cog = MagicMock()
    user_id = 12345
    conv_id = "active_conv"
    now = time.time()
    recent_time = now - (10 * 60)  # 10 mins ago

    conv_data = {
        "id": conv_id,
        "updated_at": recent_time,
        "messages": [{"role": "user", "content": "hi"}],
        "created_at": recent_time
    }

    cog.config.all_users = AsyncMock(return_value={
        user_id: {"conversations": {conv_id: "blob"}}
    })

    cog.conversation_manager.process_conversation_data.return_value = conv_data

    from poehub.poehub import PoeHub
    await PoeHub._auto_clear_loop.coro(cog)

    # Verify NOT cleared
    cog.conversation_manager.clear_messages.assert_not_called()
