from unittest.mock import AsyncMock, Mock

import pytest

from poehub.core.i18n import LANG_EN
from poehub.ui.conversation_view import ConversationMenuView, DeleteButton


@pytest.mark.asyncio
async def test_delete_button_callback_success():
    """Test successful deletion of a conversation."""
    mock_cog = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.author.id = 12345

    # Mock manager exists
    mock_cog.conversation_manager = Mock()

    # Mock context service
    mock_cog.context_service = Mock()
    mock_cog.context_service.get_active_conversation_id = AsyncMock(return_value="conv_123")
    mock_cog.context_service.set_active_conversation_id = AsyncMock()

    mock_cog._get_conversation.return_value = {"title": "Test Chat"}
    mock_cog._delete_conversation.return_value = True

    button = DeleteButton(mock_cog, mock_ctx, LANG_EN)

    # Mock interaction
    mock_interaction = AsyncMock()
    # Mock view for refresh
    mock_view = AsyncMock(spec=ConversationMenuView)
    button._view = mock_view

    await button.callback(mock_interaction)

    # Verify logic
    mock_cog.context_service.get_active_conversation_id.assert_called_with(12345)
    mock_cog._delete_conversation.assert_called_with(12345, "conv_123")
    mock_cog.context_service.set_active_conversation_id.assert_called_with(12345, "default")

    # Verify response
    mock_interaction.response.send_message.assert_called_once()
    args, kwargs = mock_interaction.response.send_message.call_args
    assert "Deleted" in args[0] or "Deleted" in str(kwargs)  # Simplified check

    # Verify refresh
    mock_view.refresh_content.assert_called_once()


@pytest.mark.asyncio
async def test_delete_button_default_fail():
    """Test failure when trying to delete default conversation."""
    mock_cog = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.author.id = 12345
    mock_cog.conversation_manager = Mock()

    # Active is default
    mock_cog.context_service = Mock()
    mock_cog.context_service.get_active_conversation_id = AsyncMock(return_value="default")

    button = DeleteButton(mock_cog, mock_ctx, LANG_EN)
    mock_interaction = AsyncMock()

    await button.callback(mock_interaction)

    # Should NOT call delete
    mock_cog._delete_conversation.assert_not_called()

    # Verify fail message
    mock_interaction.response.send_message.assert_called_once()
    # We expect a failure message about default
