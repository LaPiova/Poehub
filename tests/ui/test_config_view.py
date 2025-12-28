from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import discord
import pytest

# Mock tr
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key, **kwargs: key):
    from poehub.ui.config_view import (
        ClearPromptButton,
        ConfigLanguageSelect,
        DummyToggleButton,
        LanguageSelectButton,
        ModelSearchModal,
        ModelSelect,
        PoeConfigView,
        PromptModal,
        SearchModelsButton,
        SetPromptButton,
        ShowPromptButton,
    )

@pytest.fixture
def mock_cog():
    cog = MagicMock()
    # Mock config
    user_group = MagicMock()
    def create_config_item(return_val=None):
        item = AsyncMock(return_value=return_val)
        item.set = AsyncMock()
        return item

    user_group.model = create_config_item("gpt-4")
    user_group.system_prompt = create_config_item("Sys Prompt")
    user_group.language = create_config_item("en")

    cog.config.user.return_value = user_group
    cog.config.default_system_prompt = AsyncMock(return_value="Default Prompt")
    cog.config.use_dummy_api = create_config_item(False) # callable + set

    cog._build_model_select_options = AsyncMock(return_value=[discord.SelectOption(label="Opt1", value="1")])
    cog._init_client = AsyncMock()
    cog._build_config_embed = AsyncMock(return_value=discord.Embed(title="Conf"))

    return cog

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 12345
    return ctx

@pytest.mark.asyncio
class TestConfigView:
    async def test_view_init(self, mock_cog, mock_ctx):
        options = [discord.SelectOption(label="M1", value="m1")]
        view = PoeConfigView(mock_cog, mock_ctx, options, True, False, "en")
        assert len(view.children) > 0
        assert isinstance(view.children[0], ModelSelect)

    async def test_interaction_check(self, mock_cog, mock_ctx):
        view = PoeConfigView(mock_cog, mock_ctx, [], True, False, "en")

        interaction = AsyncMock()
        interaction.user.id = 12345
        assert await view.interaction_check(interaction) is True

        interaction.user.id = 999
        interaction.response = AsyncMock()
        assert await view.interaction_check(interaction) is False

    # --- Search Flow ---

    async def test_model_search_button(self, mock_cog, mock_ctx):
        btn = SearchModelsButton(mock_cog, mock_ctx, "en")
        interaction = AsyncMock()
        await btn.callback(interaction)
        interaction.response.send_modal.assert_called()
        args = interaction.response.send_modal.call_args[0]
        assert isinstance(args[0], ModelSearchModal)

    async def test_model_search_modal_submit(self, mock_cog, mock_ctx):
        modal = ModelSearchModal(mock_cog, mock_ctx, "en")
        modal.query = Mock(value="query")

        # Mock origin view
        view = MagicMock()
        select = Mock(spec=ModelSelect) # spec checks isinstance? Mock(spec=Class) isinstance works? Yes.
        # Actually standard Mock isinstance might fail unless using spec correctly or side_effect.
        # Let's use a real Select if possible or just rely on Mock spec.
        select = ModelSelect(mock_cog, mock_ctx, [], "en")
        view.children = [select]
        modal.origin_view = view

        interaction = AsyncMock()
        interaction.response.edit_message = AsyncMock()

        await modal.on_submit(interaction)

        mock_cog._build_model_select_options.assert_called_with("query")
        interaction.response.edit_message.assert_called_with(view=view)
        assert len(select.options) == 1 # from mock_cog default

    async def test_model_search_modal_no_results(self, mock_cog, mock_ctx):
        modal = ModelSearchModal(mock_cog, mock_ctx, "en")
        modal.query = Mock(value="query")
        mock_cog._build_model_select_options.return_value = []

        interaction = AsyncMock()
        await modal.on_submit(interaction)

        interaction.response.send_message.assert_called() # No results msg

    # --- Model Select ---

    async def test_model_select_callback(self, mock_cog, mock_ctx):
        select = ModelSelect(mock_cog, mock_ctx, [], "en")

        with patch.object(ModelSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["gpt-5"]

            interaction = AsyncMock()
            await select.callback(interaction)

            mock_cog.config.user(mock_ctx.author).model.set.assert_called_with("gpt-5")
            interaction.response.send_message.assert_called()

    # --- Prompt Flow ---

    async def test_set_prompt_button(self, mock_cog, mock_ctx):
        btn = SetPromptButton(mock_cog, mock_ctx, "en")
        interaction = AsyncMock()
        await btn.callback(interaction)
        interaction.response.send_modal.assert_called()
        args = interaction.response.send_modal.call_args[0]
        assert isinstance(args[0], PromptModal)

    async def test_prompt_modal_submit(self, mock_cog, mock_ctx):
        modal = PromptModal(mock_cog, mock_ctx, "en", "current", "default")

        modal.prompt = Mock(value="New Prompt")

        interaction = AsyncMock()
        await modal.on_submit(interaction)

        mock_cog.config.user(mock_ctx.author).system_prompt.set.assert_called_with("New Prompt")
        interaction.response.send_message.assert_called()

    async def test_prompt_modal_append(self, mock_cog, mock_ctx):
        # Trigger append mode: user_prompt > limit (stub limit)
        # Import constant to mock? Or pass very long string.
        # Assuming PROMPT_PREFILL_LIMIT is ~1000.
        # Assuming PROMPT_PREFILL_LIMIT is ~1000.
        with patch("poehub.ui.config_view.PROMPT_PREFILL_LIMIT", 100):
             modal = PromptModal(mock_cog, mock_ctx, "en", "A"*150, "default")
             assert modal._append_mode is True

             modal.prompt = Mock(value=" appended")
             interaction = AsyncMock()
             await modal.on_submit(interaction)

             mock_cog.config.user(mock_ctx.author).system_prompt.set.assert_called_with("A"*150 + " appended")

    async def test_clear_prompt(self, mock_cog, mock_ctx):
        btn = ClearPromptButton(mock_cog, mock_ctx, "en")
        interaction = AsyncMock()
        await btn.callback(interaction)

        mock_cog.config.user(mock_ctx.author).system_prompt.set.assert_called_with(None)

    async def test_show_prompt_embed(self, mock_cog, mock_ctx):
        btn = ShowPromptButton(mock_cog, mock_ctx, "en")

        # Short prompts -> Embed
        mock_cog.config.user(mock_ctx.author).system_prompt.return_value = "Short User"

        interaction = AsyncMock()
        await btn.callback(interaction)

        args = interaction.response.send_message.call_args[1]
        assert 'embed' in args

    async def test_show_prompt_dm(self, mock_cog, mock_ctx):
        btn = ShowPromptButton(mock_cog, mock_ctx, "en")

        # Long prompt -> DM
        long_p = "A" * 2000
        mock_cog.config.user(mock_ctx.author).system_prompt.return_value = long_p

        with patch("poehub.ui.config_view.send_prompt_files_dm", new=AsyncMock(return_value=True)) as mock_send:
            interaction = AsyncMock()
            await btn.callback(interaction)

            mock_send.assert_called()
            interaction.response.send_message.assert_called() # Sent confirmation

    # --- Language ---

    async def test_language_button_opens_view(self, mock_cog, mock_ctx):
        btn = LanguageSelectButton(mock_cog, mock_ctx, "en")
        interaction = AsyncMock()

        await btn.callback(interaction)

        interaction.response.send_message.assert_called()
        args = interaction.response.send_message.call_args[1]
        assert 'view' in args

    async def test_language_select_callback(self, mock_cog, mock_ctx):
        parent_view = MagicMock()
        child = LanguageSelectButton(mock_cog, mock_ctx, "en")
        parent_view.children = [child]

        select = ConfigLanguageSelect(mock_cog, mock_ctx, "en", parent_view)

        with patch.object(ConfigLanguageSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["zh"] # Change to Chinese

            interaction = AsyncMock()
            await select.callback(interaction)

            mock_cog.config.user(mock_ctx.author).language.set.assert_called_with("zh")
            assert child.lang == "zh" # Updated parent button

    # --- Dummy Toggle ---

    async def test_dummy_toggle(self, mock_cog, mock_ctx):
        btn = DummyToggleButton(mock_cog, mock_ctx, False, "en")

        # Setup view
        view = MagicMock()
        view.children = []
        # btn.view = view # Removed as read-only property
        # If we use patch.object logic for .view:

        with patch.object(DummyToggleButton, 'view', new_callable=PropertyMock) as mock_view_prop:
            mock_view_prop.return_value = view

            interaction = AsyncMock()
            interaction.response.edit_message = AsyncMock()
            interaction.followup.send = AsyncMock()

            await btn.callback(interaction)

            mock_cog.config.use_dummy_api.set.assert_called_with(True) # Toggled
            mock_cog._init_client.assert_called()
            mock_cog._build_config_embed.assert_called()
            interaction.response.edit_message.assert_called()
