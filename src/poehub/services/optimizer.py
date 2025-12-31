"""Service to optimize API request parameters using a fast classifier model."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from ..api_client import get_client

if TYPE_CHECKING:
    from redbot.core import Config

log = logging.getLogger("red.poehub.services.optimizer")


class RequestOptimizer:
    """Analyzes user queries to determine optimal API parameters."""

    def __init__(self, config: Config):
        self.config = config
        self._client = None
        # Default classifier model
        self.classifier_model = "gpt-5.2-instant"

    async def _get_client(self):
        """Get or initialize the API client for the optimizer."""
        if self._client:
            return self._client

        # We use the same credentials as the main chat service
        # This assumes the user has configured a provider that supports the classifier model
        # or that we can fallback to available providers.
        # For simplicity, we'll try to get a client from the active provider configuration.
        # Ideally, this should have robust fallback logic.

        active_provider = await self.config.active_provider()
        provider_keys = await self.config.provider_keys()
        api_key = provider_keys.get(active_provider)

        if not api_key:
            return None

        try:
             # Use the active provider's client.
             # If the active provider is 'poe', it supports GPT-4o-Mini.
             # If it's 'openai', it supports it.
             # If it's 'anthropic' or 'google', we might need to change the model alias or skip optimization.
             self._client = get_client(active_provider, api_key)
             return self._client
        except Exception:
            return None

    async def optimize_request(self, query: str) -> dict[str, Any]:
        """
        Analyze the query and return parameter overrides.

        Returns a dictionary with keys like:
        - enable_web_search: bool
        - thinking_level: str ("low", "medium", "high")
        - quality: str ("standard", "high")
        """
        # Default fallback (no overrides, use system defaults)
        overrides = {}

        client = await self._get_client()
        if not client:
            return overrides

        system_prompt = (
            "You are an AI optimizer. Analyze the user's query and decide the optimal settings for:\n"
            "1. web_search (boolean): True if the query needs real-time info (news, weather, stock, recent events). False if static knowledge.\n"
            "2. thinking_level (string): 'high' for complex logic/math/reasoning. 'low' for simple chit-chat/facts.\n"
            "3. quality (string): 'high' for creative writing/important tasks. 'low' for simple chit-chat/facts. 'medium' for all other cases.\n\n"
            "Return valid JSON ONLY. No markdown formatting."
            "Example: {\"web_search\": true, \"thinking_level\": \"high\", \"quality\": \"high\"}"
        )

        try:
            # We use a non-streaming call for the classifier
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query[:500]} # Limit context
            ]

            # Simple workaround to get full text since our client is stream-based by default
            # We'll just iterate the stream.
            full_response = ""
            async for chunk in client.stream_chat(self.classifier_model, messages):
                 if isinstance(chunk, str):
                     full_response += chunk

            # Clean potential markdown
            cleaned_response = full_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            data = json.loads(cleaned_response.strip())

            # Map to our internal keys
            if "web_search" in data:
                overrides["web_search_override"] = data["web_search"]
            if "thinking_level" in data:
                 overrides["thinking_level"] = data["thinking_level"]
            if "quality" in data:
                 overrides["quality"] = data["quality"]

            log.info(f"Optimizer Result: {overrides}")
            return overrides

        except Exception as e:
            log.warning(f"Optimization failed: {e}")
            return overrides
