
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from poehub.services.chat import ChatService


# Mock Redbot Config
@pytest.fixture
def mock_config():
    conf = MagicMock()

    # Mock Groups
    user_group = MagicMock()
    channel_group = MagicMock()

    # Mock user.conversations
    user_convs = {}

    async def get_user_convs():
        return user_convs

    async def set_user_convs(val):
        nonlocal user_convs
        user_convs.update(val)

    user_group.conversations = AsyncMock(side_effect=get_user_convs)
    user_group.conversations.set = AsyncMock(side_effect=set_user_convs)

    # Mock channel.conversations
    channel_convs = {}

    async def get_channel_convs():
        return channel_convs

    async def set_channel_convs(val):
        nonlocal channel_convs
        channel_convs.update(val)

    channel_group.conversations = AsyncMock(side_effect=get_channel_convs)
    channel_group.conversations.set = AsyncMock(side_effect=set_channel_convs)

    # Mock user.model
    user_group.model = AsyncMock(return_value="gpt-4")

    # Config accessors
    conf.user_from_id = MagicMock(return_value=user_group)
    conf.user = MagicMock(return_value=user_group)
    conf.channel = MagicMock(return_value=channel_group)

    return conf

@pytest.fixture
def mock_services(mock_config):
    bot = MagicMock()
    billing = MagicMock()
    context = MagicMock()
    # Mock context.get_active_conversation_id
    context.get_active_conversation_id = AsyncMock(return_value="conv1")
    context.get_user_system_prompt = AsyncMock(return_value=None)

    conversation_manager = MagicMock()
    # Mock manager behavior
    conversation_manager.process_conversation_data = lambda x: x
    conversation_manager.prepare_for_storage = lambda x: x
    conversation_manager.create_conversation = lambda x: {"messages": [], "title": "New Conv"}

    chat_service = ChatService(bot, mock_config, billing, context, conversation_manager)
    chat_service.client = MagicMock()
    chat_service.client.format_image_message = lambda content, urls: content
    chat_service.stream_response = AsyncMock()

    # Billing mocks
    billing.resolve_billing_guild = AsyncMock(return_value=MagicMock())
    billing.check_budget = AsyncMock(return_value=True)

    return chat_service

@pytest.mark.asyncio
async def test_process_chat_request_dm_scope(mock_services):
    """Test that DM messages are saved to USER scope."""
    service = mock_services

    # Mock Message (DM)
    message = AsyncMock()
    message.author.id = 123
    message.channel = AsyncMock(spec=discord.DMChannel)
    message.content = "Hello DM"
    message.reference = None

    # Execute
    await service.process_chat_request(message, "Hello DM")

    # Verify:
    # 1. Config.user_from_id was accessed
    service.config.user_from_id.assert_called_with(123)
    service.config.channel.assert_not_called()

    # 2. Add message called with user scope
    set_call = service.config.user_from_id(123).conversations.set
    assert set_call.called
    args = set_call.call_args[0][0]
    assert "conv1" in args
    assert args["conv1"]["messages"][-1]["content"] == "Hello DM"

@pytest.mark.asyncio
async def test_process_chat_request_thread_scope(mock_services):
    """Test that Thread messages are saved to CHANNEL scope."""
    service = mock_services

    # Mock Message (Thread)
    message = AsyncMock()
    message.author.id = 123
    thread_mock = MagicMock(spec=discord.Thread)
    thread_mock.id = 999
    message.channel = thread_mock
    message.content = "Hello Thread"
    message.reference = None

    # Helper to force determine_response_target to return the thread
    service._determine_response_target = AsyncMock(return_value=thread_mock)

    # Execute
    await service.process_chat_request(message, "Hello Thread")

    # Verify:
    # 1. Config.channel was accessed with thread object
    service.config.channel.assert_called_with(thread_mock)

    # 2. Check if message is in channel conversations
    set_call = service.config.channel(thread_mock).conversations.set
    assert set_call.called
    args = set_call.call_args[0][0]
    assert "default" in args # Threads use 'default' ID
    assert args["default"]["messages"][-1]["content"] == "Hello Thread"

@pytest.mark.asyncio
async def test_process_chat_request_creates_thread(mock_services):
    """Test that triggering a new thread moves context to the new thread."""
    service = mock_services

    # Mock Message (Text Channel Trigger)
    message = AsyncMock()
    message.author.id = 123
    text_channel = MagicMock(spec=discord.TextChannel)
    text_channel.id = 555
    message.content = "Bot start thread"
    message.reference = None

    # Mock creating a new thread
    new_thread = MagicMock(spec=discord.Thread)
    new_thread.id = 888
    service._determine_response_target = AsyncMock(return_value=new_thread)

    # Execute
    await service.process_chat_request(message, "Bot start thread")

    # Verify:
    # 1. Scope switch to New Thread object
    service.config.channel.assert_called_with(new_thread)

    # 2. Trigger message saved to New Thread history
    set_call = service.config.channel(new_thread).conversations.set
    assert set_call.called
    args = set_call.call_args[0][0]
    assert "default" in args
    assert args["default"]["messages"][-1]["content"] == "Bot start thread"

    # 3. User scope NOT touched for storage
    service.config.user_from_id(123).conversations.set.assert_not_called()

    # 4. Verify stream_response called with New Thread as target
    service.stream_response.assert_called_once()
    call_args = service.stream_response.call_args[1]
    assert call_args["target_channel"] == new_thread
    assert call_args["save_to_conv"][1] == "default"
