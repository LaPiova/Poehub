"""Interactive configuration UI for PoeHub."""

from __future__ import annotations

from typing import Awaitable, Callable, List, Optional, TYPE_CHECKING

import discord
from redbot.core import commands as red_commands

from ..i18n import tr
from ..prompt_utils import (
    PROMPT_PREFILL_LIMIT,
    PROMPT_TEXTINPUT_MAX,
    send_prompt_files_dm,
)
from .common import BackButton, CloseMenuButton

if TYPE_CHECKING:  # pragma: no cover
    from ..poehub import PoeHub


class PoeConfigView(discord.ui.View):
    """Interactive configuration dashboard."""

    def __init__(
        self,
        cog: "PoeHub",
        ctx: red_commands.Context,
        model_options: List[discord.SelectOption],
        owner_mode: bool,
        dummy_state: bool,
        lang: str,
        back_callback: Optional[Callable[[discord.Interaction], Awaitable[None]]] = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.message: Optional[discord.Message] = None
        self.owner_mode = owner_mode
        self.back_callback = back_callback
        lang = self.lang

        if model_options:
            self.add_item(ModelSelect(cog, ctx, model_options, lang))

        self.add_item(SetPromptButton(cog, ctx, lang))
        self.add_item(ShowPromptButton(cog, ctx, lang))
        self.add_item(ClearPromptButton(cog, ctx, lang))

        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))
        
        if back_callback:
            self.add_item(BackButton(back_callback, lang))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                tr(getattr(self, "lang", "en"), "RESTRICTED_MENU"),
                ephemeral=True,
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


class ModelSelect(discord.ui.Select):
    """Dropdown for picking the default model."""

    def __init__(
        self,
        cog: "PoeHub",
        ctx: red_commands.Context,
        options: List[discord.SelectOption],
        lang: str,
    ) -> None:
        super().__init__(
            placeholder=tr(lang, "CONFIG_SELECT_MODEL_PLACEHOLDER"),
            min_values=1,
            max_values=1,
            options=options,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        model_choice = self.values[0]
        await self.cog.config.user(self.ctx.author).model.set(model_choice)
        await interaction.response.send_message(
            tr(self.lang, "CONFIG_MODEL_SET_OK", model=model_choice),
            ephemeral=True,
        )


class PromptModal(discord.ui.Modal):
    """Modal to update the user's personal system prompt."""

    def __init__(
        self,
        cog: "PoeHub",
        ctx: red_commands.Context,
        lang: str,
        user_prompt: Optional[str],
        fallback_prompt: Optional[str],
    ) -> None:
        super().__init__(title=tr(lang, "CONFIG_PROMPT_MODAL_TITLE"))
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self._stored_prompt = user_prompt or ""
        self._append_mode = False

        prefill_text: Optional[str] = None
        placeholder = tr(lang, "CONFIG_PROMPT_MODAL_PLACEHOLDER")

        if user_prompt:
            if len(user_prompt) <= PROMPT_PREFILL_LIMIT:
                prefill_text = user_prompt
            else:
                self._append_mode = True
                placeholder = tr(
                    lang,
                    "CONFIG_PROMPT_APPEND_PLACEHOLDER",
                    limit=PROMPT_PREFILL_LIMIT,
                )
        elif fallback_prompt and len(fallback_prompt) <= PROMPT_TEXTINPUT_MAX:
            prefill_text = fallback_prompt
        elif fallback_prompt:
            placeholder = tr(lang, "CONFIG_PROMPT_DEFAULT_TOO_LONG")

        self.prompt: discord.ui.TextInput = discord.ui.TextInput(
            label=tr(lang, "CONFIG_PROMPT_MODAL_LABEL"),
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=PROMPT_TEXTINPUT_MAX,
            placeholder=placeholder,
            default=prefill_text,
        )
        self.add_item(self.prompt)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        raw_value = self.prompt.value
        if not raw_value or not raw_value.strip():
            await interaction.response.send_message(
                tr(self.lang, "CONFIG_PROMPT_MODAL_EMPTY"),
                ephemeral=True,
            )
            return

        new_text = raw_value
        if self._append_mode and self._stored_prompt:
            updated_prompt = self._stored_prompt + new_text
            status_text = tr(self.lang, "CONFIG_PROMPT_APPENDED")
        else:
            updated_prompt = new_text
            status_text = tr(self.lang, "CONFIG_PROMPT_UPDATED")

        await self.cog.config.user(self.ctx.author).system_prompt.set(updated_prompt)
        await interaction.response.send_message(status_text, ephemeral=True)


class SetPromptButton(discord.ui.Button):
    """Button to open the personal prompt modal."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "CONFIG_BTN_SET_PROMPT"),
            style=discord.ButtonStyle.primary,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        user_prompt = await self.cog.config.user(self.ctx.author).system_prompt()
        default_prompt = await self.cog.config.default_system_prompt()
        await interaction.response.send_modal(
            PromptModal(self.cog, self.ctx, self.lang, user_prompt, default_prompt)
        )


class ShowPromptButton(discord.ui.Button):
    """Button to display the current prompt(s) in an embed."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "CONFIG_BTN_VIEW_PROMPT"),
            style=discord.ButtonStyle.secondary,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        user_prompt = await self.cog.config.user(self.ctx.author).system_prompt()
        default_prompt = await self.cog.config.default_system_prompt()

        if not user_prompt and not default_prompt:
            await interaction.response.send_message(
                tr(self.lang, "CONFIG_NO_PROMPT"),
                ephemeral=True,
            )
            return

        payloads = []
        if user_prompt and len(user_prompt) > 1000:
            payloads.append((f"personal_prompt_{self.ctx.author.id}.txt", user_prompt))
        if default_prompt and len(default_prompt) > 1000:
            payloads.append(("default_prompt.txt", default_prompt))

        if payloads:
            dm_message = tr(self.lang, "MY_PROMPT_DM_BODY")
            dm_sent = await send_prompt_files_dm(interaction.user, payloads, dm_message)
            message = (
                tr(self.lang, "CONFIG_PROMPT_DM_SENT")
                if dm_sent
                else tr(self.lang, "CONFIG_PROMPT_DM_BLOCKED")
            )
            await interaction.response.send_message(message, ephemeral=True)
            return

        embed = discord.Embed(
            title=tr(self.lang, "CONFIG_PROMPT_EMBED_TITLE"),
            color=discord.Color.blurple(),
        )
        if user_prompt:
            embed.add_field(
                name=tr(self.lang, "CONFIG_PROMPT_FIELD_PERSONAL"),
                value=f"```{user_prompt}```",
                inline=False,
            )
        if default_prompt:
            embed.add_field(
                name=tr(self.lang, "CONFIG_PROMPT_FIELD_DEFAULT"),
                value=f"```{default_prompt}```",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class ClearPromptButton(discord.ui.Button):
    """Button to clear the user's personal prompt."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "CONFIG_BTN_CLEAR_PROMPT"),
            style=discord.ButtonStyle.secondary,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.cog.config.user(self.ctx.author).system_prompt.set(None)
        await interaction.response.send_message(
            tr(self.lang, "CONFIG_PROMPT_CLEARED"),
            ephemeral=True,
        )


class DummyToggleButton(discord.ui.Button):
    """Owner-only toggle for offline dummy mode (if enabled by env flag)."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, enabled: bool, lang: str) -> None:
        label = tr(lang, "CONFIG_BTN_DUMMY_ON") if enabled else tr(lang, "CONFIG_BTN_DUMMY_OFF")
        style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary
        super().__init__(label=label, style=style)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        new_state = not await self.cog.config.use_dummy_api()
        await self.cog.config.use_dummy_api.set(new_state)
        await self.cog._init_client()

        self.label = (
            tr(self.lang, "CONFIG_BTN_DUMMY_ON")
            if new_state
            else tr(self.lang, "CONFIG_BTN_DUMMY_OFF")
        )
        self.style = (
            discord.ButtonStyle.success if new_state else discord.ButtonStyle.secondary
        )

        if not self.view:
            await interaction.response.send_message("✅ Dummy API mode 狀態已更新。", ephemeral=True)
            return

        new_options = await self.cog._build_model_select_options()
        for child in self.view.children:
            if isinstance(child, ModelSelect):
                child.options = new_options
                break

            owner_mode = getattr(self.view, "owner_mode", True)
            embed = await self.cog._build_config_embed(self.ctx, owner_mode, new_state, self.lang)
        await interaction.response.edit_message(embed=embed, view=self.view)
        await interaction.followup.send(
            tr(self.lang, "CONFIG_DUMMY_ENABLED_OK")
            if new_state
            else tr(self.lang, "CONFIG_DUMMY_DISABLED_OK"),
            ephemeral=True,
        )
