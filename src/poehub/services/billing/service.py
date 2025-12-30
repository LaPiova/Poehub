"""Billing and Budget Service."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import TYPE_CHECKING

import discord

from .crawler import PricingCrawler
from .oracle import PricingOracle

if TYPE_CHECKING:
    from redbot.core import Config
    from redbot.core.bot import Red

log = logging.getLogger("red.poehub.services.billing")


class BillingService:
    """Manages billing, budgets, and pricing updates."""

    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config
        self.pricing_task: asyncio.Task | None = None

    async def start_pricing_loop(self):
        """Start the background pricing update loop."""
        if self.pricing_task:
            self.pricing_task.cancel()
        self.pricing_task = self.bot.loop.create_task(self._pricing_update_loop())

    async def stop_pricing_loop(self):
        """Stop the background pricing update loop."""
        if self.pricing_task:
            self.pricing_task.cancel()
            try:
                await self.pricing_task
            except asyncio.CancelledError:
                pass
            self.pricing_task = None

    async def _pricing_update_loop(self):
        """Background task to update pricing monthly (or daily for safety)."""
        await self.bot.wait_until_ready()
        while True:
            try:
                # Update prices
                log.info("Running automatic pricing update...")
                new_rates = await PricingCrawler.fetch_rates()
                if new_rates:
                    PricingOracle.load_dynamic_rates(new_rates)

                    # Persist
                    current_rates = await self.config.dynamic_rates()
                    current_rates.update(new_rates)
                    await self.config.dynamic_rates.set(current_rates)
                    log.info(
                        f"Automatic pricing update complete. {len(new_rates)} rates loaded."
                    )
            except Exception:
                log.exception("Error in pricing update loop")

            # Sleep for 24 hours
            await asyncio.sleep(86400)

    async def resolve_billing_guild(
        self, user: discord.User, channel: discord.abc.Messageable
    ) -> discord.Guild | None:
        """Determine which guild should be billed for the request."""
        # 1. Guild Channel
        if hasattr(channel, "guild") and channel.guild:
            if await self.verify_guild_access(user, channel.guild):
                return channel.guild
            return None

        # 2. DM Channel
        candidates = []
        # We need to iterate over mutual guilds where the bot is present
        # user.mutual_guilds is available in discord.py
        for guild in user.mutual_guilds:
            if await self.verify_guild_access(user, guild):
                candidates.append(guild)

        if not candidates:
            return None

        # Determine stability - Sort by ID to ensure deterministic choice
        candidates.sort(key=lambda g: g.id)

        if len(candidates) == 1:
            return candidates[0]

        # Multiple candidates: Pick the one with higher limit (None = Infinite is highest)
        best_guild = None
        best_limit = -1.0

        for guild in candidates:
            limit = await self.config.guild(guild).monthly_limit()
            if limit is None:
                return guild  # Infinite wins immediately
            if limit > best_limit:
                best_limit = limit
                best_guild = guild

        return best_guild

    async def verify_guild_access(self, user: discord.User, guild: discord.Guild) -> bool:
        """Check if a user has access to a specific guild (via roles or general access)."""
        # 1. Check if guild access is allowed globally
        if not await self.config.guild(guild).access_allowed():
            return False

        # 2. Check Role Restrictions
        allowed_roles = await self.config.guild(guild).allowed_roles()
        if not allowed_roles:
            return True  # No restrictions

        member = guild.get_member(user.id)
        if not member:
            # Should not happen if we are checking mutual guilds, but possible if cache is stale
            # Try fetching
            try:
                member = await guild.fetch_member(user.id)
            except discord.NotFound:
                return False

        user_role_ids = [r.id for r in member.roles]
        # Check intersection
        has_role = any(r_id in user_role_ids for r_id in allowed_roles)
        return has_role

    async def _reset_budget_if_new_month(self, guild: discord.Guild) -> None:
        """Reset guild spend if we are in a new month."""
        current_month = datetime.datetime.now().strftime("%Y-%m")
        last_reset = await self.config.guild(guild).last_reset_month()

        # Debug log for reset check could be too spammy if called often, so keeping it concise
        # log.debug(f"Reset Check - Guild: {guild.id}, Stored: {last_reset}, Current: {current_month}")

        if last_reset != current_month:
            # It's a new month! Reset spend (Both USD and Points).
            log.info(f"TRIGGERING RESET for Guild {guild.id}")
            await self.config.guild(guild).current_spend.set(0.0)
            await self.config.guild(guild).current_spend_points.set(0.0)
            await self.config.guild(guild).last_reset_month.set(current_month)
            log.info(
                f"Reset monthly budget for guild {guild.name} ({guild.id}) - Month: {current_month}"
            )

    async def check_budget(self, guild: discord.Guild) -> bool:
        """Check if guild has budget remaining."""
        await self._reset_budget_if_new_month(guild)

        # Determine strictness based on active provider
        active_provider = await self.config.active_provider()

        if active_provider == "poe":
            limit = await self.config.guild(guild).monthly_limit_points()
            spend = await self.config.guild(guild).current_spend_points()
            if limit is None:
                return True
            return spend < limit
        else:
            limit = await self.config.guild(guild).monthly_limit()
            spend = await self.config.guild(guild).current_spend()
            if limit is None:
                return True
            return spend < limit

    async def update_spend(
        self, guild: discord.Guild, cost: float, currency: str = "USD"
    ):
        """Update spend for guild."""
        if cost <= 0:
            return

        if currency == "Points":
            current = await self.config.guild(guild).current_spend_points()
            if current is None:
                current = 0.0
            new_spend = current + cost
            await self.config.guild(guild).current_spend_points.set(new_spend)
            log.info(
                f"Guild {guild.id} POINTS updated: {current} + {cost} -> {new_spend}"
            )
        else:
            # Default to USD logic
            current = await self.config.guild(guild).current_spend()
            if current is None:
                current = 0.0
            new_spend = current + cost
            await self.config.guild(guild).current_spend.set(new_spend)
            log.info(f"Guild {guild.id} USD updated: {current} + {cost} -> {new_spend}")
