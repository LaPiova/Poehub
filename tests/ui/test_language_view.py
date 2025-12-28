from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

# Mock constants from i18n
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key, **kwargs: key), \
     patch("poehub.core.i18n.SUPPORTED_LANGS", ["en", "zh"]), \
     patch("poehub.core.i18n.LANG_LABELS", {"en": "English", "zh": "Chinese"}):
    from poehub.ui.language_view import LanguageSelect, LanguageView

@pytest.fixture
def mock_cog():
    cog = MagicMock()
    cog.config.user = MagicMock()
    cog.config.user.return_value.language.set = AsyncMock()
    return cog

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 12345
    return ctx

@pytest.mark.asyncio
class TestLanguageView:
    async def test_view_init(self, mock_cog, mock_ctx):
        view = LanguageView(mock_cog, mock_ctx, "en")
        assert len(view.children) > 0

    async def test_interaction_check(self, mock_cog, mock_ctx):
        view = LanguageView(mock_cog, mock_ctx, "en")

        interaction = AsyncMock()
        interaction.user.id = 12345
        assert await view.interaction_check(interaction) is True

        interaction.user.id = 999
        interaction.response = AsyncMock()
        assert await view.interaction_check(interaction) is False

    async def test_language_select(self, mock_cog, mock_ctx):
        select = LanguageSelect(mock_cog, mock_ctx, "en")

        with patch.object(LanguageSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["zh"]

            interaction = AsyncMock()
            await select.callback(interaction)

            mock_cog.config.user(mock_ctx.author).language.set.assert_called_with("zh")
            interaction.response.send_message.assert_called()

    async def test_on_timeout(self, mock_cog, mock_ctx):
        view = LanguageView(mock_cog, mock_ctx, "en")
        view.message = AsyncMock()

        await view.on_timeout()

        view.message.edit.assert_called_with(view=view)
        assert view.children[0].disabled is True
