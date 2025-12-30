from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest

# Mock tr before import
# Use side_effect to return key if possible, but if not working, we adjust assertions.
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key: key):
    from poehub.ui.access_view import (
        AccessControlView,
        BackButton,
        BudgetLimitModal,
        GuildSelect,
        ResetSpendButton,
        ToggleAccessButton,
    )

@pytest.fixture
def mock_cog():
    cog = MagicMock()
    # Mock bot.guilds
    guild1 = MagicMock()
    guild1.name = "Alpha"
    guild1.id = 101
    guild2 = MagicMock()
    guild2.name = "Beta"
    guild2.id = 102

    cog.bot.guilds = [guild1, guild2]
    cog.bot.get_guild.side_effect = lambda id: guild1 if id == 101 else guild2

    # Mock config
    mock_group = MagicMock()

    def create_config_item(return_val=None):
        item = AsyncMock(return_value=return_val)
        item.set = AsyncMock()
        return item

    mock_group.access_allowed = create_config_item(False)
    mock_group.monthly_limit = create_config_item(5.0)
    mock_group.current_spend = create_config_item(1.5)
    mock_group.monthly_limit_points = create_config_item(1000)
    mock_group.current_spend_points = create_config_item(500)
    mock_group.allowed_roles = create_config_item([])

    cog.config.guild.return_value = mock_group

    return cog

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 12345
    return ctx

@pytest.mark.asyncio
class TestAccessControl:
    async def test_access_view_init(self, mock_cog, mock_ctx):
        view = AccessControlView(mock_cog, mock_ctx, "en")
        assert len(view.children) > 0
        assert isinstance(view.children[0], GuildSelect)

    async def test_interaction_check(self, mock_cog, mock_ctx):
        view = AccessControlView(mock_cog, mock_ctx, "en")

        # Valid user
        interaction = AsyncMock()
        interaction.user.id = 12345
        assert await view.interaction_check(interaction) is True

        # Invalid user
        interaction.user.id = 999
        interaction.response = AsyncMock()
        assert await view.interaction_check(interaction) is False
        # tr might return key 'RESTRICTED_MENU' or real text 'This menu...'
        # We assert called.
        interaction.response.send_message.assert_called()
        args = interaction.response.send_message.call_args[0]
        assert "menu" in args[0] or "RESTRICTED" in args[0]

    async def test_guild_select_callback(self, mock_cog, mock_ctx):
        view = AccessControlView(mock_cog, mock_ctx, "en")
        select = view.children[0]

        # Mock 'values' property
        with patch.object(GuildSelect, 'values', new_callable=PropertyMock) as mock_vals:
            mock_vals.return_value = ["101"]

            # Use real view object
            # select.view = view  <-- Read-only property, removed

            # Use patch to mock view property
            with patch.object(GuildSelect, 'view', new_callable=PropertyMock) as mock_view_prop:
                mock_view_prop.return_value = view

                interaction = AsyncMock()
                interaction.response.edit_message = AsyncMock()

                await select.callback(interaction)

        assert view.active_guild.id == 101

    async def test_toggle_access(self, mock_cog, mock_ctx):
        view = AccessControlView(mock_cog, mock_ctx, "en")
        view.active_guild = mock_cog.bot.guilds[0]

        btn = ToggleAccessButton(mock_cog, "en")

        with patch.object(ToggleAccessButton, 'view', new_callable=PropertyMock) as mock_view:
            mock_view.return_value = view

            interaction = AsyncMock()
            await btn.callback(interaction)

            mock_cog.config.guild(view.active_guild).access_allowed.set.assert_called_with(True)
            interaction.response.edit_message.assert_called()

    async def test_reset_spend(self, mock_cog, mock_ctx):
        view = AccessControlView(mock_cog, mock_ctx, "en")
        view.active_guild = mock_cog.bot.guilds[0]

        btn = ResetSpendButton(mock_cog, "en")

        with patch.object(ResetSpendButton, 'view', new_callable=PropertyMock) as mock_view:
            mock_view.return_value = view

            interaction = AsyncMock()
            await btn.callback(interaction)

            mock_cog.config.guild(view.active_guild).current_spend.set.assert_called_with(0.0)

    async def test_budget_modal_submit(self, mock_cog, mock_ctx):
        view = AccessControlView(mock_cog, mock_ctx, "en")
        guild = mock_cog.bot.guilds[0]

        modal = BudgetLimitModal(mock_cog, guild, view)

        interaction = AsyncMock()
        # is_done is a property or regular method, not async
        interaction.response.is_done = Mock(return_value=False)

        view.update_view = AsyncMock()

        # Patch input values using patch.object on the instances
        # Since Modal creates inputs in init: self.usd_input = ...
        # self.usd_input is TextInput instance.
        # We can just replace the TextInput instance with a Mock that has .value
        modal.usd_input = Mock()
        modal.usd_input.value = "10.50"

        modal.pts_input = Mock()
        modal.pts_input.value = "1000"

        await modal.on_submit(interaction)

        mock_cog.config.guild(guild).monthly_limit.set.assert_called_with(10.5)

    async def test_budget_modal_invalid(self, mock_cog, mock_ctx):
        guild = mock_cog.bot.guilds[0]
        modal = BudgetLimitModal(mock_cog, guild, Mock())

        modal.usd_input = Mock(value="invalid")
        modal.pts_input = Mock(value="")

        interaction = AsyncMock()
        await modal.on_submit(interaction)

        mock_cog.config.guild(guild).monthly_limit.set.assert_not_called()
        interaction.response.send_message.assert_called()

    async def test_back_button_callback(self, mock_cog, mock_ctx):
        btn = BackButton(mock_cog, mock_ctx, "en")

        # Patch target class where it is defined, so imports find the mock
        with patch("poehub.ui.provider_view.ProviderConfigView") as mock_cls:
            mock_view = AsyncMock()
            mock_cls.return_value = mock_view

            interaction = AsyncMock()
            await btn.callback(interaction)

            mock_view.refresh_content.assert_called_with(interaction)

