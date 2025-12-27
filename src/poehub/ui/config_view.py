"""Interactive configuration UI for PoeHub."""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

import discord
from redbot.core import commands as red_commands

from .common import CloseMenuButton

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
    ) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.message: Optional[discord.Message] = None
        self.owner_mode = owner_mode

        if model_options:
            self.add_item(ModelSelect(cog, ctx, model_options))

        self.add_item(SetPromptButton(cog, ctx))
        self.add_item(ShowPromptButton(cog, ctx))
        self.add_item(ClearPromptButton(cog, ctx))

        if owner_mode and cog.allow_dummy_mode:
            self.add_item(DummyToggleButton(cog, ctx, dummy_state))

        self.add_item(CloseMenuButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("此設定面板僅限觸發者使用。", ephemeral=True)
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
        self, cog: "PoeHub", ctx: red_commands.Context, options: List[discord.SelectOption]
    ) -> None:
        super().__init__(
            placeholder="Select your default model",
            min_values=1,
            max_values=1,
            options=options,
        )
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        model_choice = self.values[0]
        await self.cog.config.user(self.ctx.author).model.set(model_choice)
        await interaction.response.send_message(
            f"✅ 模型已設定為 `{model_choice}`", ephemeral=True
        )


class PromptModal(discord.ui.Modal, title="設定個人提示詞 / Set Personal Prompt"):
    """Modal to update the user's personal system prompt."""

    prompt: discord.ui.TextInput = discord.ui.TextInput(
        label="System Prompt",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500,
        placeholder="Describe how PoeHub should respond...",
    )

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context) -> None:
        super().__init__()
        self.cog = cog
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction) -> None:
        prompt_text = self.prompt.value.strip()
        await self.cog.config.user(self.ctx.author).system_prompt.set(prompt_text)
        preview = prompt_text[:200] + ("..." if len(prompt_text) > 200 else "")
        await interaction.response.send_message(
            f"✅ 已更新個人提示詞。Preview: ```{preview}```", ephemeral=True
        )


class SetPromptButton(discord.ui.Button):
    """Button to open the personal prompt modal."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context) -> None:
        super().__init__(label="Set Personal Prompt", style=discord.ButtonStyle.primary)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(PromptModal(self.cog, self.ctx))


class ShowPromptButton(discord.ui.Button):
    """Button to display the current prompt(s) in an embed."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context) -> None:
        super().__init__(label="View Prompt", style=discord.ButtonStyle.secondary)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        user_prompt = await self.cog.config.user(self.ctx.author).system_prompt()
        default_prompt = await self.cog.config.default_system_prompt()

        if not user_prompt and not default_prompt:
            await interaction.response.send_message("目前沒有設定任何提示詞。", ephemeral=True)
            return

        embed = discord.Embed(title="📝 System Prompt", color=discord.Color.blurple())
        if user_prompt:
            embed.add_field(
                name="Personal",
                value=f"```{user_prompt[:1000]}{'...' if len(user_prompt) > 1000 else ''}```",
                inline=False,
            )
        if default_prompt:
            embed.add_field(
                name="Default",
                value=f"```{default_prompt[:1000]}{'...' if len(default_prompt) > 1000 else ''}```",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class ClearPromptButton(discord.ui.Button):
    """Button to clear the user's personal prompt."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context) -> None:
        super().__init__(label="Clear Prompt", style=discord.ButtonStyle.secondary)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.cog.config.user(self.ctx.author).system_prompt.set(None)
        await interaction.response.send_message("✅ 個人提示詞已清除。", ephemeral=True)


class DummyToggleButton(discord.ui.Button):
    """Owner-only toggle for offline dummy mode (if enabled by env flag)."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, enabled: bool) -> None:
        label = f"Dummy Mode: {'ON' if enabled else 'OFF'}"
        style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary
        super().__init__(label=label, style=style)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction) -> None:
        new_state = not await self.cog.config.use_dummy_api()
        await self.cog.config.use_dummy_api.set(new_state)
        await self.cog._init_client()

        self.label = f"Dummy Mode: {'ON' if new_state else 'OFF'}"
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
        embed = await self.cog._build_config_embed(self.ctx, owner_mode, new_state)
        await interaction.response.edit_message(embed=embed, view=self.view)
        await interaction.followup.send(
            "✅ Dummy API mode 已啟用。" if new_state else "✅ Dummy API mode 已關閉。",
            ephemeral=True,
        )


