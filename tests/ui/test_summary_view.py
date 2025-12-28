from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import discord
import pytest

# Mock tr
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key, **kwargs: key):
    from poehub.ui.summary_view import (
        CustomTimeModal,
        StartSummaryButton,
        SummaryView,
        TimeRangeSelect,
    )

@pytest.fixture
def mock_cog():
    cog = MagicMock()
    # Mock config
    user_group = MagicMock()
    user_group.model = AsyncMock(return_value="gpt-4")
    cog.config.user.return_value = user_group

    # Summarizer
    cog.summarizer = MagicMock()

    # We need to mock summarize_messages to return async generator
    async def summary_gen(*args, **kwargs):
        yield "STATUS: Processing..."
        yield "RESULT: The summary content."

    # When mocking async generator method:
    cog.summarizer.summarize_messages = summary_gen

    # Chat Service
    cog.chat_service = MagicMock()
    cog.chat_service.send_split_message = AsyncMock()

    return cog

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 12345
    ctx.author.display_name = "User"
    ctx.guild = MagicMock()

    # Channel needs to be TextChannel for history
    channel = AsyncMock(spec=discord.TextChannel)
    channel.send = AsyncMock(return_value=AsyncMock()) # initial msg
    channel.history = MagicMock() # Will configure per test
    ctx.channel = channel

    return ctx

@pytest.mark.asyncio
class TestSummaryView:
    async def test_view_init(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        assert len(view.children) > 0
        assert view.selected_hours == 1.0

    async def test_time_range_select_standard(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        select = TimeRangeSelect("en")

        view.update_embed = AsyncMock()

        with patch.object(TimeRangeSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["6"]
            with patch.object(TimeRangeSelect, 'view', new_callable=PropertyMock) as mp:
                mp.return_value = view

                interaction = AsyncMock()
                await select.callback(interaction)

                assert view.selected_hours == 6.0
                view.update_embed.assert_called_with(interaction)

    async def test_time_range_select_custom(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        select = TimeRangeSelect("en")

        with patch.object(TimeRangeSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["custom"]
            with patch.object(TimeRangeSelect, 'view', new_callable=PropertyMock) as mp:
                mp.return_value = view

                interaction = AsyncMock()
                await select.callback(interaction)

                interaction.response.send_modal.assert_called()

    async def test_custom_time_modal_submit(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        view.update_embed = AsyncMock()

        modal = CustomTimeModal(mock_cog, mock_ctx, "en", view)
        modal.hours = Mock(value="10")

        interaction = AsyncMock()
        await modal.on_submit(interaction)

        assert view.selected_hours == 10.0
        view.update_embed.assert_called_with(interaction)

    async def test_custom_time_modal_invalid(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        modal = CustomTimeModal(mock_cog, mock_ctx, "en", view)

        modal.hours = Mock(value="invalid")
        interaction = AsyncMock()
        await modal.on_submit(interaction)
        interaction.response.send_message.assert_called() # error msg

        modal.hours = Mock(value="999") # too large
        await modal.on_submit(interaction)
        interaction.response.send_message.assert_called()

    async def test_start_summary_button_wrong_channel(self, mock_cog, mock_ctx):
        # mock_ctx.channel = AsyncMock() # Not TextChannel (e.g. DM)
        class NotTextChannel:
             pass
        mock_ctx.channel = NotTextChannel()

        btn = StartSummaryButton(mock_cog, mock_ctx, "en")
        view = SummaryView(mock_cog, mock_ctx, "en")

        with patch.object(StartSummaryButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = view
            interaction = AsyncMock()
            await btn.callback(interaction)

            interaction.response.send_message.assert_called()

    async def test_start_summary_pipeline_success(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        btn = StartSummaryButton(mock_cog, mock_ctx, "en")

        # Mock channel history
        mock_msg1 = MagicMock()
        mock_msg1.author.bot = False
        mock_msg1.content = "Msg 1"
        mock_msg1.author.display_name = "User 1" # Fix Pydantic
        mock_msg1.created_at = datetime.now(UTC)

        mock_msg2 = MagicMock()
        mock_msg2.author.bot = False
        mock_msg2.content = "Msg 2"
        mock_msg2.author.display_name = "User 2" # Fix Pydantic
        mock_msg2.created_at = datetime.now(UTC)

        async def history_gen(**kwargs):
             yield mock_msg1
             yield mock_msg2

        mock_ctx.channel.history.side_effect = history_gen

        # Initial message mock
        initial_msg = AsyncMock()
        initial_msg.create_thread = AsyncMock()
        mock_ctx.channel.send.return_value = initial_msg

        with patch.object(StartSummaryButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = view

            interaction = AsyncMock()
            interaction.edit_original_response = AsyncMock()

            await btn.callback(interaction)

            # Verify Flow
            interaction.response.defer.assert_called()
            mock_ctx.channel.send.assert_called()
            mock_ctx.channel.history.assert_called()
            mock_cog.chat_service.send_split_message.assert_called()
            args = mock_cog.chat_service.send_split_message.call_args[0]
            assert args[1] == "The summary content."
            initial_msg.create_thread.assert_called()

    async def test_pipeline_no_messages(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        btn = StartSummaryButton(mock_cog, mock_ctx, "en")

        async def empty_gen(**kwargs):
            if False:
                yield


        mock_ctx.channel.history.side_effect = empty_gen
        initial_msg = AsyncMock()
        mock_ctx.channel.send.return_value = initial_msg

        with patch.object(StartSummaryButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = view
            interaction = AsyncMock()
            await btn.callback(interaction)

            initial_msg.edit.assert_called()
            mock_cog.chat_service.send_split_message.assert_not_called()

    async def test_pipeline_summarizer_fail(self, mock_cog, mock_ctx):
        view = SummaryView(mock_cog, mock_ctx, "en")
        btn = StartSummaryButton(mock_cog, mock_ctx, "en")

        async def history_gen(**kwargs):
             msg = MagicMock()
             msg.author.bot = False
             msg.content = "A"
             msg.author.display_name = "User A" # Fix Pydantic
             msg.created_at = datetime.now(UTC)
             yield msg

        mock_ctx.channel.history.side_effect = history_gen
        initial_msg = AsyncMock()
        mock_ctx.channel.send.return_value = initial_msg

        async def fail_gen(*args, **kwargs):
             yield "STATUS: Thinking..."

        mock_cog.summarizer.summarize_messages = fail_gen

        with patch.object(StartSummaryButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = view
            interaction = AsyncMock()
            await btn.callback(interaction)

            mock_cog.chat_service.send_split_message.assert_not_called()
            initial_msg.edit.assert_called()

