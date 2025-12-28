import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import discord
import pytest

from poehub.models import TokenUsage
from poehub.services.billing import BillingService
from poehub.services.billing.crawler import PricingCrawler
from poehub.services.billing.oracle import PricingOracle


@pytest.mark.asyncio
class TestPricingCrawler:
    async def test_fetch_rates_success(self):
        mock_data = {
            "gpt-4": {
                "input_cost_per_token": 0.00003,
                "output_cost_per_token": 0.00006,
                "litellm_provider": "openai"
            },
            "claude-3": {
                # missing costs, should be skipped
            },
            "bad-data": "not-a-dict"
        }

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = mock_data

        # Mock the context manager returned by session.get()
        # session.get(...) -> returns this ctx mgr
        get_ctx_mgr = MagicMock()
        get_ctx_mgr.__aenter__.return_value = mock_response
        get_ctx_mgr.__aexit__.return_value = None

        # Mock session object
        mock_session_obj = MagicMock()
        mock_session_obj.get.return_value = get_ctx_mgr

        # Mock ClientSession() constructor context manager
        session_ctx_mgr = MagicMock()
        session_ctx_mgr.__aenter__.return_value = mock_session_obj
        session_ctx_mgr.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=session_ctx_mgr):
            rates = await PricingCrawler.fetch_rates()

        assert "gpt-4" in rates
        # 0.00003 * 1M = 30.0
        assert rates["gpt-4"] == (30.0, 60.0, "USD")
        assert "openai/gpt-4" in rates
        assert "claude-3" not in rates

    async def test_fetch_rates_failure(self):
        mock_response = AsyncMock()
        mock_response.status = 404

        get_ctx_mgr = MagicMock()
        get_ctx_mgr.__aenter__.return_value = mock_response
        get_ctx_mgr.__aexit__.return_value = None

        mock_session_obj = MagicMock()
        mock_session_obj.get.return_value = get_ctx_mgr

        session_ctx_mgr = MagicMock()
        session_ctx_mgr.__aenter__.return_value = mock_session_obj
        session_ctx_mgr.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=session_ctx_mgr):
            rates = await PricingCrawler.fetch_rates()

        assert rates == {}

    async def test_fetch_rates_exception(self):
         # Mock ClientSession raising exception on init or enter
         with patch("aiohttp.ClientSession", side_effect=Exception("network error")):
            rates = await PricingCrawler.fetch_rates()
            assert rates == {}

class TestPricingOracle:
    def setup_method(self):
        PricingOracle._DYNAMIC_RATES.clear()

    def test_get_price_exact(self):
        # Using a known rate from source code or adding one
        PricingOracle.RATES["test/model"] = (1.0, 2.0)

        price = PricingOracle.get_price("test", "model")
        assert price == (1.0, 2.0, "USD")

    def test_get_price_poe_default(self):
        price = PricingOracle.get_price("poe", "unknown-model")
        assert price[2] == "Points"
        assert price[0] > 0

    def test_get_price_poe_exact(self):
        # poe/claude-3.5-sonnet is in RATES map in source
        price = PricingOracle.get_price("poe", "claude-3.5-sonnet")
        assert price[2] == "Points"

    def test_get_price_dynamic(self):
        PricingOracle.load_dynamic_rates({"my/model": (10.0, 10.0, "USD")})
        price = PricingOracle.get_price("my", "model")
        assert price == (10.0, 10.0, "USD")

    def test_update_rate(self):
        PricingOracle.update_rate("custom", "gpt", 5.0, 5.0, "EUR")
        price = PricingOracle.get_price("custom", "gpt")
        assert price == (5.0, 5.0, "EUR")

    def test_calculate_cost_usd(self):
        PricingOracle.update_rate("test", "usd", 1.0, 2.0, "USD") # $1 per 1M in, $2 per 1M out
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        cost = PricingOracle.calculate_cost("test", "usd", usage)
        assert cost == 3.0

    def test_calculate_cost_points(self):
        usage = TokenUsage(input_tokens=10, output_tokens=10, currency="Points", cost=50.0)
        cost = PricingOracle.calculate_cost("poe", "any", usage)
        assert cost == 50.0

    def test_calculate_cost_currency_override(self):
        # If oracle says Points but usage didn't specify
        PricingOracle.update_rate("test", "points", 1.0, 1.0, "Points")
        usage = TokenUsage(input_tokens=0, output_tokens=0)
        PricingOracle.calculate_cost("test", "points", usage)
        assert usage.currency == "Points"

@pytest.mark.asyncio
class TestBillingService:
    @pytest.fixture
    def mock_bot(self):
        bot = AsyncMock()
        bot.loop = Mock()
        return bot

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.dynamic_rates = AsyncMock()
        return config

    @pytest.fixture
    def service(self, mock_bot, mock_config):
        return BillingService(mock_bot, mock_config)

    async def test_start_pricing_loop(self, service, mock_bot):
        await service.start_pricing_loop()
        mock_bot.loop.create_task.assert_called_once()

    async def test_pricing_update_loop_success(self, service, mock_config):
        mock_rates = {"gpt-4": (30.0, 60.0, "USD")}
        mock_config.dynamic_rates.return_value = {}

        with patch("poehub.services.billing.service.PricingCrawler.fetch_rates", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_rates

            with patch("poehub.services.billing.service.PricingOracle.load_dynamic_rates") as mock_oracle:
                with patch("poehub.services.billing.service.asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
                    try:
                        await service._pricing_update_loop()
                    except asyncio.CancelledError:
                        pass

                mock_oracle.assert_called_with(mock_rates)

        mock_config.dynamic_rates.set.assert_called()

    async def test_pricing_update_loop_error(self, service):
        with patch("poehub.services.billing.service.PricingCrawler.fetch_rates", side_effect=Exception("oops")):
            with patch("poehub.services.billing.service.asyncio.sleep", side_effect=[None, asyncio.CancelledError]):
                try:
                    await service._pricing_update_loop()
                except asyncio.CancelledError:
                    pass

    async def test_update_spend_usd(self, service, mock_config):
        guild = Mock(spec=discord.Guild)
        guild.id = 123
        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config
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

    async def test_update_spend_zero(self, service, mock_config):
        guild = Mock(spec=discord.Guild)
        await service.update_spend(guild, 0, currency="USD")
        # Should not make any calls
        mock_config.guild.assert_not_called()

    async def test_reset_budget_execution(self, service, mock_config):
        # Force a reset
        guild = Mock(spec=discord.Guild)
        guild.id = 999
        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config

        mock_guild_config.last_reset_month = AsyncMock(return_value="2000-01") # Old month
        mock_guild_config.current_spend.set = AsyncMock()
        mock_guild_config.current_spend_points.set = AsyncMock()
        mock_guild_config.last_reset_month.set = AsyncMock()

        await service._reset_budget_if_new_month(guild)

        mock_guild_config.current_spend.set.assert_called_with(0.0)
        mock_guild_config.current_spend_points.set.assert_called_with(0.0)
        mock_guild_config.last_reset_month.set.assert_called()

    async def test_check_budget_pass(self, service, mock_config):
        guild = Mock(spec=discord.Guild)
        mock_config.active_provider = AsyncMock(return_value="openai")
        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config
        mock_guild_config.monthly_limit = AsyncMock(return_value=10.0)
        mock_guild_config.current_spend = AsyncMock(return_value=5.0)
        mock_guild_config.last_reset_month = AsyncMock(return_value="2025-12")
        mock_guild_config.current_spend_points.set = AsyncMock()
        mock_guild_config.current_spend.set = AsyncMock()

        with patch("poehub.services.billing.service.datetime.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2025-12"
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

    async def test_check_budget_poe_pass(self, service, mock_config):
        guild = Mock(spec=discord.Guild)
        mock_config.active_provider = AsyncMock(return_value="poe")
        mock_guild_config = Mock()
        mock_config.guild.return_value = mock_guild_config
        mock_guild_config.monthly_limit_points = AsyncMock(return_value=1000)
        mock_guild_config.current_spend_points = AsyncMock(return_value=500)
        mock_guild_config.last_reset_month = AsyncMock(return_value="2025-12")

        with patch("poehub.services.billing.service.datetime.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = "2025-12"
            result = await service.check_budget(guild)
            assert result is True

    async def test_resolve_billing_guild_dm_sorted(self, service, mock_config):
        user = Mock(spec=discord.User)
        channel = Mock(spec=discord.DMChannel)
        channel.guild = None

        guild1 = Mock(spec=discord.Guild)
        guild1.id = 100
        guild2 = Mock(spec=discord.Guild)
        guild2.id = 200
        user.mutual_guilds = [guild1, guild2]

        def guild_side_effect(g):
            m = Mock()
            m.access_allowed = AsyncMock(return_value=True)
            if g.id == 100:
                m.monthly_limit = AsyncMock(return_value=10.0)
            else:
                m.monthly_limit = AsyncMock(return_value=20.0)
            return m

        mock_config.guild.side_effect = guild_side_effect

        result = await service.resolve_billing_guild(user, channel)
        assert result == guild2

    async def test_resolve_billing_guild_single(self, service, mock_config):
        # Line 82 coverage
        user = Mock(spec=discord.User)
        channel = Mock(spec=discord.DMChannel)
        channel.guild = None

        guild1 = Mock(spec=discord.Guild)
        guild1.id = 100
        user.mutual_guilds = [guild1]

        mock_g = Mock()
        mock_config.guild.return_value = mock_g
        mock_g.access_allowed = AsyncMock(return_value=True)
        # Limit doesn't matter for single guild logic (if candidates==1)

        result = await service.resolve_billing_guild(user, channel)
        assert result == guild1

    async def test_resolve_billing_guild_none(self, service, mock_config):
        # Line 76 coverage
        user = Mock(spec=discord.User)
        channel = Mock(spec=discord.DMChannel)
        channel.guild = None
        user.mutual_guilds = [] # No mutual guilds

        result = await service.resolve_billing_guild(user, channel)
        assert result is None

    async def test_resolve_billing_guild_infinite(self, service, mock_config):
        # Line 91 coverage
        user = Mock(spec=discord.User)
        channel = Mock(spec=discord.DMChannel)
        channel.guild = None

        guild1 = Mock(spec=discord.Guild)
        guild1.id = 100
        guild2 = Mock(spec=discord.Guild)
        guild2.id = 200
        user.mutual_guilds = [guild1, guild2]

        def guild_side_effect(g):
            m = Mock()
            m.access_allowed = AsyncMock(return_value=True)
            if g.id == 100:
                m.monthly_limit = AsyncMock(return_value=10.0)
            else:
                m.monthly_limit = AsyncMock(return_value=None) # Infinite
            return m

        mock_config.guild.side_effect = guild_side_effect

        result = await service.resolve_billing_guild(user, channel)
        assert result == guild2 # Infinite one wins
