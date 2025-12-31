"""Message Summary UI for PoeHub."""

from __future__ import annotations

import logging

import discord
from pydantic import BaseModel
from redbot.core import commands as red_commands

from ..core.i18n import tr
from ..core.protocols import IPoeHub
from .common import BackButton, CloseMenuButton

log = logging.getLogger("red.poehub.summary")

# --- Pydantic Models for Validation ---





class SummaryChunk(BaseModel):
    chunk_id: int
    text: str


# --- Views ---


class TimeRangeSelect(discord.ui.Select):
    """Dropdown to select time range for message summary."""

    def __init__(self, lang: str) -> None:
        options = [
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_1H"), value="1", emoji="🕐"
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_6H"), value="6", emoji="🕕"
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_24H"), value="24", emoji="📅"
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_CUSTOM"), value="custom", emoji="⚙️"
            ),
        ]
        super().__init__(
            placeholder=tr(lang, "SUMMARY_TIME_RANGE_LABEL"),
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]
        view: SummaryView = self.view  # type: ignore

        if selected == "custom":
            modal = CustomTimeModal(view.cog, view.ctx, self.lang, view)
            await interaction.response.send_modal(modal)
        else:
            view.selected_hours = float(selected)
            await view.update_embed(interaction)


class CustomTimeModal(discord.ui.Modal):
    def __init__(
        self,
        cog: IPoeHub,
        ctx: red_commands.Context,
        lang: str,
        parent_view: SummaryView,
    ) -> None:
        super().__init__(title=tr(lang, "SUMMARY_CUSTOM_MODAL_TITLE"))
        self.parent_view = parent_view
        self.lang = lang
        self.hours = discord.ui.TextInput(
            label=tr(lang, "SUMMARY_CUSTOM_HOURS_LABEL"),
            placeholder="1-7200",
            required=True,
            max_length=5,
        )
        self.add_item(self.hours)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            val = float(self.hours.value)
            if val <= 0 or val > 7200:
                raise ValueError
            self.parent_view.selected_hours = val
            await self.parent_view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message(
                tr(self.lang, "SUMMARY_INVALID_HOURS"), ephemeral=True
            )


class StartSummaryButton(discord.ui.Button):
    def __init__(self, cog: IPoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "SUMMARY_BTN_START"),
            style=discord.ButtonStyle.success,
            emoji="📊",
            row=1,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        view: SummaryView = self.view
        # Defer interaction to prevent timeout while we start the process
        await interaction.response.defer(ephemeral=False, thinking=False)

        await self.view.cog.run_summary_pipeline(
            self.view.ctx,
            self.view.ctx.channel,
            view.selected_hours,
            interaction=interaction
        )


class SummaryView(discord.ui.View):
    def __init__(self, cog: IPoeHub, ctx: red_commands.Context, lang: str, back_callback: callable | None = None) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.selected_hours = 1.0
        self.back_callback = back_callback

        self.add_item(TimeRangeSelect(lang))
        self.add_item(StartSummaryButton(cog, ctx, lang))
        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))
        if back_callback:
            self.add_item(BackButton(back_callback, lang))

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=tr(self.lang, "SUMMARY_TITLE"),
            description=tr(self.lang, "SUMMARY_DESC"),
            color=discord.Color.orange(),
        )
        embed.add_field(name="Selected Time", value=f"**{self.selected_hours} Hours**")
        return embed

    async def update_embed(self, interaction: discord.Interaction):
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)
