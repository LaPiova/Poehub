from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import discord
import pytest

# Mock tr
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key, **kwargs: key):
    from poehub.ui.functions_view import FunctionsMenuView, SummaryButton

@pytest.fixture
def mock_cog():
    cog = MagicMock()
    return cog

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 12345
    return ctx

@pytest.mark.asyncio
class TestFunctionsView:
    async def test_view_init(self, mock_cog, mock_ctx):
        view = FunctionsMenuView(mock_cog, mock_ctx, "en")
        assert len(view.children) > 0

    async def test_interaction_check(self, mock_cog, mock_ctx):
        view = FunctionsMenuView(mock_cog, mock_ctx, "en")

        interaction = AsyncMock()
        interaction.user.id = 12345
        assert await view.interaction_check(interaction) is True

        interaction.user.id = 999
        interaction.response = AsyncMock()
        assert await view.interaction_check(interaction) is False

    async def test_summary_button(self, mock_cog, mock_ctx):
        btn = SummaryButton(mock_cog, mock_ctx, "en")

        # Mock view attached to button (FunctionsMenuView)
        mock_parent_view = MagicMock()
        mock_parent_view.back_callback = AsyncMock()

        with patch("poehub.ui.functions_view.SummaryView") as MockSummaryView, \
             patch("poehub.ui.functions_view.FunctionsMenuView") as MockFuncView:

            mock_summary_view = AsyncMock()
            mock_summary_view.build_embed.return_value = discord.Embed()
            MockSummaryView.return_value = mock_summary_view

            # Setup button view
            with patch.object(SummaryButton, 'view', new_callable=PropertyMock) as mp:
                mp.return_value = mock_parent_view

                interaction = AsyncMock()
                interaction.response.edit_message = AsyncMock()

                await btn.callback(interaction)

                MockSummaryView.assert_called()
                mock_summary_view.build_embed.assert_called()
                interaction.response.edit_message.assert_called()

                # Test Back Callback (go_back_to_functions)
                args = MockSummaryView.call_args[1]
                back_cb = args.get('back_callback')
                assert back_cb is not None

                # Execute Back Callback
                inter_back = AsyncMock()
                await back_cb(inter_back)

                MockFuncView.assert_called()
                # Verify back_callback passed to FuncView is the same one
                func_args = MockFuncView.call_args[1]
                assert func_args['back_callback'] == mock_parent_view.back_callback

                inter_back.response.edit_message.assert_called()
