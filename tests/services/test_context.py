from unittest.mock import AsyncMock, Mock, patch

import pytest

from poehub.services.context import ContextService


@pytest.mark.asyncio
class TestContextService:
    @pytest.fixture
    def mock_config(self):
        config = Mock()
        return config

    @pytest.fixture
    def service(self, mock_config):
        return ContextService(mock_config)

    async def test_get_user_language_valid(self, service, mock_config):
        # Setup
        mock_user_group = Mock()
        mock_config.user_from_id.return_value = mock_user_group
        mock_user_group.language = AsyncMock(return_value="zh-TW")

        # Execute
        lang = await service.get_user_language(123)

        # Verify
        assert lang == "zh-TW"
        mock_config.user_from_id.assert_called_with(123)

    async def test_get_user_language_invalid_fallback(self, service, mock_config):
        # Setup
        mock_user_group = Mock()
        mock_config.user_from_id.return_value = mock_user_group
        mock_user_group.language = AsyncMock(return_value="invalid-lang")

        # Execute
        lang = await service.get_user_language(123)

        # Verify
        assert lang == "en"

    async def test_translate(self, service, mock_config):
        # Setup
        mock_user_group = Mock()
        mock_config.user_from_id.return_value = mock_user_group
        mock_user_group.language = AsyncMock(return_value="en")

        with patch("poehub.services.context.tr") as mock_tr:
            mock_tr.return_value = "Translated"

            # Execute
            result = await service.translate(123, "SOME_KEY", arg="val")

            # Verify
            assert result == "Translated"
            mock_tr.assert_called_with("en", "SOME_KEY", arg="val")

    async def test_get_user_system_prompt_personal(self, service, mock_config):
        mock_user_group = Mock()
        mock_config.user_from_id.return_value = mock_user_group
        mock_user_group.system_prompt = AsyncMock(return_value="Personal Prompt")

        prompt = await service.get_user_system_prompt(123)
        assert prompt == "Personal Prompt"

    async def test_get_user_system_prompt_default(self, service, mock_config):
        mock_user_group = Mock()
        mock_config.user_from_id.return_value = mock_user_group
        mock_user_group.system_prompt = AsyncMock(return_value=None)

        mock_config.default_system_prompt = AsyncMock(return_value="Global Default")

        prompt = await service.get_user_system_prompt(123)
        assert prompt == "Global Default"

    async def test_active_conversation(self, service, mock_config):
        mock_user_group = Mock()
        mock_config.user_from_id.return_value = mock_user_group

        # Test Get
        mock_user_group.active_conversation = AsyncMock(return_value="conv-123")
        conv_id = await service.get_active_conversation_id(123)
        assert conv_id == "conv-123"

        # Test Set
        # Mock the attribute so we can check .set call
        mock_val = AsyncMock()
        mock_user_group.active_conversation = mock_val

        await service.set_active_conversation_id(123, "new-conv")
        mock_val.set.assert_called_with("new-conv")
