import asyncio
from unittest.mock import MagicMock, patch

import discord
import pytest

# Mock tr
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key, **kwargs: key):
    from poehub.ui.home_view import (
        ConversationsButton,
        FunctionsButton,
        HomeMenuView,
        SettingsButton,
    )

def async_return(result=None):
    def side_effect(*args, **kwargs):
        f = asyncio.Future()
        f.set_result(result)
        return f
    return MagicMock(side_effect=side_effect)

@pytest.fixture
def mock_cog():
    cog = MagicMock()

    cog.config.use_dummy_api = async_return(False)
    cog._build_model_select_options = async_return([])
    cog._build_config_embed = async_return(discord.Embed())
    cog.bot.is_owner = async_return(False)
    cog.allow_dummy_mode = True

    # Manager check
    cog.conversation_manager = MagicMock() # not None

    return cog

@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.author.id = 12345
    ctx.send = async_return()
    return ctx

@pytest.mark.asyncio
@pytest.mark.filterwarnings("ignore:coroutine 'AsyncMockMixin._execute_mock_call' was never awaited")
class TestHomeView:
    async def test_view_init(self, mock_cog, mock_ctx):
        view = HomeMenuView(mock_cog, mock_ctx, "en")
        assert len(view.children) > 0

    async def test_interaction_check(self, mock_cog, mock_ctx):
        view = HomeMenuView(mock_cog, mock_ctx, "en")

        interaction = MagicMock()
        interaction.user.id = 12345
        assert await view.interaction_check(interaction) is True

        interaction.user.id = 999
        interaction.response = MagicMock()
        interaction.response.send_message = async_return()
        assert await view.interaction_check(interaction) is False

    async def test_settings_button(self, mock_cog, mock_ctx):
        btn = SettingsButton(mock_cog, mock_ctx, "en")

        # Patch PoeConfigView and HomeMenuView (for callback)
        with patch("poehub.ui.home_view.PoeConfigView") as MockConfigView, \
             patch("poehub.ui.home_view.HomeMenuView") as MockHomeView:

            mock_config_view = MagicMock()
            MockConfigView.return_value = mock_config_view

            interaction = MagicMock()
            interaction.response = MagicMock()
            interaction.edit_original_response = async_return()
            interaction.response.defer = async_return()

            await btn.callback(interaction)

            # Check initialization
            # Check initialization
            MockConfigView.assert_called()
            interaction.edit_original_response.assert_called()

            # Test back callback logic
            args = MockConfigView.call_args[1]
            back_cb = args.get('back_callback')
            assert back_cb is not None

            # Executing back callback
            inter_back = MagicMock()
            inter_back.response = MagicMock()
            inter_back.response.edit_message = async_return()
            await back_cb(inter_back)

            MockHomeView.assert_called()
            inter_back.response.edit_message.assert_called()

    async def test_conversations_button(self, mock_cog, mock_ctx):
        btn = ConversationsButton(mock_cog, mock_ctx, "en")

        with patch("poehub.ui.home_view.ConversationMenuView") as MockConvView, \
             patch("poehub.ui.home_view.HomeMenuView") as MockHomeView:

            mock_conv_view = MagicMock()
            mock_conv_view.refresh_content = async_return(discord.Embed())
            MockConvView.return_value = mock_conv_view

            interaction = MagicMock()
            interaction.response = MagicMock()
            interaction.edit_original_response = async_return()
            interaction.response.defer = async_return()

            await btn.callback(interaction)

            MockConvView.assert_called()
            mock_conv_view.refresh_content.assert_called()
            interaction.edit_original_response.assert_called()

            # Back callback check
            args = MockConvView.call_args[1]
            back_cb = args.get('back_callback')
            assert back_cb is not None

            inter_back = MagicMock()
            inter_back.response = MagicMock()
            inter_back.response.edit_message = async_return()
            await back_cb(inter_back)

            MockHomeView.assert_called()

    async def test_conversations_button_no_manager(self, mock_cog, mock_ctx):
        mock_cog.conversation_manager = None
        btn = ConversationsButton(mock_cog, mock_ctx, "en")

        interaction = MagicMock()
        interaction.response = MagicMock()
        interaction.response.send_message = async_return()
        await btn.callback(interaction)

        interaction.response.send_message.assert_called()
        # Ensure view not created
        with patch("poehub.ui.home_view.ConversationMenuView") as MockConvView:
             MockConvView.assert_not_called()

    async def test_functions_button(self, mock_cog, mock_ctx):
        btn = FunctionsButton(mock_cog, mock_ctx, "en")

        with patch("poehub.ui.home_view.FunctionsMenuView") as MockFuncView, \
             patch("poehub.ui.home_view.HomeMenuView") as MockHomeView:

            mock_func_view = MagicMock()
            MockFuncView.return_value = mock_func_view

            interaction = MagicMock()
            interaction.response = MagicMock()
            interaction.response.edit_message = async_return()

            await btn.callback(interaction)

            MockFuncView.assert_called()
            interaction.response.edit_message.assert_called()

            # Back callback
            args = MockFuncView.call_args[1]
            back_cb = args.get('back_callback')

            inter_back = MagicMock()
            inter_back.response = MagicMock()
            inter_back.response.edit_message = async_return()
            await back_cb(inter_back)
            MockHomeView.assert_called()

