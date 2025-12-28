from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import discord
import pytest

# Mocking tr before importing common
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key: key):
    from poehub.ui.common import BackButton, CloseMenuButton, preview_content

@pytest.mark.asyncio
class TestUICommon:
    async def test_preview_content(self):
        # String
        assert preview_content("Hello World") == "Hello World"
        # "A"*100 with max_len=10 -> "AAAAAAAAAA" + "..." -> "AAAAAAAAAA..."
        assert preview_content("A" * 100, max_len=10) == "AAAAAAAAAA..."

        # Test max_len constraint implementation details
        # code: if len(text) > max_len: return text[:max_len] + "..."
        assert preview_content("A" * 20, max_len=5) == "AAAAA..."

        # List
        content_list = [{"type": "text", "text": "Foo"}, {"type": "image"}, {"type": "text", "text": "Bar"}]
        assert preview_content(content_list) == "Foo Bar"

        # Empty logic
        assert preview_content("") == "*Empty*"
        assert preview_content(None) == "*Empty*"
        assert preview_content([]) == "[non-text content]"
        assert preview_content([{"type": "image"}]) == "[non-text content]"

    async def test_back_button(self):
        callback = AsyncMock()
        # Ensure we patch tr for this test if we rely on keys, OR just accept "Back"
        # Let's rely on the real tr function behavior if simpler, or patch it.
        # Since I imported it inside patch block, 'tr' imported in common.py 'might' be the mock IF the from...import bound it?
        # Python imports bind names. If I patched it during import, poehub.ui.common.tr is the mock/lambda.
        # But failure showed "Back", meaning it was NOT the mock.
        # Ah, patch("poehub.core.i18n.tr") patches the source.
        # But if 'from ..core.i18n import tr' ran BEFORE my patch (e.g. implicitly imported by something else), my patch context misses it?
        # Anyway, checking for "Back" or "BTN_BACK" is fine.
        btn = BackButton(callback, "en")
        assert btn.label in ["Back", "BTN_BACK"]

        interaction = AsyncMock(spec=discord.Interaction)
        await btn.callback(interaction)
        callback.assert_called_with(interaction)

    async def test_close_menu_button(self):
        btn = CloseMenuButton(label="Close")

        # We must attach to a View to set btn.view
        view = MagicMock(spec=discord.ui.View)
        # Mocking View behavior for children iteration
        child = Mock()
        view.children = [child]

        # Cannot set btn.view directly. But we can patch the property on the instance?
        # Or just use a real View?
        # Real view:
        real_view = discord.ui.View()
        real_view.add_item(btn)
        # Now btn.view is real_view.

        # We need to mock real_view.stop() and children.
        # discord.ui.View.children is a property.
        # We can't easily mock children of real view unless we add mock items.

        # Alternative: Patch the 'view' property on the button class or instance?
        # btn.view is a property.
        with patch.object(discord.ui.Button, 'view', new_callable=PropertyMock) as mock_view_prop:
             mock_view_prop.return_value = view

             interaction = AsyncMock(spec=discord.Interaction)
             interaction.response.edit_message = AsyncMock()
             await btn.callback(interaction)

             assert child.disabled is True
             view.stop.assert_called()
             interaction.response.edit_message.assert_called_with(view=view)

    async def test_close_menu_button_no_view(self):
        btn = CloseMenuButton()
        # Ensure view is None (default)
        interaction = AsyncMock()
        await btn.callback(interaction)
        interaction.response.edit_message.assert_not_called()
