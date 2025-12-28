import pytest
from unittest.mock import AsyncMock, Mock
from poehub.ui.home_view import HomeMenuView
from poehub.i18n import LANG_EN

@pytest.mark.asyncio
async def test_home_view_init():
    mock_cog = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.author.id = 12345
    
    view = HomeMenuView(mock_cog, mock_ctx, LANG_EN)
    
    # Needs: Settings, Conversations, Close
    assert len(view.children) == 3
    
    labels = [child.label for child in view.children]
    assert "Settings" in labels
    assert "Conversations" in labels
    assert "Close" in labels

@pytest.mark.asyncio
async def test_home_view_interaction_check():
    mock_context = AsyncMock()
    mock_context.author.id = 12345
    
    mock_cog = AsyncMock()
    view = HomeMenuView(mock_cog, mock_context, LANG_EN)
    
    # Authorized
    mock_interaction = AsyncMock()
    mock_interaction.user.id = mock_context.author.id
    assert await view.interaction_check(mock_interaction) is True
    
    # Unauthorized
    mock_interaction.user.id = 999
    assert await view.interaction_check(mock_interaction) is False
    mock_interaction.response.send_message.assert_called_once()
