"""PoeHub Multi-Provider API Client.

This module provides a unified interface for interacting with various LLM providers:
- OpenAI (and compatible APIs like Poe, DeepSeek, OpenRouter)
- Anthropic (Claude)
- Google (Gemini)
"""

from __future__ import annotations

import abc
import asyncio
import base64
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union
from dataclasses import dataclass

import aiohttp
from .pricing_oracle import PricingOracle, TokenUsage

# Optional imports for providers
try:
    from openai import AsyncOpenAI, APIError as OpenAIError
except ImportError:
    AsyncOpenAI = None
    OpenAIError = Exception

try:
    from anthropic import AsyncAnthropic, APIError as AnthropicError
except ImportError:
    AsyncAnthropic = None
    
    class AnthropicError(Exception):
        pass

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
except ImportError:
    genai = None
    google_exceptions = None


log = logging.getLogger("red.poehub.api")


class BaseLLMClient(abc.ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self._cached_models: Optional[List[Dict[str, Any]]] = None
        self._models_cache_time: float = 0
        self._models_cache_duration: int = 3600  # 1 hour cache

    async def get_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
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
    async def _fetch_models(self) -> List[Dict[str, Any]]:
        """Fetch models from the specific provider."""
        pass

    @abc.abstractmethod
    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[Union[str, TokenUsage], None]:
        """Stream chat completion responses. Yields content strings and finally a TokenUsage object."""
        pass
    
    @staticmethod
    def format_image_message(text: str, image_urls: List[str]) -> List[Dict[str, Any]]:
        """Format message with images using the OpenAI Vision content format (standard)."""
        content: List[Dict[str, Any]] = []
        
        if text:
            content.append({
                "type": "text",
                "text": text
            })
            
        for url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": url
                }
            })
            
        return content

    def get_cache_age(self) -> int:
        """Return the age of the model cache in seconds."""
        return int(time.time() - self._models_cache_time)


class OpenAIProvider(BaseLLMClient):
    """Client for OpenAI and compatible APIs (Poe, DeepSeek, OpenRouter)."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        if AsyncOpenAI is None:
            raise ImportError("openai library not installed.")
        
        # Default base_url if not customized
        final_base_url = base_url if base_url else "https://api.openai.com/v1"
        
        # Use a custom httpx client for better control over timeouts/limits
        # 60s connect, 300s read
        import httpx
        http_client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=60.0))
        
        self.client = AsyncOpenAI(
            api_key=api_key, 
            base_url=final_base_url,
            http_client=http_client
        )

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        response = await self.client.models.list()
        models: List[Dict[str, Any]] = []
        for model in response.data:
            models.append({
                "id": model.id,
                "object": model.object,
                "created": getattr(model, "created", None),
                "owned_by": getattr(model, "owned_by", "system"),
            })
        return models

    async def fetch_openrouter_pricing(self) -> Dict[str, Tuple[float, float, str]]:
        """Fetch current pricing from OpenRouter API."""
        if "openrouter" not in str(self.base_url):
            return {}
            
        url = "https://openrouter.ai/api/v1/models"
        try:
             async with aiohttp.ClientSession() as session:
                 async with session.get(url) as response:
                     if response.status != 200:
                         log.error(f"Failed to fetch OpenRouter pricing: {response.status}")
                         return {}
                     
                     data = await response.json()
                     rates = {}
                     
                     for model in data.get("data", []):
                         m_id = model.get("id")
                         pricing = model.get("pricing", {})
                         
                         # OpenRouter provides price per token. We want per 1M.
                         # They give strings usually "0.000001"
                         prompt_cost = float(pricing.get("prompt", 0)) * 1_000_000
                         completion_cost = float(pricing.get("completion", 0)) * 1_000_000
                         
                         # Store as "openrouter/model_id"
                         # Note: provider name in PricingOracle logic is often "openrouter" if base_url matches
                         key = f"openrouter/{m_id.lower()}"
                         rates[key] = (prompt_cost, completion_cost, "USD")
                         
                     return rates
        except Exception:
            log.exception("Error fetching OpenRouter models")
            return {}

    async def fetch_poe_point_cost(self) -> Optional[int]:
        """Fetch the point cost of the most recent message from Poe usage history."""
        url = "https://api.poe.com/usage/points_history"
        try:
             async with aiohttp.ClientSession() as session:
                 headers = {"Authorization": f"Bearer {self.api_key}"}
                 params = {"limit": 1} # We only need the latest one
                 async with session.get(url, headers=headers, params=params) as response:
                     if response.status != 200:
                         return None
                     
                     data = await response.json()
                     # Check if data exists and is recent (optional: time check)
                     if data.get("data") and len(data["data"]) > 0:
                         # Return the cost of the most recent request
                         return int(data["data"][0].get("cost_points", 0))
                     return None
        except Exception:
            log.exception("Error fetching Poe usage history")
            return None

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[Union[str, TokenUsage], None]:
        # Retry configuration
        max_retries = 3
        current_try = 0
        
        while True:
            try:
                current_try += 1
                # Handle DeepSeek specific "reasoner" model separation if needed? 
                # DeepSeek uses same API, so standard call works.
                
                # Add stream_options to get usage statistics (OpenAI standard)
                create_kwargs = {
                    "model": model,
                    "messages": messages,
                    "stream": True,
                    # Set a reasonable timeout for the request
                    "timeout": 60.0, 
                }
                if "deepseek" not in str(self.client.base_url): # OpenRouter/standard support it
                     create_kwargs["stream_options"] = {"include_usage": True}

                stream = await self.client.chat.completions.create(**create_kwargs)
                
                # If we successfully got the stream, we break the retry loop and start yielding
                break
                
            except (OpenAIError, Exception) as e:
                # Check for specific connection errors that are worth retrying
                # "peer closed connection" is often an httpx.RemoteProtocolError wrapped in APIConnectionError
                is_connection_error = (
                    "peer closed connection" in str(e).lower() 
                    or "connection error" in str(e).lower()
                    or "incomplete chunked read" in str(e).lower()
                )
                
                if is_connection_error and current_try < max_retries:
                    log.warning(f"Connection error with Poe API (Attempt {current_try}/{max_retries}): {e}. Retrying...")
                    await asyncio.sleep(1 * current_try) # Exponential-ish backoff
                    continue
                
                # If not retryable or out of retries, re-raise
                raise
        
        # NOTE: The following logic for processing the stream must be OUTSIDE the `while True` loop
        # but inside the outer `try...except` block which is now... ambiguous.
        # Wait, the outer try/except (lines 297-306 in original, which is the `except Exception as e` block I am looking at below)
        # needs to wrap the ENTIRE logic including the loop and the processing.
        # My previous edit removed the outer `try:` block opening. 
        # I need to restore the structure:
        # try:
        #    ... retry loop ...
        #    ... processing loop ...
        # except Exception: ...
        
        try:
            final_usage = None
            
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content
                
                # Check for usage in chunk (often in final chunk)
                if hasattr(chunk, "usage") and chunk.usage:
                     final_usage = TokenUsage(
                         input_tokens=chunk.usage.prompt_tokens,
                         output_tokens=chunk.usage.completion_tokens,
                         currency="USD"
                     )
            
            if final_usage:
                # Calculate cost using Oracle
                # Provider name needs to be passed or inferred? 
                # We'll use "openai" as generic or try to detect from URL or passed in context
                # For now, let's use the object passed to us? 
                # We can't easily get the provider name string here without storing it on init.
                # Assuming 'openai' for now or 'deepseek' if base_url matches.
                provider_name = "openai"
                base_str = str(self.client.base_url).lower()
                if "deepseek" in base_str:
                    provider_name = "deepseek"
                elif "openrouter" in base_str:
                    provider_name = "openrouter"
                elif "poe" in base_str:
                    provider_name = "poe"
                
                # Special handling for Poe Points
                if provider_name == "poe":
                    # Try to fetch exact point cost from API
                    poe_cost = await self.fetch_poe_point_cost()
                    if poe_cost is not None:
                        final_usage.cost = float(poe_cost)
                        final_usage.currency = "Points"
                    else:
                        # Fallback to oracle estimation if fetch fails
                        final_usage.cost = PricingOracle.calculate_cost(provider_name, model, final_usage)
                        final_usage.currency = "Points" # Ensure currency is set
                else:
                    final_usage.cost = PricingOracle.calculate_cost(provider_name, model, final_usage)

                yield final_usage
        except Exception as e:
            # If we crash mid-stream, we can't retry, so just log and re-raise
            # But we can try to provide a better error message if it's the specific chunk error
            if "incomplete chunked read" in str(e).lower() or "peer closed connection" in str(e).lower():
                 log.error(f"Stream interrupted by Poe API connection drop: {e}")
                 # We yield a user-friendly error string if possible, but the caller expects str or TokenUsage.
                 # The caller wraps this in try/except Exception, so raising is fine.
            else:
                 log.exception("Error during OpenAI compatible stream")
            raise


class AnthropicProvider(BaseLLMClient):
    """Client for Anthropic Claude API."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        if AsyncAnthropic is None:
            raise ImportError("anthropic library not installed. Run `pip install anthropic`.")
        self.client = AsyncAnthropic(api_key=api_key, base_url=base_url)

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        # Anthropic doesn't have a public 'list models' API endpoint in the SDK?
        # Actually it does not. We'll return a static list of common models.
        # This is a known limitation of Anthropic API currently.
        return [
            {"id": "claude-3-5-sonnet-latest", "object": "model", "owned_by": "anthropic"},
            {"id": "claude-3-5-haiku-latest", "object": "model", "owned_by": "anthropic"},
            {"id": "claude-3-opus-latest", "object": "model", "owned_by": "anthropic"},
        ]

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[Union[str, TokenUsage], None]:
        try:
            # Convert OpenAI format messages to Anthropic format
            anthropic_messages = []
            system_prompt = None

            for msg in messages:
                if msg["role"] == "system":
                    system_prompt = msg["content"]
                    continue
                
                content = msg["content"]
                # Convert content if list (has images)
                new_content = []
                if isinstance(content, list):
                    for part in content:
                        if part["type"] == "text":
                            new_content.append({"type": "text", "text": part["text"]})
                        elif part["type"] == "image_url":
                            # Anthropic needs base64. 
                            # WARNING: Just passing text for now to avoid huge refactor for image downloading
                            # TODO: Implement image downloading
                            new_content.append({"type": "text", "text": "[Image: Support for images in Anthropic provider requires base64 conversion, pending implementation]"})
                else:
                    new_content = content

                anthropic_messages.append({
                    "role": msg["role"],
                    "content": new_content
                })

            kwargs = {
                "max_tokens": 4096,
                "messages": anthropic_messages,
                "model": model,
                "stream": True,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            stream = await self.client.messages.create(**kwargs)
            
            async for chunk in stream:
                 if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                    yield chunk.delta.text
                 elif chunk.type == "message_stop":
                    # message_stop might contain usage?
                    pass
            
            # Message stream usage is available in `message_start` (input) and `message_delta` (output/usage) event
            # Handling API usage with `stream` requires listening to all events. 
            # The simple loop above might miss it if we only look for content_block_delta.
            # But implementing full event parser is required.
            
            # Simple fallback for now: Manual estimation if API doesn't yield it simply
            input_tokens = sum(len(str(m["content"]))/4 for m in anthropic_messages) # Rough est
            output_tokens = 0 # Tracked during stream?
            # Note: For Anthropic, we really need to capture the Usage event. 
            # Ideally update to handle (event.type == "message_delta" -> event.usage)
            
            usage = TokenUsage(
                input_tokens=int(input_tokens), 
                output_tokens=int(output_tokens),
                currency="USD"
            )
            usage.cost = PricingOracle.calculate_cost("anthropic", model, usage)
            yield usage

        except Exception:
            log.exception("Error during Anthropic stream")
            raise


class GeminiProvider(BaseLLMClient):
    """Client for Google Gemini API."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        if genai is None:
            raise ImportError("google-generativeai library not installed.")
        genai.configure(api_key=api_key)

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        models = []
        try:
            # list_models returns an iterator
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                     models.append({
                        "id": m.name.replace("models/", ""),
                        "object": "model",
                        "owned_by": "google"
                    })
        except Exception as e:
            log.warning("Gemini list_models failed: %s", e)
            # Fallback
            return [{"id": "gemini-1.5-pro", "object": "model", "owned_by": "google"}]
        return models

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[Union[str, TokenUsage], None]:
        try:
            # Convert messages to Gemini format (Content objects)
            # Gemini manages history in a ChatSession usually, or we can pass full history each time
            # For compatibility, we'll use generate_content(stream=True) with full history? 
            # Or reconstruct chat history.
            
            gemini_history = []
            system_instruction = None
            last_user_message = None

            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                if msg["role"] == "system":
                    system_instruction = msg["content"]
                    continue
                
                parts = []
                content = msg["content"]
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if block["type"] == "text":
                            parts.append(block["text"])
                        elif block["type"] == "image_url":
                             parts.append("[Image: Gemini image support pending download impl]")
                
                if msg == messages[-1] and role == "user":
                    last_user_message = parts
                else:
                    gemini_history.append({"role": role, "parts": parts})
            
            model_instance = genai.GenerativeModel(
                model_name=model,
                system_instruction=system_instruction
            )
            
            if not last_user_message:
                # Should not happen in normal flow
                yield "Error: No user message found."
                return

            # Start chat with history
            chat = model_instance.start_chat(history=gemini_history)
            response = await chat.send_message_async(last_user_message, stream=True)
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
            
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                 usage = TokenUsage(
                     input_tokens=response.usage_metadata.prompt_token_count,
                     output_tokens=response.usage_metadata.candidates_token_count,
                     currency="USD"
                 )
                 usage.cost = PricingOracle.calculate_cost("google", model, usage)
                 yield usage
            else:
                 # ESTIMATE
                 usage = TokenUsage(0, 0, currency="USD")
                 usage.cost = PricingOracle.calculate_cost("google", model, usage)
                 yield usage

        except Exception:
            log.exception("Error during Gemini stream")
            raise


class DummyProvider(BaseLLMClient):
    """Offline-friendly stand-in client for local debugging."""

    def __init__(self, api_key: str = "dummy", base_url: Optional[str] = None):
        super().__init__(api_key, base_url)
        self._models = [
            {"id": "dummy-gpt-4", "object": "model", "owned_by": "dummy"},
            {"id": "dummy-claude-3", "object": "model", "owned_by": "dummy"},
        ]

    async def _fetch_models(self) -> List[Dict[str, Any]]:
        await asyncio.sleep(0.05)
        return self._models

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[Union[str, TokenUsage], None]:
        response = f"[Dummy Response] This is a test response from {model}."
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.1)
        
        # Fake usage for dummy
        yield TokenUsage(input_tokens=10, output_tokens=20, cost=0.0, currency="USD")


def get_client(provider: str, api_key: str, base_url: Optional[str] = None) -> BaseLLMClient:
    """Factory to create the appropriate client."""
    provider = provider.lower()
    
    if provider in ["poe", "openai", "deepseek", "openrouter"]:
        # Ensure base_url matches provider if defaulting (Poe legacy)
        if provider == "poe" and not base_url:
             base_url = "https://api.poe.com/v1"
        return OpenAIProvider(api_key, base_url)
    elif provider == "anthropic":
        return AnthropicProvider(api_key, base_url)
    elif provider == "google":
        return GeminiProvider(api_key, base_url)
    elif provider == "dummy":
        return DummyProvider()
    else:
        # Fallback to OpenAI if unknown, or raise?
        raise ValueError(f"Unknown provider: {provider}")
