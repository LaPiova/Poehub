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
