from unittest.mock import AsyncMock, MagicMock, Mock, patch

import discord
import pytest

from poehub.i18n import LANG_EN
from poehub.ui.config_view import ModelSearchModal, ModelSelect


@pytest.mark.asyncio
async def test_get_matching_models():
    """Test the model filtering logic."""
    import importlib
    import sys

    # Define a dummy Cog class to solve the inheritance issue
    class DummyCog:
        def __init__(self, bot):
            self.bot = bot

        @staticmethod
        def listener(name=None):
            def decorator(func):
                return func

            return decorator

    # Modify the mock in sys.modules to return our DummyCog
    with patch.multiple(sys.modules["redbot.core"].commands, Cog=DummyCog):
        # Reload poehub to pick up the new base class
        import poehub.poehub

        importlib.reload(poehub.poehub)
        from poehub.poehub import PoeHub

        # Now PoeHub should be a real class inheriting from DummyCog
        cog = PoeHub(Mock())

        # We need to manually initialize what __init__ might verify or setup if we didn't run real init
        # But we called PoeHub(Mock()), so __init__ ran.
        # PoeHub.__init__ calls self._initialize() which might fail if dependencies are mocked/missing
        # But let's assume global mocks in conftest handle imports.

        cog.client = MagicMock()

        async def mock_get_models(force_refresh=False):
            return [
                {"id": "Claude-3-Opus"},
                {"id": "Claude-Instant"},
                {"id": "GPT-4"},
                {"id": "Gemini-Pro"},
            ]

        cog.client.get_models = Mock(side_effect=mock_get_models)

        # Test query
        results = await cog._get_matching_models("claude")
        assert len(results) == 2
        assert "Claude-3-Opus" in results
        assert "Claude-Instant" in results
        assert "GPT-4" not in results

        # Test no query
        results_all = await cog._get_matching_models(None)
        assert len(results_all) == 4

        # Test no match
        results_none = await cog._get_matching_models("xyz")
        assert len(results_none) == 0


@pytest.mark.asyncio
async def test_modal_submit_success():
    """Test modal submit updates the view."""
    mock_cog = AsyncMock()
    # Mock return of build options
    mock_cog._build_model_select_options.return_value = [
        discord.SelectOption(label="Claude-3", value="Claude-3")
    ]

    mock_ctx = Mock()
    modal = ModelSearchModal(mock_cog, mock_ctx, LANG_EN)

    # Mock TextInput to allow setting value
    modal.query = Mock()
    modal.query.value = "claude"

    # Mock origin view
    mock_view = Mock()
    mock_select = Mock(spec=ModelSelect)
    mock_view.children = [mock_select]
    modal.origin_view = mock_view

    mock_interaction = AsyncMock()

    await modal.on_submit(mock_interaction)

    # Verify cog called
    mock_cog._build_model_select_options.assert_called_with("claude")

    # Verify child updated
    assert len(mock_select.options) == 1
    assert mock_select.options[0].value == "Claude-3"

    # Verify edit message called
    mock_interaction.response.edit_message.assert_called_once()
    assert mock_interaction.response.edit_message.call_args.kwargs["view"] == mock_view


@pytest.mark.asyncio
async def test_modal_submit_no_results():
    """Test modal submit handles no results."""
    mock_cog = AsyncMock()
    mock_cog._build_model_select_options.return_value = []

    mock_ctx = Mock()
    modal = ModelSearchModal(mock_cog, mock_ctx, LANG_EN)

    # Mock TextInput
    modal.query = Mock()
    modal.query.value = "nonsense"

    mock_interaction = AsyncMock()

    await modal.on_submit(mock_interaction)

    # Verify error message
    mock_interaction.response.send_message.assert_called_once()
    assert "found" in str(mock_interaction.response.send_message.call_args)
