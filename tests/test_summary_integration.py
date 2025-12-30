from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from poehub.services.chat import ChatService
from poehub.ui.summary_view import SummaryView


@pytest.fixture
def mock_cog():
    cog = MagicMock()
    cog.config.user = MagicMock()
    mock_user_group = MagicMock()
    mock_user_group.model = AsyncMock(return_value="gpt-4o")
    cog.config.user.return_value = mock_user_group

    cog.config.channel = MagicMock()
    cog.chat_service = AsyncMock(spec=ChatService)
    # Use MagicMock for summarizer so side_effect generator is returned directly
    # instead of wrapped in a coroutine by AsyncMock
    cog.summarizer = MagicMock()
    cog.conversation_manager = MagicMock()
    return cog

@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.channel = AsyncMock(spec=discord.TextChannel)
    ctx.author.id = 12345
    ctx.guild = MagicMock()
    return ctx

@pytest.mark.asyncio
async def test_summary_pipeline_creates_thread_and_saves_history(mock_cog, mock_ctx):
    # Setup
    view = SummaryView(mock_cog, mock_ctx, "en-US")
    view.selected_hours = 1.0

    # Mock channel history
    mock_message = MagicMock()
    mock_message.content = "Test message"
    mock_message.author.display_name = "TestUser"
    mock_message.author.bot = False
    mock_message.created_at = datetime.now()

    # Mock generator for history
    async def mock_history(*args, **kwargs):
        yield mock_message

    mock_ctx.channel.send = AsyncMock()
    mock_ctx.channel.history = mock_history

    # Mock thread creation
    mock_thread = AsyncMock(spec=discord.Thread)
    mock_thread.id = 98765
    mock_ctx.channel.send.return_value.create_thread.return_value = mock_thread

    # Mock summarizer response
    async def mock_summarize(*args, **kwargs):
        yield "STATUS: Processing..."
        yield "RESULT: Summary content"

    mock_cog.summarizer.summarize_messages.side_effect = mock_summarize

    # Mock scope group
    mock_scope = AsyncMock()
    mock_cog.config.channel.return_value = mock_scope
    mock_scope.conversations.return_value = {} # Empty initially
    mock_scope.conversations.set = AsyncMock()

    from poehub.ui.summary_view import StartSummaryButton

    # Execution
    button = StartSummaryButton(mock_cog, mock_ctx, "en-US")
    # Mock view parent for the button? The button uses self.cog which is passed in init.
    # It doesn't seem to access self.view in _run_summary_pipeline, only in callback.
    # checking _run_summary_pipeline... it uses self.cog, self.ctx.

    await button._run_summary_pipeline(mock_ctx.channel, 1.0)

    # Assertions

    # 1. Verify thread creation
    mock_ctx.channel.send.return_value.create_thread.assert_awaited()

    # 2. Verify Config.channel called with thread object (not ID)
    mock_cog.config.channel.assert_called_with(mock_thread)

    # 3. Verify conversation initialization (model set)
    mock_scope.conversations.set.assert_awaited()

    # 4. Verify messages added to history via ChatService
    assert mock_cog.chat_service.add_message_to_conversation.call_count == 2

    # Trigger message
    call1 = mock_cog.chat_service.add_message_to_conversation.call_args_list[0]
    assert call1[0][3] == "user" # Role
    assert "Summarize" in call1[0][4] # Content
    assert call1[0][2] == f"channel:{mock_thread.id}:default" # Unique key

    # Assistant message
    call2 = mock_cog.chat_service.add_message_to_conversation.call_args_list[1]
    assert call2[0][3] == "assistant"
    assert "Summary content" in call2[0][4]

# Helper hack to access the method on the button which is dynamically bound?
# No, _run_summary_pipeline is on the StartSummaryButton class in the real code?
# Wait, let's check summary_view.py again.
# _run_summary_pipeline is a method of StartSummaryButton, NOT SummaryView.
# So I need to instantiate the button to test it.

