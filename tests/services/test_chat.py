from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest

from poehub.models import TokenUsage
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
        config.provider_keys.set = AsyncMock()
        config.provider_urls = AsyncMock(return_value={})
        config.api_key = AsyncMock(return_value=None)
        config.base_url = AsyncMock(return_value=None)

        # User config mocks
        user_conf = Mock()
        user_conf.model = AsyncMock(return_value="gpt-4")
        user_conf.conversations = AsyncMock(return_value={})
        user_conf.conversations.set = AsyncMock()
        config.user_from_id.return_value = user_conf
        config.user.return_value = user_conf

        return config

    @pytest.fixture
    def mock_billing(self):
        billing = Mock()
        billing.resolve_billing_guild = AsyncMock()
        billing.check_budget = AsyncMock(return_value=True)
        billing.update_spend = AsyncMock()
        return billing

    @pytest.fixture
    def mock_context(self):
        ctx = Mock()
        ctx.get_active_conversation_id = AsyncMock(return_value="conv1")
        ctx.get_user_system_prompt = AsyncMock(return_value=None)
        return ctx

    @pytest.fixture
    def mock_conv_manager(self):
        mgr = Mock()
        mgr.process_conversation_data.side_effect = lambda x: x
        mgr.create_conversation.return_value = {"messages": []}
        mgr.prepare_for_storage.side_effect = lambda x: x
        mgr.add_message.return_value = {"messages": ["msg"]}
        mgr.get_api_messages.return_value = []
        return mgr

    @pytest.fixture
    def service(
        self, mock_bot, mock_config, mock_billing, mock_context, mock_conv_manager
    ):
        return ChatService(
            mock_bot, mock_config, mock_billing, mock_context, mock_conv_manager
        )

    # ... Previous tests ...

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

    async def test_initialize_client_migration(self, service, mock_config):
        mock_config.provider_keys.return_value = {}
        mock_config.api_key.return_value = "legacy_key"
        mock_config.active_provider.return_value = "poe"

        with patch("poehub.services.chat.get_client") as mock_get_client:
            await service.initialize_client()
            mock_config.provider_keys.set.assert_called()
            mock_get_client.assert_called_with("poe", "legacy_key", None)

    async def test_get_matching_models(self, service):
        service.client = AsyncMock()
        service.client.get_models.return_value = [{"id": "gpt-4"}, {"id": "claude-3"}]
        models = await service.get_matching_models(query="gpt")
        assert len(models) == 1
        assert models[0] == "gpt-4"

    async def test_get_matching_models_no_client(self, service):
        service.client = None
        models = await service.get_matching_models()
        assert models == []

    async def test_process_chat_request_billing_fail(self, service, mock_billing):
        service.client = AsyncMock()
        mock_billing.resolve_billing_guild.return_value = Mock(spec=discord.Guild)
        mock_billing.check_budget.return_value = False
        ctx = AsyncMock()
        await service.process_chat_request(Mock(), "hi", ctx)
        ctx.send.assert_called()

    async def test_process_chat_request_no_guild(self, service, mock_billing):
        service.client = AsyncMock()
        mock_billing.resolve_billing_guild.return_value = None
        ctx = AsyncMock()
        await service.process_chat_request(Mock(channel=Mock()), "hi", ctx)
        ctx.send.assert_called()

    async def test_process_chat_request_flow(self, service):
        service.client = AsyncMock()
        service.client.format_image_message.return_value = "content"

        # Mock internal helpers to isolate flow
        with patch.object(service, "stream_response", new_callable=AsyncMock) as mock_stream:
           with patch.object(service, "_resolve_quote_context", return_value=""):
               with patch.object(service, "_extract_image_urls", return_value=[]):
                   with patch.object(service, "_add_message_to_conversation", new_callable=AsyncMock):
                       with patch.object(service, "_determine_response_target", new_callable=AsyncMock):
                            message = AsyncMock(spec=discord.Message)
                            message.channel = AsyncMock(spec=discord.TextChannel)
                            await service.process_chat_request(message, "hello", None)
                            mock_stream.assert_called_once()

    async def test_get_response(self, service):
        # Test non-streaming response
        service.client = AsyncMock()

        async def mock_stream(*args):
            yield "Response"
            yield TokenUsage(input_tokens=1, output_tokens=1, cost=0.1)

        service.client.stream_chat = mock_stream

        response = await service.get_response(messages=[], model="gpt-4")
        assert response == "Response"

    async def test_get_response_billing(self, service, mock_billing):
        service.client = AsyncMock()
        mock_guild = Mock(spec=discord.Guild)

        async def mock_stream(*args):
            yield "Response"
            yield TokenUsage(input_tokens=10, output_tokens=10, cost=0.5, currency="USD")

        service.client.stream_chat = mock_stream

        response = await service.get_response(
            messages=[], model="gpt-4", billing_guild=mock_guild
        )
        assert response == "Response"
        mock_billing.update_spend.assert_called_with(mock_guild, 0.5, currency="USD")

    async def test_get_response_error(self, service):
        service.client = AsyncMock()
        service.client.stream_chat = Mock(side_effect=Exception("Boom"))

        with pytest.raises(Exception, match="Boom"):
            await service.get_response(messages=[], model="gpt-4")

    async def test_stream_response(self, service, mock_billing):
        service.client = AsyncMock()
        # Mock stream_chat: it must be a callable that returns an async iterable
        async def mock_stream(*args):
            yield "Hello"
            yield " World"
            yield TokenUsage(input_tokens=10, output_tokens=10, cost=0.01)
        service.client.stream_chat = mock_stream

        target_channel = AsyncMock()
        response_msg = AsyncMock()
        target_channel.send.return_value = response_msg

        await service.stream_response(
            ctx=None,
            messages=[],
            model="gpt-4",
            target_channel=target_channel,
            billing_guild=Mock(spec=discord.Guild)
        )
        assert response_msg.edit.call_count >= 1
        mock_billing.update_spend.assert_called_once()

    async def test_stream_response_pacing_and_save(self, service):
        service.client = AsyncMock()
        async def mock_stream(*args):
            yield "Part 1"
            yield "Part 2"
        service.client.stream_chat = mock_stream

        target_channel = AsyncMock()
        response_msg = AsyncMock()
        target_channel.send.return_value = response_msg

        # Mock time to simulate passage of 2+ seconds between chunks
        with patch("poehub.services.chat.time.time", side_effect=[100, 103, 106, 110]):
            # Initial time, loop 1 time, loop 2 time (trigger update), final
            with patch.object(service, "_add_message_to_conversation", new_callable=AsyncMock) as mock_add:
                await service.stream_response(
                    ctx=None,
                    messages=[],
                    model="gpt-4",
                    target_channel=target_channel,
                    save_to_conv=(123, "c1")
                )

                # Verify edits happened due to pacing
                assert response_msg.edit.call_count >= 1
                # Verify save called
                mock_add.assert_called_with(
                    123, "c1", "assistant", "Part 1Part 2"
                )

    async def test_stream_response_error(self, service):
        service.client = AsyncMock()
        # Mock stream_chat to raise Exception when called (simulating immediate failure)
        # It should be a Mock, not AsyncMock, because ChatService calls it synchronously to get the iterator
        service.client.stream_chat = Mock(side_effect=Exception("API error"))

        target_channel = AsyncMock()
        target_channel.send.return_value = AsyncMock()

        await service.stream_response(
            ctx=None, messages=[], model="gpt-4", target_channel=target_channel
        )
        # Check that error message was sent
        args = target_channel.send.call_args[0]
        assert "Error communicating with Poe API" in args[0]
        assert "API error" in args[0]

    async def test_split_message(self, service):
        text = "12345" * 400
        chunks = service._split_message(text, max_length=100)
        assert len(chunks) > 1
        assert len(chunks[0]) <= 130

    async def test_resolve_quote_context(self, service):
        # Mock logic
        message = Mock(spec=discord.Message)
        message.reference = Mock()
        message.reference.message_id = 123
        message.reference.cached_message = None
        ref_msg = Mock(content="quoted text")
        ref_msg.author.display_name = "UserB"
        message.channel.fetch_message = AsyncMock(return_value=ref_msg)

        ctx_str = await service._resolve_quote_context(message)
        assert 'UserB: "quoted text"' in ctx_str

    async def test_extract_image_urls(self, service):
        message = Mock(spec=discord.Message)
        att = Mock()
        att.content_type = "image/png"
        att.url = "http://img"
        message.attachments = [att]
        message.reference = None

        urls = service._extract_image_urls(message)
        assert urls == ["http://img"]

        # Test reference
        message.attachments = []
        ref_msg = Mock()
        ref_msg.attachments = [att]
        message.reference = Mock()
        message.reference.cached_message = ref_msg

        urls = service._extract_image_urls(message)
        assert urls == ["http://img"]

    async def test_determine_response_target_thread(self, service):
        message = AsyncMock(spec=discord.Message)
        channel = AsyncMock(spec=discord.TextChannel)
        thread = AsyncMock(spec=discord.Thread)
        message.create_thread.return_value = thread

        target = await service._determine_response_target(message, channel, "topic")
        assert target == thread

    async def test_conversation_helpers(self, service, mock_conv_manager):
        user_id = 999
        conv_id = "c1"
        res = await service._get_conversation(user_id, conv_id)
        assert res is None
        await service._save_conversation(user_id, conv_id, {"msg": "foo"})
        # Should call config set
