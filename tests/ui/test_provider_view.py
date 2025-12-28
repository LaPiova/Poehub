from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest

# Mock tr
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key, **kwargs: key):
    from poehub.ui.provider_view import (
        APIKeyModal,
        CheckPricingButton,
        DefaultPromptModal,
        ManageAccessButton,
        ProviderConfigView,
        ProviderSelect,
        RefreshButton,
        SetDefaultPromptButton,
        SetKeyButton,
    )

@pytest.fixture
def mock_cog():
    cog = MagicMock()
    # Mock config
    cog.config.active_provider = AsyncMock(return_value="poe")
    cog.config.active_provider.set = AsyncMock()

    cog.config.use_dummy_api = AsyncMock(return_value=False)
    cog.config.use_dummy_api.set = AsyncMock()

    cog.config.provider_keys = AsyncMock(return_value={"poe": "key123"})
    cog.config.provider_keys.set = AsyncMock()

    cog.config.default_system_prompt.set = AsyncMock()

    # User config required for CheckPricing
    user_group = MagicMock()
    user_group.model = AsyncMock(return_value="gpt-4")
    cog.config.user.return_value = user_group

    cog.allow_dummy_mode = True
    cog._init_client = AsyncMock()

    return cog

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 12345
    return ctx

@pytest.mark.asyncio
class TestProviderView:
    async def test_view_init(self, mock_cog, mock_ctx):
        view = ProviderConfigView(mock_cog, mock_ctx, "en")
        assert len(view.children) > 0

    async def test_refresh_content(self, mock_cog, mock_ctx):
        view = ProviderConfigView(mock_cog, mock_ctx, "en")

        interaction = AsyncMock()
        interaction.response.edit_message = AsyncMock()

        await view.refresh_content(interaction)

        interaction.response.edit_message.assert_called()
        args = interaction.response.edit_message.call_args[1]
        assert 'embed' in args

    async def test_interaction_check(self, mock_cog, mock_ctx):
        view = ProviderConfigView(mock_cog, mock_ctx, "en")

        interaction = AsyncMock()
        interaction.user.id = 12345
        assert await view.interaction_check(interaction) is True

        interaction.user.id = 999
        interaction.response = AsyncMock()
        assert await view.interaction_check(interaction) is False

    async def test_provider_select_callback(self, mock_cog, mock_ctx):
        view = ProviderConfigView(mock_cog, mock_ctx, "en")
        select = ProviderSelect(mock_cog, mock_ctx, "en")
        view.refresh_content = AsyncMock()

        # Switch to OpenAI
        with patch.object(ProviderSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["openai"]
            with patch.object(ProviderSelect, 'view', new_callable=PropertyMock) as mp:
                mp.return_value = view

                interaction = AsyncMock()
                await select.callback(interaction)

                mock_cog.config.active_provider.set.assert_called_with("openai")
                mock_cog.config.use_dummy_api.set.assert_called_with(False)
                mock_cog._init_client.assert_called()
                view.refresh_content.assert_called()

    async def test_provider_select_dummy(self, mock_cog, mock_ctx):
        select = ProviderSelect(mock_cog, mock_ctx, "en")

        with patch.object(ProviderSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["dummy"]

            interaction = AsyncMock()
            await select.callback(interaction)

            mock_cog.config.use_dummy_api.set.assert_called_with(True)
            mock_cog._init_client.assert_called()

    async def test_provider_select_dummy_disabled(self, mock_cog, mock_ctx):
        mock_cog.allow_dummy_mode = False
        select = ProviderSelect(mock_cog, mock_ctx, "en")

        with patch.object(ProviderSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["dummy"]

            interaction = AsyncMock()
            await select.callback(interaction)

            interaction.response.send_message.assert_called_with(
                "❌ Dummy mode is disabled in this build.", ephemeral=True
            )
            mock_cog._init_client.assert_not_called()

    async def test_api_key_modal(self, mock_cog):
        modal = APIKeyModal(mock_cog, "poe", "en")
        modal.api_key = Mock(value="new_key")

        interaction = AsyncMock()
        await modal.on_submit(interaction)

        # Should set key
        # provider_keys mock returns dict, we need to verify set was called with updated dict?
        # The code does: keys = await keys(); keys[prov] = key; await keys.set(keys)
        # Since mock returns a new dict each time if not carefully managed, let's check basic call.
        mock_cog.config.provider_keys.set.assert_called()
        args = mock_cog.config.provider_keys.set.call_args[0][0]
        assert args["poe"] == "new_key"

        # Should re-init if active
        mock_cog._init_client.assert_called()
        interaction.response.send_message.assert_called()

    async def test_set_key_button(self, mock_cog, mock_ctx):
        btn = SetKeyButton(mock_cog, mock_ctx, "en")
        interaction = AsyncMock()
        await btn.callback(interaction)
        interaction.response.send_modal.assert_called()

        # Dummy check
        mock_cog.config.active_provider.return_value = "dummy"
        interaction = AsyncMock()
        await btn.callback(interaction)
        interaction.response.send_message.assert_called() # Warn dummy no key

    async def test_manage_access_button(self, mock_cog, mock_ctx):
        btn = ManageAccessButton(mock_cog, mock_ctx, "en")

        # Patch AccessControlView
        with patch("poehub.ui.provider_view.AccessControlView") as MockClass:
            mock_view = AsyncMock()
            MockClass.return_value = mock_view

            interaction = AsyncMock()
            await btn.callback(interaction)

            MockClass.assert_called()
            mock_view.update_view.assert_called_with(interaction)

    async def test_check_pricing_button(self, mock_cog):
        btn = CheckPricingButton(mock_cog, "en")

        # Mock PricingOracle
        with patch("poehub.services.billing.oracle.PricingOracle.get_price") as mock_price:
            mock_price.return_value = (5.0, 15.0, "USD")

            interaction = AsyncMock()
            interaction.user = Mock()
            await btn.callback(interaction)

            interaction.response.send_message.assert_called()
            args = interaction.response.send_message.call_args[1]
            embed = args['embed']
            assert "$5.00" in str(embed.fields)

    async def test_set_default_prompt_flow(self, mock_cog, mock_ctx):
        # Button
        btn = SetDefaultPromptButton(mock_cog, mock_ctx, "en")
        interaction = AsyncMock()
        await btn.callback(interaction)
        interaction.response.send_modal.assert_called()

        # Modal
        modal = DefaultPromptModal(mock_cog, "en")
        modal.prompt = Mock(value="Default Sys")
        interaction = AsyncMock()
        await modal.on_submit(interaction)

        mock_cog.config.default_system_prompt.set.assert_called_with("Default Sys")
        interaction.response.send_message.assert_called()

    async def test_refresh_button(self, mock_cog):
        btn = RefreshButton("en")
        # But isinstance check requires type. MagicMock might pass if spec set?
        # Safer: real view or patch isinstance?
        # Or mock the 'view' attribute and just run.
        # However, button code: `if isinstance(self.view, ProviderConfigView):`
        # Using real class stub?

        class FakeProviderView(ProviderConfigView):
             pass

        # Create a mock view that is ALSO an instance of ProviderConfigView (to pass assertions if any)
         # Just bypass checks if needed, but interaction.view is usually expected.
        # spec doesn't make isinstance true

        # We can just use ProviderConfigView but we need to init it.
        # Or patch isinstance? No.
        # Just use patch.object on RefreshButton.view to return a mock that "looks like" ProviderConfigView?
        # isinstance checks inheritance.
        # Let's use `MagicMock(spec=ProviderConfigView)`? No.
        # Let's create a dummy class that inherits.
        dummy_view = ProviderConfigView(mock_cog, AsyncMock(), "en")
        dummy_view.refresh_content = AsyncMock()

        with patch.object(RefreshButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = dummy_view

            interaction = AsyncMock()
            await btn.callback(interaction)

            dummy_view.refresh_content.assert_called_with(interaction)
