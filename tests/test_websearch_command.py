
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from poehub.poehub import PoeHub


@pytest.mark.asyncio
async def test_websearch_command_dm():
    # Setup
    bot = MagicMock()
    cog = PoeHub(bot)
    cog.bot = bot

    # Mock context
    ctx = AsyncMock()
    ctx.channel = MagicMock(spec=discord.DMChannel)
    ctx.author.id = 12345

    # Mock context service to return a conversation ID
    cog.context_service = AsyncMock()
    cog.context_service.get_active_conversation_id.return_value = "conv_123"

    # Mock conversation manager
    cog.conversation_manager = MagicMock()
    mock_conv_data = {"messages": []}
    cog.conversation_manager.process_conversation_data.return_value = mock_conv_data
    cog.conversation_manager.create_conversation.return_value = mock_conv_data
    cog.conversation_manager.prepare_for_storage.return_value = "encrypted_data"

    # Mock config
    # We need to ensure _get_or_create_conversation works
    # It accesses config.user_from_id(uid).conversations()
    mock_user_group = AsyncMock()
    mock_conversations = {}
    mock_user_group.conversations.return_value = mock_conversations

    # Setup config mock chain
    cog.config.user_from_id.return_value = mock_user_group

    # Execute command /websearch True
    await cog.web_search(ctx, True)

    # Check if data was updated in our mock reference
    # Note: _save_conversation calls set() on the config group
    # We verify that set was called with updated data
    mock_user_group.conversations.set.assert_called()


    # We can't easily inspect "args" because prepare_for_storage transforms it to string.
    # But we can check that prepare_for_storage was called with the right data?
    prepare_call = cog.conversation_manager.prepare_for_storage.call_args
    saved_data = prepare_call[0][0]

    assert "optimizer_settings" in saved_data
    assert saved_data["optimizer_settings"]["web_search_override"] is True

    # Now Disable
    await cog.web_search(ctx, False)
    prepare_call = cog.conversation_manager.prepare_for_storage.call_args
    saved_data = prepare_call[0][0]
    assert saved_data["optimizer_settings"]["web_search_override"] is False


@pytest.mark.asyncio
async def test_websearch_command_thread():
    # Setup
    bot = MagicMock()
    cog = PoeHub(bot)
    cog.bot = bot

    # Mock context
    ctx = AsyncMock()
    # Not DM
    ctx.channel = MagicMock(spec=discord.TextChannel)

    # Mock conversation manager
    cog.conversation_manager = MagicMock()
    mock_conv_data = {"messages": []}
    cog.conversation_manager.process_conversation_data.return_value = mock_conv_data
    cog.conversation_manager.create_conversation.return_value = mock_conv_data

    # Mock config for channel
    mock_channel_group = AsyncMock()
    mock_conversations = {}
    mock_channel_group.conversations.return_value = mock_conversations

    cog.config.channel.return_value = mock_channel_group

    # Execute
    await cog.web_search(ctx, True)

    # Check save to channel config
    mock_channel_group.conversations.set.assert_called()

    # Verify prepare_for_storage call for content
    prepare_call = cog.conversation_manager.prepare_for_storage.call_args
    saved_data = prepare_call[0][0]

    assert "optimizer_settings" in saved_data
    assert saved_data["optimizer_settings"]["web_search_override"] is True
