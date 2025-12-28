from unittest.mock import AsyncMock, Mock

import discord
import pytest

from poehub.models import MessageData
from poehub.ui.summary_view import StartSummaryButton, SummaryView


@pytest.mark.asyncio
class TestSummaryView:
    @pytest.fixture
    def mock_cog(self):
        cog = Mock()
        # Mock attributes required by IPoeHub
        cog.chat_service = Mock()
        cog.chat_service.stream_response = AsyncMock()
        cog.chat_service.send_split_message = AsyncMock()
        cog.summarizer = Mock()
        cog.summarizer.summarize_messages = AsyncMock()
        cog.config = Mock()
        cog.bot = Mock()
        return cog

    @pytest.fixture
    def mock_ctx(self):
        ctx = Mock()
        ctx.author.id = 123
        ctx.channel = AsyncMock(spec=discord.TextChannel)
        ctx.guild = Mock(spec=discord.Guild)
        return ctx

    async def test_init(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        assert view is not None

    async def test_start_summary_button_callback(self, mock_cog, mock_ctx):
        # Setup
        view = SummaryView(mock_cog, mock_ctx, "en")
        # Get the actual button instance attached to the view
        button = next(child for child in view.children if isinstance(child, StartSummaryButton))

        interaction = AsyncMock(spec=discord.Interaction)
        interaction.response = AsyncMock()
        interaction.edit_original_response = AsyncMock()

        # Mock message producer to return some dummy messages
        async def mock_producer(*args, **kwargs):
            yield [
                MessageData(
                    author="User", content="Hello", timestamp="2023-01-01 12:00"
                )
            ]

        button._fetch_messages_producer = mock_producer

        # Mock config model
        mock_user_conf = Mock()
        mock_user_conf.model = AsyncMock(return_value="gpt-4")
        mock_cog.config.user.return_value = mock_user_conf

        # Mock summarizer generator
        async def mock_summarize(*args, **kwargs):
            yield "STATUS: Thinking..."
            yield "RESULT: Final Summary Text"

        mock_cog.summarizer.summarize_messages = mock_summarize

        # Execute
        await button.callback(interaction)

        # Verify summarizer called
        # mock_cog.summarizer.summarize_messages.assert_called_once() # Can't assert called on generator func easily if mocked this way,
        # normally we assert on the mock that returned the generator, but here I replaced the method.
        # Let's assume verifying the output call implies it worked.

        # Verify send_split_message called with result
        args, kwargs = mock_cog.chat_service.send_split_message.call_args
        assert args[1] == "Final Summary Text"
