"""Unified Home Menu UI for PoeHub."""

from __future__ import annotations

import discord
from redbot.core import commands as red_commands

from ..i18n import tr
from .common import CloseMenuButton
from .config_view import PoeConfigView
from .conversation_view import ConversationMenuView


class SettingsButton(discord.ui.Button):
    """Button to open the Settings menu."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "HOME_BTN_SETTINGS"),
            style=discord.ButtonStyle.secondary,
            emoji="⚙️",
            row=0,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        # Check permissions/ownership for config if needed?
        # Standard users can see settings (model/prompt), owner sees more.
        # Logic from menu command:
        is_owner = await self.cog.bot.is_owner(self.ctx.author)
        dummy_state = (
            await self.cog.config.use_dummy_api()
            if (is_owner and self.cog.allow_dummy_mode)
            else False
        )
        model_options = await self.cog._build_model_select_options()

        async def go_home(inter: discord.Interaction):
            view = HomeMenuView(self.cog, self.ctx, self.lang)
            embed = discord.Embed(
                title=tr(self.lang, "HOME_TITLE"),
                description=tr(self.lang, "HOME_DESC"),
                color=discord.Color.blue(),
            )
            await inter.response.edit_message(embed=embed, view=view)
            view.message = inter.message

        embed = await self.cog._build_config_embed(
            self.ctx, is_owner, dummy_state, self.lang
        )
        view = PoeConfigView(
            self.cog,
            self.ctx,
            model_options,
            is_owner,
            dummy_state,
            self.lang,
            back_callback=go_home,
        )
        
        # We want to replace the current message
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = interaction.message


class ConversationsButton(discord.ui.Button):
    """Button to open the Conversations menu."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "HOME_BTN_CONV"),
            style=discord.ButtonStyle.primary,
            emoji="💬",
            row=0,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.cog.conversation_manager:
            await interaction.response.send_message(
                tr(self.lang, "CONV_SYSTEM_NOT_INITIALIZED"), ephemeral=True
            )
            return

        async def go_home(inter: discord.Interaction):
            view = HomeMenuView(self.cog, self.ctx, self.lang)
            embed = discord.Embed(
                title=tr(self.lang, "HOME_TITLE"),
                description=tr(self.lang, "HOME_DESC"),
                color=discord.Color.blue(),
            )
            await inter.response.edit_message(embed=embed, view=view)
            view.message = inter.message

        view = ConversationMenuView(self.cog, self.ctx, self.lang, back_callback=go_home)
        embed = await view.refresh_content(None)
        
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = interaction.message


class HomeMenuView(discord.ui.View):
    """Unified Home Menu View."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, lang: str) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        
        self.add_item(ConversationsButton(cog, ctx, lang))
        self.add_item(SettingsButton(cog, ctx, lang))
        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                tr(self.lang, "RESTRICTED_MENU"),
                ephemeral=True,
            )
            return False
        return True
