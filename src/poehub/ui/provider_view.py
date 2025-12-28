"""Interactive provider configuration UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from redbot.core import commands as red_commands

from ..core.i18n import tr
from .access_view import AccessControlView
from .common import CloseMenuButton

if TYPE_CHECKING:  # pragma: no cover
    from ..poehub import PoeHub


class ProviderConfigView(discord.ui.View):
    """Interactive provider configuration menu."""

    def __init__(
        self,
        cog: PoeHub,
        ctx: red_commands.Context,
        lang: str,
    ) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.message: discord.Message | None = None

        self.add_item(ProviderSelect(cog, ctx, lang))
        self.add_item(SetKeyButton(cog, ctx, lang))
        self.add_item(ManageAccessButton(cog, ctx, lang))
        self.add_item(SetDefaultPromptButton(cog, ctx, lang))
        self.add_item(CheckPricingButton(cog, lang))
        self.add_item(RefreshButton(lang))
        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                tr(self.lang, "RESTRICTED_MENU"),
                ephemeral=True,
            )
            return False
        return True

    async def refresh_content(self, interaction: discord.Interaction) -> None:
        """Refresh the view content."""
        active = await self.cog.config.active_provider()
        dummy = await self.cog.config.use_dummy_api()

        embed = discord.Embed(
            title="Provider Configuration",
            description="Select an AI provider and set your API key.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Active Provider", value=f"**{active}**", inline=True)
        embed.add_field(name="Dummy Mode", value="ON" if dummy else "OFF", inline=True)

        if active != "dummy":
            keys = await self.cog.config.provider_keys()
            has_key = bool(keys.get(active))
            embed.add_field(
                name="API Key Set", value="✅ Yes" if has_key else "❌ No", inline=True
            )

        await interaction.response.edit_message(embed=embed, view=self)


class ProviderSelect(discord.ui.Select):
    """Dropdown to switch active provider."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        providers = [
            ("Poe", "poe", "Standard Poe API"),
            ("OpenAI", "openai", "Direct OpenAI API"),
            ("Anthropic", "anthropic", "Direct Claude API"),
            ("Google", "google", "Direct Gemini API"),
            ("DeepSeek", "deepseek", "Budget-friendly OpenAI-compatible"),
            ("OpenRouter", "openrouter", "Aggregator for many models"),
            ("Dummy", "dummy", "Offline Testing Mode"),
        ]

        options = []
        for label, value, desc in providers:
            options.append(
                discord.SelectOption(label=label, value=value, description=desc)
            )

        super().__init__(
            placeholder=tr(
                lang, "PROVIDER_SELECT_PLACEHOLDER", default="Select AI Provider..."
            ),
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        provider = self.values[0]

        # Handle Dummy logic
        if provider == "dummy":
            if not self.cog.allow_dummy_mode:
                await interaction.response.send_message(
                    "❌ Dummy mode is disabled in this build.", ephemeral=True
                )
                return
            await self.cog.config.use_dummy_api.set(True)
        else:
            await self.cog.config.use_dummy_api.set(False)

        await self.cog.config.active_provider.set(provider)
        await self.cog._init_client()

        if isinstance(self.view, ProviderConfigView):
            await self.view.refresh_content(interaction)


class APIKeyModal(discord.ui.Modal):
    """Modal to input API Key."""

    def __init__(self, cog: PoeHub, provider: str, lang: str) -> None:
        super().__init__(title=f"Set API Key for {provider.title()}")
        self.cog = cog
        self.provider = provider
        self.lang = lang

        self.api_key = discord.ui.TextInput(
            label="API Key",
            placeholder=f"Paste your {provider} API key here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=200,
        )
        self.add_item(self.api_key)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        key = self.api_key.value.strip()

        provider_keys = await self.cog.config.provider_keys()
        provider_keys[self.provider] = key
        await self.cog.config.provider_keys.set(provider_keys)

        # Re-init if active
        active = await self.cog.config.active_provider()
        if active == self.provider:
            await self.cog._init_client()

        await interaction.response.send_message(
            f"✅ API Key for **{self.provider}** has been updated!", ephemeral=True
        )


class SetKeyButton(discord.ui.Button):
    """Button to open API Key modal for active provider."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label="Set API Key", style=discord.ButtonStyle.primary, emoji="🔑", row=1
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        active_provider = await self.cog.config.active_provider()
        if active_provider == "dummy":
            await interaction.response.send_message(
                "⚠️ Dummy provider does not need an API key.", ephemeral=True
            )
            return

        await interaction.response.send_modal(
            APIKeyModal(self.cog, active_provider, self.lang)
        )


class ManageAccessButton(discord.ui.Button):
    """Button to open Access Control view."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label="Manage Access & Budget",
            style=discord.ButtonStyle.secondary,
            emoji="🛡️",
            row=2,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        view = AccessControlView(self.cog, self.ctx, self.lang)
        # Initial update to set correct state (no guild selected)
        await view.update_view(interaction)


class CheckPricingButton(discord.ui.Button):
    """Button to check current model pricing."""

    def __init__(self, cog: PoeHub, lang: str) -> None:
        super().__init__(
            label="Check Pricing", style=discord.ButtonStyle.secondary, emoji="🏷️", row=2
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction) -> None:
        # Get context
        user_conf = self.cog.config.user(interaction.user)
        provider = await self.cog.config.active_provider()
        model = await user_conf.model()

        # Get Price
        from ..services.billing.oracle import PricingOracle

        in_price, out_price, currency = PricingOracle.get_price(provider, model)

        embed = discord.Embed(
            title=f"🏷️ Pricing Check: {provider.title()}",
            description=f"Current rates for **{model}**",
            color=discord.Color.green(),
        )

        # Format Logic
        if currency == "Points":
            suffix = "pts"
            # Points are usually per message or compute, but Oracle returns roughly per 1M for consistency
            # Actually, Oracle fallback for Poe was 20k points.
            # Let's just show the raw numbers
            rate_desc = f"**Input:** {in_price:,.0f} {suffix}/1M tokens\n**Output:** {out_price:,.0f} {suffix}/1M tokens"
            note = "⚠️ Poe prices vary dynamically per message complexity."
        else:
            rate_desc = f"**Input:** ${in_price:.2f}/1M tokens\n**Output:** ${out_price:.2f}/1M tokens"
            note = "sourced from pricing oracle"

        embed.add_field(name="Rate Card", value=rate_desc, inline=False)
        embed.set_footer(text=f"Currency: {currency} • {note}")

        await interaction.response.send_message(embed=embed, ephemeral=True)


class SetDefaultPromptButton(discord.ui.Button):
    """Button to set global default prompt."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label="Set Default Prompt",
            style=discord.ButtonStyle.secondary,
            emoji="📝",
            row=2,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        # Re-using the logic from config_view.py's PromptModal but saving to default config
        await interaction.response.send_modal(DefaultPromptModal(self.cog, self.lang))


class DefaultPromptModal(discord.ui.Modal):
    def __init__(self, cog: PoeHub, lang: str) -> None:
        super().__init__(title="Global Default System Prompt")
        self.cog = cog

        self.prompt = discord.ui.TextInput(
            label="System Prompt",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1500,
            placeholder="You are a helpful assistant...",
        )
        self.add_item(self.prompt)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.config.default_system_prompt.set(self.prompt.value)
        await interaction.response.send_message(
            "✅ Global default system prompt updated.", ephemeral=True
        )


class RefreshButton(discord.ui.Button):
    """Button to refresh the view."""

    def __init__(self, lang: str) -> None:
        super().__init__(
            label="Refresh",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            row=1,
        )
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        if isinstance(self.view, ProviderConfigView):
            await self.view.refresh_content(interaction)
