"""Access Control and Budget Management UI."""

from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from redbot.core import commands as red_commands

from ..core.i18n import tr
from .common import CloseMenuButton

if TYPE_CHECKING:
    from ..poehub import PoeHub


class AccessControlView(discord.ui.View):
    """View for managing guild access and budgets."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.active_guild: discord.Guild | None = None

        # Initial components
        self.add_item(GuildSelect(cog, ctx, lang))
        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))

        # These will be added/enabled once a guild is selected
        self.toggle_btn = ToggleAccessButton(cog, lang)
        self.limit_btn = SetLimitButton(cog, lang)
        self.reset_btn = ResetSpendButton(cog, lang)
        self.back_btn = BackButton(cog, ctx, lang)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                tr(self.lang, "RESTRICTED_MENU"), ephemeral=True
            )
            return False
        return True

    async def update_view(self, interaction: discord.Interaction):
        """Update view components based on selected guild."""
        self.clear_items()
        self.add_item(GuildSelect(self.cog, self.ctx, self.lang))

        embed = discord.Embed(
            title="🛡️ Access Control & Budget Manager", color=discord.Color.blue()
        )

        if self.active_guild:
            # Fetch Data
            guild_conf = self.cog.config.guild(self.active_guild)
            is_allowed = await guild_conf.access_allowed()

            # USD Stats
            limit_usd = await guild_conf.monthly_limit()
            spend_usd = await guild_conf.current_spend() or 0.0

            # Points Stats
            limit_pts = await guild_conf.monthly_limit_points()
            spend_pts = await guild_conf.current_spend_points() or 0.0

            # Roles
            allowed_roles = await guild_conf.allowed_roles()
            role_count = len(allowed_roles) if allowed_roles else 0
            role_status = (
                "🌍 Everyone (No restrictions)"
                if role_count == 0
                else f"🔒 Restricted to {role_count} role(s)"
            )

            # Format Limits
            usd_str = "∞" if limit_usd is None else f"${limit_usd:.2f}"
            pts_str = "∞" if limit_pts is None else f"{limit_pts:,}"

            # Status Emoji
            status = "✅ Authorized" if is_allowed else "⛔ Unauthorized"

            embed.description = f"**Selected Guild:** {self.active_guild.name} (`{self.active_guild.id}`)"
            embed.add_field(name="Status", value=status, inline=True)
            embed.add_field(name="Role Access", value=role_status, inline=True)

            embed.add_field(
                name="💰 Standard Budget (USD)",
                value=f"Limit: **{usd_str}**\nSpent: **${spend_usd:.2f}**",
                inline=True,
            )
            embed.add_field(
                name="🔮 Poe Budget (Points)",
                value=f"Limit: **{pts_str}**\nSpent: **{spend_pts:,.0f}**",
                inline=True,
            )

            # Update Buttons

            # Update Buttons
            self.toggle_btn.update_style(is_allowed)
            self.add_item(self.toggle_btn)
            self.add_item(self.limit_btn)
            self.add_item(self.reset_btn)

            # Add Role Select
            self.add_item(RoleSelect(self.cog, self.active_guild, allowed_roles))
        else:
            embed.description = "Please select a guild from the dropdown below to manage its permissions."

        self.add_item(self.back_btn)
        self.add_item(CloseMenuButton(label=tr(self.lang, "CLOSE_MENU")))

        await interaction.response.edit_message(embed=embed, view=self)


class GuildSelect(discord.ui.Select):
    """Dropdown to select a guild (shared only)."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        options = []
        # List all shared guilds
        # Limit to 25 for Discord select menu
        # Prioritize authorized guilds? Or just alphabetical?
        # Let's do alphabetical.

        # We need to find guilds where the bot is.
        # Since this is owner-only, we can look at cog.bot.guilds

        guilds = sorted(cog.bot.guilds, key=lambda g: g.name.lower())[:25]

        if not guilds:
            options.append(discord.SelectOption(label="No Guilds Found", value="none"))

        for g in guilds:
            options.append(
                discord.SelectOption(
                    label=g.name[:100], value=str(g.id), description=f"ID: {g.id}"
                )
            )

        super().__init__(
            placeholder="Select a Guild to Manage...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return

        guild_id = int(self.values[0])
        guild = self.cog.bot.get_guild(guild_id)

        if isinstance(self.view, AccessControlView):
            self.view.active_guild = guild
            await self.view.update_view(interaction)


class RoleSelect(discord.ui.Select):
    """Dropdown to manage allowed roles."""

    def __init__(
        self, cog: PoeHub, guild: discord.Guild, current_allowed: list[int]
    ) -> None:
        self.cog = cog
        self.guild = guild

        options = []
        # Filter and sort roles
        # Exclude managed roles and @everyone
        roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
        valid_roles = [r for r in roles if not r.is_default() and not r.is_bot_managed()]

        # Slice top 25
        for role in valid_roles[:25]:
            is_selected = role.id in (current_allowed or [])
            options.append(
                discord.SelectOption(
                    label=role.name[:100],
                    value=str(role.id),
                    default=is_selected,
                    description=f"ID: {role.id}",
                )
            )

        if not options:
            options.append(
                discord.SelectOption(
                    label="No valid roles found", value="none", default=False
                )
            )

        super().__init__(
            placeholder="Select Allowed Roles (Empty = All)",
            min_values=0,
            max_values=len(options),
            options=options,
            row=2,
        )

    async def callback(self, interaction: discord.Interaction):
        if not self.view.active_guild:
            return

        if "none" in self.values:
            # Should not happen if strictly valid roles, but handle it
            pass

        selected_ids = [int(v) for v in self.values if v != "none"]
        await self.cog.config.guild(self.view.active_guild).allowed_roles.set(
            selected_ids
        )
        await self.view.update_view(interaction)


class ToggleAccessButton(discord.ui.Button):
    def __init__(self, cog: PoeHub, lang: str):
        super().__init__(row=1)
        self.cog = cog

    def update_style(self, is_allowed: bool):
        if is_allowed:
            self.label = "Revoke Access"
            self.style = discord.ButtonStyle.danger
            self.emoji = "⛔"
        else:
            self.label = "Authorize Access"
            self.style = discord.ButtonStyle.success
            self.emoji = "✅"

    async def callback(self, interaction: discord.Interaction):
        view: AccessControlView = self.view
        if not view.active_guild:
            return

        # Toggle
        current = await self.cog.config.guild(view.active_guild).access_allowed()
        await self.cog.config.guild(view.active_guild).access_allowed.set(not current)

        await view.update_view(interaction)


class SetLimitButton(discord.ui.Button):
    def __init__(self, cog: PoeHub, lang: str):
        super().__init__(
            label="Set Limits", style=discord.ButtonStyle.secondary, emoji="💰", row=1
        )
        self.cog = cog
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        view: AccessControlView = self.view
        if not view.active_guild:
            return
        await interaction.response.send_modal(
            BudgetLimitModal(self.cog, view.active_guild, view)
        )


class ResetSpendButton(discord.ui.Button):
    def __init__(self, cog: PoeHub, lang: str):
        super().__init__(
            label="Reset/Clear Spend",
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            row=1,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        view: AccessControlView = self.view
        if not view.active_guild:
            return

        # Reset everything or ask? Let's just reset everything for simplicity in this admin tool.
        # Or add a confirmation?

        await self.cog.config.guild(view.active_guild).current_spend.set(0.0)
        await self.cog.config.guild(view.active_guild).current_spend_points.set(0.0)

        await view.update_view(interaction)
        await interaction.followup.send(
            f"Status: Spend usage (USD & Points) reset for {view.active_guild.name}",
            ephemeral=True,
        )


class BudgetLimitModal(discord.ui.Modal):
    def __init__(
        self, cog: PoeHub, guild: discord.Guild, parent_view: AccessControlView
    ):
        super().__init__(title=f"Set Budget: {guild.name[:30]}")
        self.cog = cog
        self.guild = guild
        self.parent_view = parent_view

        self.usd_input = discord.ui.TextInput(
            label="Standard Limit (USD)",
            placeholder="e.g. 5.00 (Leave empty for Infinite)",
            required=False,
        )
        self.pts_input = discord.ui.TextInput(
            label="Poe Limit (Points)",
            placeholder="e.g. 100000 (Leave empty for Infinite)",
            required=False,
        )

        self.add_item(self.usd_input)
        self.add_item(self.pts_input)

    async def on_submit(self, interaction: discord.Interaction):
        # Handle USD
        usd_val = self.usd_input.value.strip()
        usd_msg = ""
        if not usd_val:
            await self.cog.config.guild(self.guild).monthly_limit.set(None)
            usd_msg = "USD: Infinite"
        else:
            try:
                limit = float(usd_val)
                if limit < 0:
                    raise ValueError
                await self.cog.config.guild(self.guild).monthly_limit.set(limit)
                usd_msg = f"USD: ${limit:.2f}"
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid USD value.", ephemeral=True
                )
                return

        # Handle Points
        pts_val = self.pts_input.value.strip()
        pts_msg = ""
        if not pts_val:
            await self.cog.config.guild(self.guild).monthly_limit_points.set(None)
            pts_msg = "Points: Infinite"
        else:
            try:
                limit_p = int(float(pts_val))  # Handle 100.0 gracefully
                if limit_p < 0:
                    raise ValueError
                await self.cog.config.guild(self.guild).monthly_limit_points.set(
                    limit_p
                )
                pts_msg = f"Points: {limit_p:,}"
            except ValueError:
                await interaction.response.send_message(
                    "❌ Invalid Points value.", ephemeral=True
                )
                return

        # Refresh Parent
        await self.parent_view.update_view(interaction)

        msg = f"✅ Limits updated!\n{usd_msg}\n{pts_msg}"

        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)


class BackButton(discord.ui.Button):
    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str):
        super().__init__(
            label="Back to Settings",
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=3,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction):
        # Local import to avoid circular dependency
        from .provider_view import ProviderConfigView

        view = ProviderConfigView(self.cog, self.ctx, self.lang)
        await view.refresh_content(interaction)
