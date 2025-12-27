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

import aiohttp

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
    ) -> AsyncGenerator[str, None]:
        """Stream chat completion responses."""
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
        self.client = AsyncOpenAI(api_key=api_key, base_url=final_base_url)

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

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        try:
            # Handle DeepSeek specific "reasoner" model separation if needed? 
            # DeepSeek uses same API, so standard call works.
            
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content
        except Exception:
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
    ) -> AsyncGenerator[str, None]:
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
    ) -> AsyncGenerator[str, None]:
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
    ) -> AsyncGenerator[str, None]:
        response = f"[Dummy Response] This is a test response from {model}."
        for word in response.split():
            yield word + " "
            await asyncio.sleep(0.1)


def get_client(provider: str, api_key: str, base_url: Optional[str] = None) -> BaseLLMClient:
    """Factory to create the appropriate client."""
    provider = provider.lower()
    
    if provider in ["poe", "openai", "deepseek", "openrouter"]:
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
