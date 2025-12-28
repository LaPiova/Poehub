"""Context Service for managing user sessions and localization."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..core.i18n import LANG_EN, SUPPORTED_LANGS, tr

if TYPE_CHECKING:
    from redbot.core import Config


class ContextService:
    """Manages user context, preferences, and localization."""

    def __init__(self, config: Config):
        self.config = config

    async def get_user_language(self, user_id: int) -> str:
        """Return the user's language code."""
        # Note: redbot config.user_from_id(id) allows accessing user config without a Member object
        lang = await self.config.user_from_id(user_id).language()
        if lang in SUPPORTED_LANGS:
            return lang
        return LANG_EN

    async def translate(self, user_id: int, key: str, **kwargs: Any) -> str:
        """Translate a string key for a specific user."""
        lang = await self.get_user_language(user_id)
        return tr(lang, key, **kwargs)

    async def get_user_system_prompt(self, user_id: int) -> str | None:
        """Get the user's specific system prompt, if set."""
        # Logic extracted from PoeHub._get_system_prompt
        # 1. Check for personal prompt override
        personal_prompt = await self.config.user_from_id(user_id).system_prompt()
        if personal_prompt:
            return personal_prompt

        # 2. Fall back to global default
        return await self.config.default_system_prompt()

    async def get_active_conversation_id(self, user_id: int) -> str:
        """Get the user's currently active conversation ID."""
        return await self.config.user_from_id(user_id).active_conversation()

    async def set_active_conversation_id(self, user_id: int, conv_id: str) -> None:
        """Set the user's active conversation ID."""
        await self.config.user_from_id(user_id).active_conversation.set(conv_id)
