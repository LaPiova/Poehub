"""Pricing Oracle for PoeHub."""

# Import TokenUsage from models for Pydantic validation
from ...models import TokenUsage

# Re-export for backward compatibility
__all__ = ["TokenUsage", "PricingOracle"]


class PricingOracle:
    """Centralized pricing logic."""

    # Rate Card: (Input Price, Output Price) per 1M tokens in USD
    RATES = {
        "openai/gpt-4o": (2.50, 10.00),
        "openai/gpt-4o-mini": (0.15, 0.60),
        "openai/gpt-4": (30.00, 60.00),
        "openai/gpt-4-turbo": (10.00, 30.00),
        "openai/gpt-3.5-turbo": (0.50, 1.50),
        "anthropic/claude-3-5-sonnet-latest": (3.00, 15.00),
        "anthropic/claude-3-5-haiku-latest": (0.80, 4.00),  # Approx
        "anthropic/claude-3-opus-latest": (15.00, 75.00),
        "deepseek/deepseek-chat": (0.27, 1.10),  # DeepSeek V3
        "deepseek/deepseek-reasoner": (0.55, 2.19),  # DeepSeek R1
        "google/gemini-1.5-pro": (3.50, 10.50),  # Approx
        "google/gemini-1.5-flash": (0.075, 0.30),
        "dummy/dummy-gpt-4": (10.0, 30.0),  # Fake rates for testing
        # Poe Points (Approximate per 1M tokens equivalent is hard, so we store "Per Message" cost in Input slot for logic?)
        # Actually, PricingOracle return is (In, Out, Currency).
        # For Points, we usually bill "Per Request" or "Per Token".
        # Poe API models often charge per message + per token.
        # But our usage tracking in api_client attempts to get the REAL cost.
        # These are ESTIMATES for when the API header is missing.
        # Based on Dec 2024 checks:
        "poe/claude-3.5-sonnet": (343.0, 0.0),  # Points per message (Approx)
        "poe/gpt-4o": (289.0, 0.0),
        "poe/gemini-1.5-pro": (175.0, 0.0),
        "poe/llama-3.1-405b": (1800.0, 0.0),
        "poe/o1-mini": (1800.0, 0.0),
        "poe/grok-beta": (570.0, 0.0),
        "poe/assistant": (20.0, 0.0),
        "poe/web-search": (15.0, 0.0),
    }

    _DYNAMIC_RATES: dict[str, tuple[float, float, str]] = {}

    @classmethod
    def load_dynamic_rates(cls, rates: dict[str, tuple[float, float, str]]) -> None:
        """Load dynamic rates from config."""
        cls._DYNAMIC_RATES.update(rates)

    @classmethod
    def update_rate(
        cls,
        provider: str,
        model: str,
        in_price: float,
        out_price: float,
        currency: str = "USD",
    ) -> None:
        """Update a specific rate."""
        key = f"{provider.lower()}/{model.lower()}"
        cls._DYNAMIC_RATES[key] = (in_price, out_price, currency)

    @classmethod
    def get_price(cls, provider: str, model: str) -> tuple[float, float, str]:
        """Get pricing for a model. Returns (input_per_1m, output_per_1m, currency)."""
        key = f"{provider.lower()}/{model.lower()}"

        # Check dynamic/overrides first
        if key in cls._DYNAMIC_RATES:
            return cls._DYNAMIC_RATES[key]

        # Try exact match
        if key in cls.RATES:
            rates = cls.RATES[key]
            # Points Check
            if provider == "poe":
                return (*rates, "Points")
            return (*rates, "USD")

        # Try partial match (e.g. model name mapping)
        for k, v in cls.RATES.items():
            if k.split("/")[1] == model.lower():
                if provider == "poe":
                    return (*v, "Points")
                return (*v, "USD")

        # Defaults
        if provider == "poe":
            return (200.0, 0.0, "Points")  # Better default: 200 points per msg

        return (0.0, 0.0, "USD")

    @classmethod
    def calculate_cost(cls, provider: str, model: str, usage: TokenUsage) -> float:
        """Calculate cost for usage."""
        if usage.currency == "Points":
            return usage.cost  # Already set by provider logic if possible

        in_price, out_price, currency = cls.get_price(provider, model)

        # Override currency if oracle says so
        if currency == "Points":
            usage.currency = "Points"

        cost = (usage.input_tokens / 1_000_000 * in_price) + (
            usage.output_tokens / 1_000_000 * out_price
        )
        return round(cost, 6)
