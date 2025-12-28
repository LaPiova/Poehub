from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest

from poehub.services.chat import ChatService


@pytest.mark.asyncio
class TestChatService:
    @pytest.fixture
    def mock_bot(self):
        return Mock()

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.use_dummy_api = AsyncMock(return_value=False)
        config.active_provider = AsyncMock(return_value="poe")
        config.provider_keys = AsyncMock(return_value={"poe": "key"})
        config.provider_urls = AsyncMock(return_value={})
        config.api_key = AsyncMock(return_value=None)
        config.base_url = AsyncMock(return_value=None)
        return config

    @pytest.fixture
    def mock_billing(self):
        return Mock()

    @pytest.fixture
    def mock_context(self):
        return Mock()

    @pytest.fixture
    def mock_conv_manager(self):
        return Mock()

    @pytest.fixture
    def service(
        self, mock_bot, mock_config, mock_billing, mock_context, mock_conv_manager
    ):
        return ChatService(
            mock_bot, mock_config, mock_billing, mock_context, mock_conv_manager
        )

    async def test_initialize_client_dummy(self, service, mock_config):
        mock_config.use_dummy_api.return_value = True

        with patch("poehub.services.chat.get_client") as mock_get_client:
            await service.initialize_client()
            mock_get_client.assert_called_with("dummy", "dummy")

    async def test_initialize_client_poe(self, service, mock_config):
        mock_config.use_dummy_api.return_value = False
        mock_config.active_provider.return_value = "poe"
        mock_config.provider_keys.return_value = {"poe": "test_key"}

        with patch("poehub.services.chat.get_client") as mock_get_client:
            await service.initialize_client()
            mock_get_client.assert_called()
            args, _ = mock_get_client.call_args
            assert args[0] == "poe"
            assert args[1] == "test_key"

    async def test_process_chat_request_no_client(self, service):
        service.client = None
        ctx = AsyncMock()
        await service.process_chat_request(Mock(), "hi", ctx)
        ctx.send.assert_called()

    async def test_process_chat_request_flow(
        self, service, mock_config, mock_billing, mock_context
    ):
        # Setup dependencies
        service.client = AsyncMock()
        service.client.format_image_message.return_value = "formatted"
        service.stream_response = AsyncMock()

        # Mocks
        message = AsyncMock(spec=discord.Message)
        message.content = "hello"
        message.channel = AsyncMock(spec=discord.TextChannel)
        message.author.id = 123
        message.attachments = []
        message.reference = None

        # Config mocks
        mock_user_conf = Mock()
        mock_config.user.return_value = mock_user_conf
        mock_user_conf.model = AsyncMock(return_value="gpt-4")

        # Context mocks
        mock_context.get_active_conversation_id = AsyncMock(return_value="conv1")
        mock_context.get_user_system_prompt = AsyncMock(return_value=None)

        # Billing mocks
        guild = Mock(spec=discord.Guild)
        mock_billing.resolve_billing_guild = AsyncMock(return_value=guild)
        mock_billing.check_budget = AsyncMock(return_value=True)

        # Internal mocks
        service._get_conversation_messages = AsyncMock(return_value=[])
        service._add_message_to_conversation = AsyncMock()
        service._determine_response_target = AsyncMock(return_value=message.channel)
        service._resolve_quote_context = AsyncMock(return_value="")

        # Execute
        await service.process_chat_request(message, "hello", None)

        # Verify
        service.stream_response.assert_called_once()
        service._add_message_to_conversation.assert_called()

    async def test_split_message(self, service):
        long_content = "a" * 3000
        chunks = service._split_message(long_content, max_length=1900)
        assert len(chunks) > 1
        assert len(chunks[0]) <= 2000
