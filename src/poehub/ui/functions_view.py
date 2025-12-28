"""Functions Menu UI for PoeHub."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import discord
from redbot.core import commands as red_commands

from ..core.i18n import tr
from ..core.protocols import IPoeHub
from .common import BackButton, CloseMenuButton
from .summary_view import SummaryView


class SummaryButton(discord.ui.Button):
    """Button to open the Message Summary view."""

    def __init__(self, cog: IPoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "FUNC_BTN_SUMMARY"),
            style=discord.ButtonStyle.primary,
            emoji="📊",
            row=0,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        view: FunctionsMenuView = self.view  # type: ignore

        async def go_back_to_functions(inter: discord.Interaction) -> None:
            """Return to the Functions menu."""
            func_view = FunctionsMenuView(
                self.cog,
                self.ctx,
                self.lang,
                back_callback=view.back_callback,
            )
            embed = discord.Embed(
                title=tr(self.lang, "FUNC_TITLE"),
                description=tr(self.lang, "FUNC_DESC"),
                color=discord.Color.teal(),
            )
            await inter.response.edit_message(embed=embed, view=func_view)
            func_view.message = inter.message

        # Open the Summary view
        summary_view = SummaryView(
            self.cog,
            self.ctx,
            self.lang,
            back_callback=go_back_to_functions,
        )
        embed = summary_view.build_embed()

        await interaction.response.edit_message(embed=embed, view=summary_view)
        summary_view.message = interaction.message


class FunctionsMenuView(discord.ui.View):
    """Functions Menu View - container for additional features."""

    def __init__(
        self,
        cog: IPoeHub,
        ctx: red_commands.Context,
        lang: str,
        back_callback: Callable[[discord.Interaction], Awaitable[None]] | None = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.back_callback = back_callback

        self.add_item(SummaryButton(cog, ctx, lang))
        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))

        if back_callback:
            self.add_item(BackButton(back_callback, lang))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                tr(self.lang, "RESTRICTED_MENU"),
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if hasattr(self, "message") and self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
