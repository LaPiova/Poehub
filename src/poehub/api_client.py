from __future__ import annotations

import abc
import logging
import time
from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .services.billing.oracle import PricingOracle, TokenUsage
from .utils.logging import RequestContext

# Check for provider libraries, but we might rely on HttpX for some
try:
    from openai import APIError as OpenAIError
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None
    OpenAIError = Exception

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

log = logging.getLogger("red.poehub.api")

# --- Pydantic Data Models ---


class PoeMessageRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"
    MODEL = "model"


class PoeMessagePart(BaseModel):
    type: str  # text or image_url
    text: str | None = None
    image_url: dict[str, str] | None = None

    model_config = ConfigDict(extra="ignore")


class PoeMessage(BaseModel):
    role: PoeMessageRole
    content: str | list[PoeMessagePart]

    model_config = ConfigDict(extra="ignore")


class PoeChatRequest(BaseModel):
    model: str
    messages: list[PoeMessage]
    stream: bool = True

    model_config = ConfigDict(extra="ignore")


class BaseLLMClient(abc.ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self._cached_models: list[dict[str, Any]] | None = None
        self._models_cache_time: float = 0
        self._models_cache_duration: int = 3600

    async def get_models(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Return available models from the provider with caching."""
        current_time = time.time()
        if (
            not force_refresh
            and self._cached_models is not None
            and current_time - self._models_cache_time < self._models_cache_duration
        ):
            return self._cached_models

        try:
            models = await self._fetch_models()
            self._cached_models = models
            self._models_cache_time = current_time
            log.info("Fetched %s models from provider", len(models))
            return models
        except Exception:
            log.exception("Error fetching models")
            if self._cached_models:
                log.info("Using expired cached models due to fetch error")
                return self._cached_models
            return []

    @abc.abstractmethod
    async def _fetch_models(self) -> list[dict[str, Any]]:
        pass

    @abc.abstractmethod
    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[str | TokenUsage, None]:
        pass

    def get_cache_age(self) -> int:
        return int(time.time() - self._models_cache_time)

    def format_image_message(self, text: str, image_urls: list[str]) -> list[dict[str, Any]]:
        """Format a message with text and images for multimodal input.

        Args:
            text: The text content of the message
            image_urls: List of image URLs to include

        Returns:
            A list of content parts compatible with OpenAI's multimodal format
        """
        content = []

        # Add text part if present
        if text:
            content.append({"type": "text", "text": text})

        # Add image parts
        for url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": url}
            })

        return content


class OpenAIProvider(BaseLLMClient):
    """Client for OpenAI and compatible APIs (Poe, DeepSeek, OpenRouter)."""

    def __init__(self, api_key: str, base_url: str | None = None):
        super().__init__(api_key, base_url)
        if AsyncOpenAI is None:
            raise ImportError("openai library not installed.")

        final_base_url = base_url if base_url else "https://api.openai.com/v1"

        # Robust HTTP Client with limitations
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )

        self.client = AsyncOpenAI(
            api_key=api_key, base_url=final_base_url, http_client=self.http_client
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=before_sleep_log(log, logging.WARNING),
    )
    async def _fetch_models(self) -> list[dict[str, Any]]:
        response = await self.client.models.list()
        models: list[dict[str, Any]] = []
        for model in response.data:
            models.append(
                {
                    "id": model.id,
                    "object": model.object,
                    "created": getattr(model, "created", None),
                    "owned_by": getattr(model, "owned_by", "system"),
                }
            )
        return models

    async def fetch_openrouter_pricing(self) -> dict[str, tuple[float, float, str]]:
        if "openrouter" not in str(self.base_url):
            return {}

        # Use existing http client for efficiency
        url = "https://openrouter.ai/api/v1/models"
        try:
            resp = await self.http_client.get(url)
            if resp.status_code != 200:
                return {}

            data = resp.json()
            rates = {}
            for model in data.get("data", []):
                pricing = model.get("pricing", {})
                prompt_cost = float(pricing.get("prompt", 0)) * 1_000_000
                completion_cost = float(pricing.get("completion", 0)) * 1_000_000
                key = f"openrouter/{model.get('id').lower()}"
                rates[key] = (prompt_cost, completion_cost, "USD")
            return rates
        except Exception:
            log.exception("Error fetching OpenRouter models")
            return {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
    )
    async def fetch_poe_point_cost(self) -> int | None:
        url = "https://api.poe.com/usage/points_history"
        try:
            # Need separate headers since we might not have them on self.http_client default
            headers = {"Authorization": f"Bearer {self.api_key}"}
            resp = await self.http_client.get(url, headers=headers, params={"limit": 1})
            if resp.status_code != 200:
                return None

            data = resp.json()
            if data.get("data") and len(data["data"]) > 0:
                return int(data["data"][0].get("cost_points", 0))
            return None
        except Exception:
            log.exception("Error fetching Poe usage")
            return None

    # Tenacity retry for the stream connection itself
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((OpenAIError, httpx.RequestError)),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,  # We want the caller to handle the final failure
    )
    async def _create_stream(self, **kwargs):
        """Internal method to create stream with retry logic."""
        return await self.client.chat.completions.create(**kwargs)

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[str | TokenUsage, None]:
        ctx = RequestContext(model=model, message_count=len(messages))
        ctx.info("Starting chat request")

        create_kwargs = {
            "model": model,
            "messages": messages,
            "stream": True,
            "timeout": 90.0,
        }

        # Check support for stream_options
        if "deepseek" not in str(self.client.base_url):
            create_kwargs["stream_options"] = {"include_usage": True}

        try:
            stream = await self._create_stream(**create_kwargs)

            final_usage = None
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content

                if hasattr(chunk, "usage") and chunk.usage:
                    final_usage = TokenUsage(
                        input_tokens=chunk.usage.prompt_tokens,
                        output_tokens=chunk.usage.completion_tokens,
                        currency="USD",
                    )

            # Post-stream cost calculation
            if final_usage:
                provider_name = "openai"
                base_str = str(self.client.base_url).lower()
                if "deepseek" in base_str:
                    provider_name = "deepseek"
                elif "openrouter" in base_str:
                    provider_name = "openrouter"
                elif "poe" in base_str:
                    provider_name = "poe"

                if provider_name == "poe":
                    poe_cost = await self.fetch_poe_point_cost()
                    if poe_cost is not None:
                        final_usage.cost = float(poe_cost)
                        final_usage.currency = "Points"
                    else:
                        final_usage.cost = PricingOracle.calculate_cost(
                            provider_name, model, final_usage
                        )
                        final_usage.currency = "Points"
                else:
                    final_usage.cost = PricingOracle.calculate_cost(
                        provider_name, model, final_usage
                    )

                ctx.info(
                    "Request completed",
                    cost=final_usage.cost,
                    currency=final_usage.currency,
                )
                yield final_usage

        except Exception as e:
            log.error(f"Stream error: {e}")
            raise


class AnthropicProvider(BaseLLMClient):
    """Client for Anthropic Claude API."""

    def __init__(self, api_key: str, base_url: str | None = None):
        super().__init__(api_key, base_url)
        if AsyncAnthropic is None:
            raise ImportError("anthropic library not installed.")
        self.client = AsyncAnthropic(api_key=api_key, base_url=base_url)

    async def _fetch_models(self) -> list[dict[str, Any]]:
        return [
            {
                "id": "claude-3-5-sonnet-latest",
                "object": "model",
                "owned_by": "anthropic",
            },
            {
                "id": "claude-3-5-haiku-latest",
                "object": "model",
                "owned_by": "anthropic",
            },
            {"id": "claude-3-opus-latest", "object": "model", "owned_by": "anthropic"},
        ]

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[str | TokenUsage, None]:
        anthropic_messages = []
        system_prompt = None

        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
                continue

            content = msg["content"]
            # Simplified content handling
            new_content = content
            if isinstance(content, list):
                # Basic handler for multimodal lists
                new_content = []
                for part in content:
                    if part.get("type") == "text":
                        new_content.append({"type": "text", "text": part["text"]})
                    # Add image handling if needed

            anthropic_messages.append({"role": msg["role"], "content": new_content})

        kwargs = {
            "max_tokens": 4096,
            "messages": anthropic_messages,
            "model": model,
            "stream": True,
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        try:
            stream = await self.client.messages.create(**kwargs)
            async for chunk in stream:
                if (
                    chunk.type == "content_block_delta"
                    and chunk.delta.type == "text_delta"
                ):
                    yield chunk.delta.text

            # Placeholder for usage
            usage = TokenUsage(input_tokens=0, output_tokens=0, currency="USD")
            usage.cost = PricingOracle.calculate_cost("anthropic", model, usage)
            yield usage
        except Exception:
            log.exception("Error during Anthropic stream")
            raise


class GeminiProvider(BaseLLMClient):
    """Client for Google Gemini API."""

    def __init__(self, api_key: str, base_url: str | None = None):
        super().__init__(api_key, base_url)
        if genai is None:
            raise ImportError("google-generativeai library not installed.")
        genai.configure(api_key=api_key)

    async def _fetch_models(self) -> list[dict[str, Any]]:
        try:
            return [
                {
                    "id": m.name.replace("models/", ""),
                    "object": "model",
                    "owned_by": "google",
                }
                for m in genai.list_models()
                if "generateContent" in m.supported_generation_methods
            ]
        except Exception:
            return [{"id": "gemini-3-pro", "object": "model", "owned_by": "google"}]

    async def stream_chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
    ) -> AsyncGenerator[str | TokenUsage, None]:
        # Minimal implementation for brevity
        try:
            # ... Logic similar to before ...
            model_instance = genai.GenerativeModel(model)
            response = await model_instance.generate_content_async(
                [m["content"] for m in messages if m["role"] == "user"][
                    -1
                ],  # Simplified
                stream=True,
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text

            usage = TokenUsage(input_tokens=0, output_tokens=0, currency="USD")
            yield usage
        except Exception as e:
            log.error(f"Gemini error: {e}")
            raise


class DummyProvider(BaseLLMClient):
    def __init__(self, api_key: str = "dummy", base_url: None = None):
        super().__init__(api_key, base_url)

    async def _fetch_models(self):
        return [{"id": "dummy-model", "object": "model", "owned_by": "dummy"}]

    async def stream_chat(self, model, messages):
        yield "[Dummy Response] This is a test response."
        yield TokenUsage(input_tokens=10, output_tokens=10, cost=0.0, currency="USD")


def get_client(
    provider: str, api_key: str, base_url: str | None = None
) -> BaseLLMClient:
    provider = provider.lower()
    if provider in ["poe", "openai", "deepseek", "openrouter"]:
        if provider == "poe" and not base_url:
            base_url = "https://api.poe.com/v1"
        return OpenAIProvider(api_key, base_url)
    elif provider == "anthropic":
        return AnthropicProvider(api_key, base_url)
    elif provider == "google":
        return GeminiProvider(api_key, base_url)
    elif provider == "dummy":
        return DummyProvider()
    raise ValueError(f"Unknown provider: {provider}")
