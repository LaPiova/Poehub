
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from poehub.services.chat import ChatService
from poehub.services.optimizer import RequestOptimizer


@pytest.fixture
def mock_optimizer():
    optimizer = MagicMock(spec=RequestOptimizer)
    optimizer.optimize_request = AsyncMock(return_value={"web_search_override": True})
    return optimizer

@pytest.fixture
def mock_chat_deps():
    bot = MagicMock()
    config = MagicMock()
    billing = MagicMock()
    context = MagicMock()

    # Mock conversation storage behavior
    storage = MagicMock()
    storage.prepare_for_storage.side_effect = lambda x: x # Identity for "encrypt"
    storage.process_conversation_data.side_effect = lambda x: x # Identity for "decrypt"
    storage.create_conversation.return_value = {"messages": [], "id": "default"}
    storage.clear_messages = MagicMock(side_effect=lambda x: {"messages": [], "id": x["id"]}) # Simulate clear dropping keys?
    # Actually storage.clear_messages modifies in place usually or returns modified.
    # We should match the real implementation logic or mock it to behave similarly.
    # Real implementation pops the key.
    def clear_impl(conv):
        conv["messages"] = []
        conv.pop("optimizer_settings", None)
        return conv
    storage.clear_messages.side_effect = clear_impl

    return bot, config, billing, context, storage

@pytest.mark.asyncio
async def test_optimizer_persistence(mock_chat_deps, mock_optimizer):
    bot, config, billing, context, storage = mock_chat_deps

    chat_service = ChatService(bot, config, billing, context, storage)
    chat_service.optimizer = mock_optimizer
    chat_service.client = MagicMock() # Mock client to avoid init error check

    # Mock conversation flow helpers
    # We need to mock _get_or_create_conversation to duplicate stateful behavior
    # Simplest way is to define a dict for "config" storage

    async def get_conv(user_id, conv_id): # Signature match _get_conversation
         # Wait, _get_conversation takes different args depending on implementation?
         # In ChatService it calls self._get_conversation(scope_group, conv_id)

         # Let's mock the internal methods directly for easier testing of the logic flow
         pass

    # We will mock _get_or_create_conversation and _save_conversation
    # to simulate simple storage

    current_conv = {"id": "123", "messages": []}

    chat_service._get_or_create_conversation = AsyncMock(return_value=current_conv)
    chat_service._save_conversation = AsyncMock()
    chat_service.stream_response = AsyncMock()
    chat_service._resolve_quote_context = AsyncMock(return_value="")
    chat_service._determine_response_target = AsyncMock()
    chat_service.get_conversation_messages = AsyncMock(return_value=[])
    chat_service.add_message_to_conversation = AsyncMock()
    chat_service.context.get_active_conversation_id = AsyncMock(return_value="default")
    chat_service.billing.resolve_billing_guild = AsyncMock(return_value=MagicMock())
    chat_service.billing.check_budget = AsyncMock(return_value=True)

    # 1. First Request - Should call optimizer
    message = MagicMock()
    message.author.id = 1

    # Configure config.user_from_id(id).conversations() to be awaitable
    mock_config_group = MagicMock()
    mock_config_group.conversations = AsyncMock(return_value={})
    config.user_from_id.return_value = mock_config_group
    config.channel.return_value = mock_config_group
    config.user.return_value.model = AsyncMock(return_value="gpt-4")

    chat_service.context.get_user_system_prompt = AsyncMock(return_value="")

    await chat_service.process_chat_request(message, "Hello")

    mock_optimizer.optimize_request.assert_awaited_once()
    assert "optimizer_settings" in current_conv
    assert current_conv["optimizer_settings"] == {"web_search_override": True}
    chat_service._save_conversation.assert_called()

    # Verify stream_response received the settings
    _, kwargs = chat_service.stream_response.call_args
    assert kwargs.get("web_search_override") is True

    # 2. Second Request - Should NOT call optimizer
    mock_optimizer.optimize_request.reset_mock()
    await chat_service.process_chat_request(message, "Follow up")

    mock_optimizer.optimize_request.assert_not_called()

    # 3. Clear History (Simulation)
    # We test that if we call storage.clear_messages, the key is gone
    storage.clear_messages(current_conv)
    assert "optimizer_settings" not in current_conv

    # 4. Request after clear - Should call optimizer again
    await chat_service.process_chat_request(message, "New Topic")
    mock_optimizer.optimize_request.assert_awaited_once()

@pytest.mark.asyncio
async def test_api_client_default_behavior():
    # This verifies the api_client.py change we made
    from poehub.api_client import OpenAIProvider
    with patch("poehub.api_client.AsyncOpenAI"):
        client = OpenAIProvider("key")
        client.client = MagicMock()
        client._create_stream = AsyncMock()

        # Call without kwargs
        async for _ in client.stream_chat("model", []):
            pass
        call_kwargs = client._create_stream.call_args[1]

        # extra_body should NOT be present
        assert "extra_body" not in call_kwargs or not call_kwargs["extra_body"]

        # Call with kwargs
        async for _ in client.stream_chat("model", [], web_search_override=True):
            pass
        call_kwargs = client._create_stream.call_args[1]

        assert "extra_body" in call_kwargs
        assert call_kwargs["extra_body"]["web_search"] is True


