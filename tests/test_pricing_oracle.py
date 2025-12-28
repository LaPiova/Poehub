from poehub.pricing_oracle import PricingOracle, TokenUsage


class TestPricingOracle:
    def test_get_price_known_model(self):
        in_price, out_price, currency = PricingOracle.get_price("openai", "gpt-4o")
        assert in_price == 2.50
        assert out_price == 10.00
        assert currency == "USD"

    def test_get_price_poe_model(self):
        in_price, out_price, currency = PricingOracle.get_price("poe", "gpt-4o")
        # Should be Points, and should default to something if not in RATES or use RATES if mapped
        # In code: "poe/gpt-4o": (289.0, 0.0) -> Points per message
        assert currency == "Points"
        assert in_price == 289.0

    def test_get_price_default_poe(self):
        in_price, out_price, currency = PricingOracle.get_price(
            "poe", "unknown-model-123"
        )
        assert currency == "Points"
        assert in_price == 200.0  # Default

    def test_get_price_default_usd(self):
        in_price, out_price, currency = PricingOracle.get_price(
            "openai", "unknown-model"
        )
        assert currency == "USD"
        assert in_price == 0.0

    def test_calculate_cost_usd(self):
        usage = TokenUsage(
            input_tokens=1_000_000, output_tokens=1_000_000, currency="USD"
        )
        # openai/gpt-4o: 2.50 in, 10.00 out
        cost = PricingOracle.calculate_cost("openai", "gpt-4o", usage)
        assert cost == 12.50

    def test_calculate_cost_points_precalculated(self):
        # usage.cost is already set
        usage = TokenUsage(
            input_tokens=10, output_tokens=10, cost=500.0, currency="Points"
        )
        cost = PricingOracle.calculate_cost("poe", "any", usage)
        assert cost == 500.0

    def test_calculate_cost_points_fallback(self):
        # usage.cost not set, calculate from Rate Card
        usage = TokenUsage(
            input_tokens=100, output_tokens=100, currency="USD"
        )  # passed as USD usually
        # poe/gpt-4o: 289 per msg (input slot)
        # Wait, calculate_cost logic:
        # (input / 1M * in_price) + ...
        # If rate is 289.0, then for 1M input tokens it is 289? No, code says:
        # "poe/gpt-4o": (289.0, 0.0)
        # But comment says "Points per message (Approx)".
        # The PricingOracle implementation treats it as "Per 1M tokens".
        # If the rate card implies "Per Message", the code might be semantically mismatched
        # OR the code expects the rate to be scaled to 1M tokens.
        # Let's check `get_price`: return (*rates, "Points")
        # `calculate_cost`: (usage.input_tokens / 1_000_000 * in_price)
        # So 289.0 in the dict means 289 points per 1 MILLION tokens?? That's super cheap.
        # A message costs ~300 points. 1 message is not 1M tokens.
        # This hints at a bug or misunderstanding in the existing code, but I am writing tests for EXISTING code.
        # So I expect the calculation to follow the code logic.

        # 289.0 * (100 / 1,000,000) = 0.0289
        cost = PricingOracle.calculate_cost("poe", "gpt-4o", usage)
        assert (
            cost == 0.0289
        )  # Testing existing logic, even if it seems odd for points.

    def test_dynamic_rates(self):
        PricingOracle.update_rate("custom", "model-x", 5.0, 10.0, "USD")
        in_price, out_price, currency = PricingOracle.get_price("custom", "model-x")
        assert in_price == 5.0
        assert out_price == 10.0
