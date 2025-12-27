
import aiohttp
import logging
from typing import Dict, Tuple, Optional, Any

log = logging.getLogger("red.poehub.pricing_crawler")

LITELLM_PRICES_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

class PricingCrawler:
    """
    Fetches model pricing from community-maintained sources (LiteLLM)
    to ensure the bot has up-to-date rates for OpenAI, Anthropic, Gemini, etc.
    """
    
    @staticmethod
    async def fetch_rates() -> Dict[str, Tuple[float, float, str]]:
        """
        Fetches rates and returns a dictionary mapping:
        provider/model -> (input_per_1M, output_per_1M, currency)
        """
        rates = {}
        log.info("Fetching pricing data from LiteLLM...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(LITELLM_PRICES_URL) as response:
                    if response.status != 200:
                        log.error(f"Failed to fetch LiteLLM prices: {response.status}")
                        return {}
                    
                    data = await response.json(content_type=None) # Handle text/plain if needed, though raw usually is proper json
                    
                    # Data structure is key=model_name, value={...}
                    # We need to map model names to our provider naming convention if possible,
                    # or just store them as is and let Oracle match "openai/gpt-4" etc.
                    
                    for model_key, details in data.items():
                        if not isinstance(details, dict):
                            continue
                            
                        # Extract costs (usually per token)
                        # LiteLLM uses 'input_cost_per_token' and 'output_cost_per_token'
                        in_cost = details.get("input_cost_per_token")
                        out_cost = details.get("output_cost_per_token")
                        
                        if in_cost is None or out_cost is None:
                            continue
                            
                        # Convert to float and per 1M
                        try:
                            in_per_1m = float(in_cost) * 1_000_000
                            out_per_1m = float(out_cost) * 1_000_000
                        except (ValueError, TypeError):
                            continue
                            
                        # Determine provider/key
                        # LiteLLM keys are often just "gpt-4", "claude-3-opus", etc.
                        # Sometimes "openai/gpt-4".
                        
                        # We will store multiple keys to be safe.
                        # 1. Exact match (e.g. "gpt-4")
                        rates[model_key] = (in_per_1m, out_per_1m, "USD")
                        
                        # 2. Provider prefixed if known and not already prefixed
                        litellm_provider = details.get("litellm_provider")
                        if litellm_provider and "/" not in model_key:
                            prefixed = f"{litellm_provider}/{model_key}"
                            rates[prefixed] = (in_per_1m, out_per_1m, "USD")
                            
        except Exception as e:
            log.exception(f"Error crawling pricing data: {e}")
            return {}
            
        log.info(f"Fetched {len(rates)} pricing entries.")
        return rates
