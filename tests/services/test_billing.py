from unittest.mock import AsyncMock, Mock, patch

import discord
import pytest

from poehub.services.billing import BillingService


@pytest.mark.asyncio
class TestBillingService:
    @pytest.fixture
    def mock_bot(self):
        return AsyncMock()

    @pytest.fixture
    def mock_config(self):
        # Config itself is synchronous for group access but values are awaitable
        config = Mock()
        return config

    @pytest.fixture
    def service(self, mock_bot, mock_config):
        return BillingService(mock_bot, mock_config)

    async def test_update_spend_usd(self, service, mock_config):
        guild = Mock(spec=discord.Guild)
        guild.id = 123

        mock_guild_config = Mock()
        # config.guild(guild) - synchronous return of group
        mock_config.guild.return_value = mock_guild_config

        # .current_spend is a Value object (synchronous access),
        # but operations on it (like set/get) are async.
        # However, Red's syntax is usually await config.guild(g).current_spend()
        # If .current_spend is an AsyncMock, then calling it returns a coroutine.
        mock_spend_value = AsyncMock()
        mock_guild_config.current_spend = mock_spend_value
        mock_spend_value.return_value = 10.0

        await service.update_spend(guild, 5.0, currency="USD")

        mock_spend_value.set.assert_called_with(15.0)

    async def test_update_spend_points(self, service, mock_config):
        guild = Mock(spec=discord.Guild)
        guild.id = 123

        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config

        mock_points_value = AsyncMock()
        mock_guild_config.current_spend_points = mock_points_value
        mock_points_value.return_value = 1000

        await service.update_spend(guild, 500, currency="Points")

        mock_points_value.set.assert_called_with(1500)

    async def test_check_budget_pass(self, service, mock_config):
        guild = Mock(spec=discord.Guild)

        # config.active_provider() is async
        mock_config.active_provider = AsyncMock(return_value="openai")

        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config

        # Accessors like monthly_limit() return awaitables
        mock_guild_config.monthly_limit = AsyncMock(return_value=10.0)
        mock_guild_config.current_spend = AsyncMock(return_value=5.0)
        mock_guild_config.last_reset_month = AsyncMock(
            return_value="should_match_current_date"
        )
        mock_guild_config.current_spend_points.set = AsyncMock()
        mock_guild_config.current_spend.set = AsyncMock()

        with patch("poehub.services.billing.service.datetime.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "should_match_current_date"
            result = await service.check_budget(guild)
            assert result is True

    async def test_check_budget_fail(self, service, mock_config):
        guild = Mock(spec=discord.Guild)
        mock_config.active_provider = AsyncMock(return_value="openai")

        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config

        mock_guild_config.monthly_limit = AsyncMock(return_value=10.0)
        mock_guild_config.current_spend = AsyncMock(return_value=11.0)
        mock_guild_config.last_reset_month = AsyncMock(return_value="2025-12")

        with patch("poehub.services.billing.service.datetime.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2025-12"

            result = await service.check_budget(guild)
            assert result is False

    async def test_resolve_billing_guild_direct(self, service, mock_config):
        user = Mock(spec=discord.User)
        channel = Mock(spec=discord.TextChannel)
        guild = Mock(spec=discord.Guild)
        channel.guild = guild

        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config
        mock_guild_config.access_allowed = AsyncMock(return_value=True)

        result = await service.resolve_billing_guild(user, channel)
        assert result == guild

    async def test_resolve_billing_guild_dm(self, service, mock_config):
        user = Mock(spec=discord.User)
        channel = Mock(spec=discord.DMChannel)
        channel.guild = None

        guild1 = Mock(spec=discord.Guild)
        guild1.id = 100
        user.mutual_guilds = [guild1]

        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config
        mock_guild_config.access_allowed = AsyncMock(return_value=True)
        mock_guild_config.monthly_limit = AsyncMock(return_value=10.0)

        result = await service.resolve_billing_guild(user, channel)
        assert result == guild1
