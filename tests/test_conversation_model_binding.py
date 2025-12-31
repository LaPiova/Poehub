from unittest.mock import AsyncMock, MagicMock, Mock

import discord
import pytest

from poehub.services.chat import ChatService


@pytest.mark.asyncio
class TestConversationModelBinding:
    @pytest.fixture
    def mock_service(self):
        bot = Mock()
        config = Mock()
        billing = Mock()
        context = Mock()
        conv_manager = Mock()

        # Setup basic config mocks
        config.user.return_value.model = AsyncMock(return_value="default-gpt")
        config.channel.return_value.conversations = AsyncMock(return_value={})
        config.user_from_id.return_value.conversations = AsyncMock(return_value={})

        # Setup service
        service = ChatService(bot, config, billing, context, conv_manager)
        service.client = AsyncMock()  # Mock initialized client

        # Mock billing to pass
        billing.resolve_billing_guild = AsyncMock(return_value=Mock())
        billing.check_budget = AsyncMock(return_value=True)

        # Mock internal helpers
        service.get_conversation_messages = AsyncMock(return_value=[])
        service._resolve_quote_context = AsyncMock(return_value="")
        service._extract_image_urls = Mock(return_value=[])
        service.add_message_to_conversation = AsyncMock()
        service._determine_response_target = AsyncMock(return_value=Mock())
        service.stream_response = AsyncMock()

        # Mock optimizer
        service.optimizer = MagicMock()
        service.optimizer.optimize_request = AsyncMock(return_value={})

        # Fix missing context mock
        service.context.get_user_system_prompt = AsyncMock(return_value=None)

        return service

    async def test_uses_user_default_when_no_conv_model(self, mock_service):
        # Setup: convo exists but no model field
        mock_service.context.get_active_conversation_id = AsyncMock(return_value="conv1")
        mock_service._get_conversation = AsyncMock(return_value={"id": "conv1"})  # No model key

        user = Mock()
        user.id = 123
        message = Mock(author=user)

        await mock_service.process_chat_request(message, "Hello")

        # Check stream_response calls with user default
        mock_service.stream_response.assert_called_once()
        call_args = mock_service.stream_response.call_args[1]
        assert call_args["model"] == "default-gpt"

    async def test_uses_conversation_model(self, mock_service):
        # Setup: convo has specific model
        mock_service.context.get_active_conversation_id = AsyncMock(return_value="conv2")

        # Return conversation with specific model
        mock_service._get_conversation = AsyncMock(return_value={"id": "conv2", "model": "special-claude"})

        user = Mock()
        user.id = 123
        message = Mock(author=user)
        # Ensure it's treated as a DM so it uses user-scope conversation ID lookup
        message.channel = AsyncMock(spec=discord.DMChannel)

        await mock_service.process_chat_request(message, "Hello")

        # Check stream_response called with special model
        mock_service.stream_response.assert_called_once()
        call_args = mock_service.stream_response.call_args[1]
        assert call_args["model"] == "special-claude"

    async def test_fallback_if_conv_model_none(self, mock_service):
        # Setup: convo has model key but None
        mock_service.context.get_active_conversation_id = AsyncMock(return_value="conv3")
        mock_service._get_conversation = AsyncMock(return_value={"id": "conv3", "model": None})

        user = Mock()
        user.id = 123
        message = Mock(author=user)

        await mock_service.process_chat_request(message, "Hello")

        call_args = mock_service.stream_response.call_args[1]
        assert call_args["model"] == "default-gpt"
