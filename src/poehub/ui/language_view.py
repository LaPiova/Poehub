"""Interactive language selection UI for PoeHub."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from redbot.core import commands as red_commands

from ..i18n import LANG_LABELS, SUPPORTED_LANGS, tr
from .common import CloseMenuButton

if TYPE_CHECKING:  # pragma: no cover
    from ..poehub import PoeHub


class LanguageSelect(discord.ui.Select):
    """Dropdown to pick UI/help language."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        options: list[discord.SelectOption] = []
        for code in SUPPORTED_LANGS:
            label = LANG_LABELS.get(code, code)
            options.append(
                discord.SelectOption(
                    label=label,
                    value=code,
                    default=(code == lang),
                )
            )

        super().__init__(
            placeholder=tr(lang, "LANG_SELECT_PLACEHOLDER"),
            min_values=1,
            max_values=1,
            options=options,
        )
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        code = self.values[0]
        await self.cog.config.user(self.ctx.author).language.set(code)
        label = LANG_LABELS.get(code, code)
        await interaction.response.send_message(
            tr(code, "LANG_SET_OK", language=label),
            ephemeral=True,
        )


class LanguageView(discord.ui.View):
    """Language selection view."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.message: discord.Message | None = None

        self.add_item(LanguageSelect(cog, ctx, lang))
        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                tr(self.lang, "RESTRICTED_MENU"), ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if not self.message:
            return
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass
