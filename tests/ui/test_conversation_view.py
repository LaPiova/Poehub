from unittest.mock import AsyncMock, MagicMock, Mock, PropertyMock, patch

import pytest

# Mock tr
with patch("poehub.core.i18n.tr", side_effect=lambda lang, key, **kwargs: key):
    from poehub.ui.conversation_view import (
        ClearHistoryButton,
        ConversationMenuView,
        DeleteButton,
        NewConversationButton,
        RefreshButton,
        SwitchConversationSelect,
    )

@pytest.fixture
def mock_cog():
    cog = MagicMock()

    # Context Service
    cog.context_service = AsyncMock()
    cog.context_service.get_active_conversation_id.return_value = "c1"
    cog.context_service.set_active_conversation_id = AsyncMock()

    # Conversation Manager
    cog.conversation_manager = MagicMock()
    cog.conversation_manager.process_conversation_data = Mock(side_effect=lambda x: x)
    cog.conversation_manager.clear_messages = Mock(side_effect=lambda x: {**x, "messages": []})

    # Chat Service
    cog.chat_service = MagicMock()
    cog.chat_service._clear_conversation_memory = AsyncMock()

    # Helpers
    cog._get_conversation = AsyncMock(return_value={"messages": [{"role": "user", "content": "hi"}]})
    cog._get_or_create_conversation = AsyncMock(return_value={"messages": []})
    cog._delete_conversation = AsyncMock(return_value=True)
    cog._save_conversation = AsyncMock()
    cog._create_and_switch_conversation = AsyncMock()

    # Config
    user_group = MagicMock()
    # conversations() returns dict of id -> data
    user_group.conversations = AsyncMock(return_value={"c1": {"messages": []}, "c2": {"messages": []}})
    user_group.model = AsyncMock(return_value="gpt-4")
    cog.config.user.return_value = user_group

    cog._build_model_select_options = AsyncMock(return_value=[])

    return cog

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 12345
    return ctx

@pytest.mark.asyncio
class TestConversationView:
    async def test_view_init(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")
        # Items are added in refresh_content, not init?
        # Let's check init: only timeouts and attrs.
        assert len(view.children) == 0 # Correct, refresh_content populates it

    async def test_refresh_content(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")

        interaction = AsyncMock()
        # is_done is synchronous, so use Mock
        interaction.response.is_done = Mock(return_value=False)
        interaction.response.edit_message = AsyncMock()

        await view.refresh_content(interaction)

        assert len(view.children) > 0
        interaction.response.edit_message.assert_called()
        args = interaction.response.edit_message.call_args[1]
        assert 'embed' in args

    async def test_interaction_check(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")

        interaction = AsyncMock()
        interaction.user.id = 12345
        assert await view.interaction_check(interaction) is True

        interaction.user.id = 999
        interaction.response = AsyncMock()
        assert await view.interaction_check(interaction) is False

    async def test_switch_select(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")
        select = SwitchConversationSelect(mock_cog, mock_ctx, [], "en")

        view.refresh_content = AsyncMock()

        with patch.object(SwitchConversationSelect, 'values', new_callable=PropertyMock) as mv:
            mv.return_value = ["c2"]
            with patch.object(SwitchConversationSelect, 'view', new_callable=PropertyMock) as mp:
                mp.return_value = view

                interaction = AsyncMock()
                interaction.response.defer = AsyncMock()

                await select.callback(interaction)

                mock_cog.context_service.set_active_conversation_id.assert_called_with(12345, "c2")
                view.refresh_content.assert_called_with(interaction)

    async def test_delete_button(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")
        btn = DeleteButton(mock_cog, mock_ctx, "en")
        view.refresh_content = AsyncMock()

        with patch.object(DeleteButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = view

            interaction = AsyncMock()
            interaction.response.send_message = AsyncMock()

            await btn.callback(interaction)

            mock_cog._delete_conversation.assert_called()
            mock_cog.context_service.set_active_conversation_id.assert_called_with(12345, "default")
            view.refresh_content.assert_called_with(interaction, update_response=True)

    async def test_clear_history_button(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")
        btn = ClearHistoryButton(mock_cog, mock_ctx, "en")
        view.refresh_content = AsyncMock()

        with patch.object(ClearHistoryButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = view

            interaction = AsyncMock()
            await btn.callback(interaction)

            mock_cog.conversation_manager.clear_messages.assert_called()
            mock_cog._save_conversation.assert_called()
            mock_cog.chat_service._clear_conversation_memory.assert_awaited()
            view.refresh_content.assert_called()

    async def test_new_conversation_button(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")
        btn = NewConversationButton(mock_cog, mock_ctx, "en")
        view.refresh_content = AsyncMock()

        with patch.object(NewConversationButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = view

            interaction = AsyncMock()
            await btn.callback(interaction)

            mock_cog._create_and_switch_conversation.assert_called_with(12345)
            view.refresh_content.assert_called()

    async def test_refresh_button(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")
        btn = RefreshButton("en")
        view.refresh_content = AsyncMock()

        with patch.object(RefreshButton, 'view', new_callable=PropertyMock) as mp:
            mp.return_value = view

            interaction = AsyncMock()
            interaction.response.defer = AsyncMock()

            await btn.callback(interaction)

            view.refresh_content.assert_called_with(interaction)
            interaction.response.defer.assert_called()

    async def test_build_options_empty_manager(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")
        mock_cog.conversation_manager = None # Not initialized

        opts, aid = await view.build_options()
        assert aid == "default"
        assert len(opts) == 1
        assert opts[0].value == "default"

    async def test_build_options(self, mock_cog, mock_ctx):
        view = ConversationMenuView(mock_cog, mock_ctx, "en")

        opts, aid = await view.build_options()
        assert aid == "c1" # from fixture
        # Should have c1 and c2 + default fallback if empty?
        # Logic says: if conversations: sort and return.
        # If conversations empty, return default option.
        # mock_cog conversations returns c1, c2.
        assert len(opts) == 2
        # Check if one is marked active
        active = [o for o in opts if o.default]
        assert len(active) == 1
        assert active[0].value == "c1"

