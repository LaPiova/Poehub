import asyncio
import time
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI

log = logging.getLogger("red.poehub.api")

class PoeClient:
    """
    Client for interacting with Poe API via OpenAI SDK
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.poe.com/v1"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self._cached_models: Optional[List[Dict[str, Any]]] = None
        self._models_cache_time: float = 0
        self._models_cache_duration: int = 3600  # 1 hour cache
        
    async def get_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch available models from Poe API with caching
        """
        current_time = time.time()
        if (not force_refresh and 
            self._cached_models is not None and 
            current_time - self._models_cache_time < self._models_cache_duration):
            return self._cached_models
            
        try:
            response = await self.client.models.list()
            
            models = []
            for model in response.data:
                models.append({
                    "id": model.id,
                    "object": model.object,
                    "created": getattr(model, 'created', None),
                    "owned_by": getattr(model, 'owned_by', 'poe')
                })
                
            self._cached_models = models
            self._models_cache_time = current_time
            log.info(f"Fetched {len(models)} models from Poe API")
            return models
            
        except Exception as e:
            log.error(f"Error fetching models: {e}", exc_info=True)
            if self._cached_models:
                log.info("Using expired cached models due to fetch error")
                return self._cached_models
            raise e

    async def stream_chat(
        self, 
        model: str, 
        messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completion responses
        """
        try:
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
                        
        except Exception as e:
            log.error(f"Error during stream: {e}", exc_info=True)
            raise e

    @staticmethod
    def format_image_message(text: str, image_urls: List[str]) -> List[Dict[str, Any]]:
        """
        Format message with images using OpenAI Vision format
        """
        content = []
        
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
        """Return the age of the model cache in seconds"""
        return int(time.time() - self._models_cache_time)


class DummyPoeClient:
    """Offline-friendly stand-in client for local debugging"""

    def __init__(self):
        self._models_cache_time = time.time()
        self._models: List[Dict[str, Any]] = [
            {"id": "dummy-claude-lite", "object": "model", "created": None, "owned_by": "poehub"},
            {"id": "dummy-gpt-lite", "object": "model", "created": None, "owned_by": "poehub"},
            {"id": "dummy-image", "object": "model", "created": None, "owned_by": "poehub"},
        ]

    async def get_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        if force_refresh:
            self._models_cache_time = time.time()
        await asyncio.sleep(0.05)
        return self._models

    async def stream_chat(self, model: str, messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        preview = self._extract_latest_user_prompt(messages)
        response = (
            f"[Dummy Response - {model}]\n"
            "This is a local stub so you can test PoeHub without a Poe API key.\n"
            f"Latest user message: {preview if preview else 'No user content detected.'}"
        )

        for chunk in self._chunk_response(response):
            await asyncio.sleep(0.1)
            yield chunk

    @staticmethod
    def format_image_message(text: str, image_urls: List[str]) -> List[Dict[str, Any]]:
        return PoeClient.format_image_message(text, image_urls)

    def get_cache_age(self) -> int:
        return int(time.time() - self._models_cache_time)

    def _extract_latest_user_prompt(self, messages: List[Dict[str, Any]]) -> str:
        for entry in reversed(messages):
            if entry.get("role") != "user":
                continue
            return self._flatten_content(entry.get("content"))
        return ""

    def _flatten_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return " ".join(filter(None, parts))
        return ""

    def _chunk_response(self, text: str, chunk_size: int = 350) -> List[str]:
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
