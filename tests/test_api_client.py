import sys
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Need to patch imports that might be missing
sys.modules["openai"] = MagicMock()
sys.modules["anthropic"] = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()

# Re-import after patching
from poehub.api_client import (
    AnthropicProvider,
    BaseLLMClient,
    DummyProvider,
    GeminiProvider,
    OpenAIProvider,
    TokenUsage,
    get_client,
)


@pytest.fixture
def mock_httpx():
    with patch("httpx.AsyncClient") as mock_client:
        instance = AsyncMock()
        mock_client.return_value = instance
        yield instance

class TestBaseLLMClient:
    class ConcreteClient(BaseLLMClient):
        async def _fetch_models(self):
            return [{"id": "model-1"}]
        async def stream_chat(self, model, messages):
            yield "chunk"

    @pytest.mark.asyncio
    async def test_get_models_caching(self):
        client = self.ConcreteClient("key")

        # First fetch
        client._fetch_models = AsyncMock(return_value=[{"id": "mod1"}])
        models = await client.get_models()
        assert len(models) == 1
        assert client._fetch_models.call_count == 1

        # Second fetch (cached)
        models2 = await client.get_models()
        assert models2 == models
        assert client._fetch_models.call_count == 1

        # Force refresh
        await client.get_models(force_refresh=True)
        assert client._fetch_models.call_count == 2

        # Cache expiration
        client._models_cache_time = time.time() - 4000
        await client.get_models()
        assert client._fetch_models.call_count == 3

    @pytest.mark.asyncio
    async def test_get_models_error_fallback(self):
        client = self.ConcreteClient("key")
        # Setup cache
        client._cached_models = [{"id": "cached"}]
        client._models_cache_time = 0 # Expired

        client._fetch_models = AsyncMock(side_effect=Exception("API Error"))

        models = await client.get_models()
        # Should return cached despite expiry because of error
        assert models[0]["id"] == "cached"

class TestOpenAIProvider:
    @pytest.fixture
    def provider(self, mock_httpx):
        # We need to mock AsyncOpenAI being present
        with patch("poehub.api_client.AsyncOpenAI"):
            client = OpenAIProvider("key")
            client.client = AsyncMock() # The AsyncOpenAI instance
            return client

    @pytest.mark.asyncio
    async def test_fetch_models(self, provider):
        mock_resp = Mock()
        mock_model = Mock()
        mock_model.id = "gpt-4"
        mock_model.object = "model"
        mock_model.created = 123
        mock_model.owned_by = "openai"

        mock_resp.data = [mock_model]
        provider.client.models.list = AsyncMock(return_value=mock_resp)

        models = await provider._fetch_models()
        assert len(models) == 1
        assert models[0]["id"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_stream_chat(self, provider):
        # Mock stream
        chunk = Mock()
        chunk.choices = [Mock(delta=Mock(content="Hello"))]
        chunk.usage = None

        chunk2 = Mock()
        chunk2.choices = []
        chunk2.usage = Mock(prompt_tokens=5, completion_tokens=5)

        async def stream_gen(*args, **kwargs):
             yield chunk
             yield chunk2

        # _create_stream logic calls client.chat.completions.create
        provider.client.chat.completions.create.side_effect = stream_gen

        messages = [{"role": "user", "content": "hi"}]
        chunks = []
        usage = None

        async for item in provider.stream_chat("gpt-4", messages):
            if isinstance(item, str):
                chunks.append(item)
            else:
                usage = item

        assert chunks == ["Hello"]
        assert usage.currency == "USD"
        assert usage.input_tokens == 5

    @pytest.mark.asyncio
    async def test_fetch_openrouter_pricing(self, provider, mock_httpx):
        provider.base_url = "https://openrouter.ai/api/v1"

        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "foo",
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"}
                }
            ]
        }
        provider.http_client.get.return_value = mock_resp

        rates = await provider.fetch_openrouter_pricing()
        assert "openrouter/foo" in rates
        assert rates["openrouter/foo"][0] == 1.0

    @pytest.mark.asyncio
    async def test_fetch_poe_point_cost(self, provider, mock_httpx):
        mock_resp = Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": [{"cost_points": 50}]}
        provider.http_client.get.return_value = mock_resp

        cost = await provider.fetch_poe_point_cost()
        assert cost == 50

    @pytest.mark.asyncio
    async def test_provider_specific_usage(self, provider, mock_httpx):
        # Test usage calculation for different providers based on base_url

        # Helper to run stream and get usage
        async def run_stream(base_url, model):
            provider.client.base_url = base_url
            # provider.base_url is cached? No self.base_url
            provider.base_url = base_url

            chunk = Mock()
            chunk.choices = []
            chunk.usage = Mock(prompt_tokens=10, completion_tokens=10)

            async def gen(*args, **kwargs):
                yield chunk

            # We must set client.chat.completions.create again
            provider.client.chat.completions.create.side_effect = gen
            # provider.client.base_url should be updated ideally but api_client uses self.client.base_url ?
            provider.client.base_url = base_url

            usage = None
            async for item in provider.stream_chat(model, []):
                if isinstance(item, TokenUsage):
                    usage = item
            return usage

        # DeepSeek
        u_ds = await run_stream("https://api.deepseek.com", "deepseek-coder")
        assert u_ds.currency == "USD"

        # OpenRouter
        u_or = await run_stream("https://openrouter.ai/api/v1", "gpt-4")
        assert u_or.currency == "USD"

        # Poe
        # Mock fetch_poe_point_cost behavior
        provider.fetch_poe_point_cost = AsyncMock(return_value=100)
        u_poe = await run_stream("https://api.poe.com/v1", "gpt-4")
        assert u_poe.currency == "Points"
        assert u_poe.cost == 100

        # Poe fallback
        provider.fetch_poe_point_cost = AsyncMock(return_value=None)
        u_poe_fail = await run_stream("https://api.poe.com/v1", "gpt-4")
        assert u_poe_fail.currency == "Points"

    @pytest.mark.asyncio
    async def test_fetch_exceptions(self, provider):
        # OpenRouter exception
        provider.http_client.get.side_effect = Exception("Net Error")
        provider.base_url = "https://openrouter.ai/api/v1"
        rates = await provider.fetch_openrouter_pricing()
        assert rates == {}

        # Poe exception
        provider.http_client.get.side_effect = Exception("Net Error")
        cost = await provider.fetch_poe_point_cost()
        assert cost is None

class TestAnthropicProvider:
    @pytest.fixture
    def provider(self):
        with patch("poehub.api_client.AsyncAnthropic"):
            prov = AnthropicProvider("key")
            prov.client = AsyncMock()
            return prov

    @pytest.mark.asyncio
    async def test_stream_chat(self, provider):
        chunk = Mock()
        chunk.type = "content_block_delta"
        chunk.delta.type = "text_delta"
        chunk.delta.text = "Hello"

        async def stream_gen(**kwargs):
            yield chunk

        provider.client.messages.create.side_effect = stream_gen

        messages = [{"role": "user", "content": "hi"}]
        chunks = []
        async for item in provider.stream_chat("claude-3", messages):
            if isinstance(item, str):
                 chunks.append(item)

        assert chunks == ["Hello"]

class TestGeminiProvider:
    @pytest.fixture
    def provider(self):
        with patch("poehub.api_client.genai", new=MagicMock()):
            return GeminiProvider("key")

    @pytest.mark.asyncio
    async def test_stream_chat(self, provider):
        with patch("poehub.api_client.genai") as mock_genai:
            mock_model = AsyncMock()
            mock_genai.GenerativeModel.return_value = mock_model

            mock_resp = AsyncMock()
            mock_chunk = Mock()
            mock_chunk.text = "Hello"
            mock_resp.__aiter__.return_value = [mock_chunk]

            mock_model.generate_content_async.return_value = mock_resp

            messages = [{"role": "user", "content": "hi"}]
            chunks = []
            async for item in provider.stream_chat("gemini-pro", messages):
                if isinstance(item, str):
                    chunks.append(item)

            assert chunks == ["Hello"]

def test_get_client():
    with patch("poehub.api_client.OpenAIProvider") as m1:
        get_client("openai", "k")
        m1.assert_called()
    with patch("poehub.api_client.AnthropicProvider") as m2:
        get_client("anthropic", "k")
        m2.assert_called()
    with patch("poehub.api_client.GeminiProvider") as m3:
        get_client("google", "k")
        m3.assert_called()
    with pytest.raises(ValueError):
        get_client("unknown", "k")

@pytest.mark.asyncio
async def test_dummy_provider():
    p = DummyProvider()
    res = await p.get_models()
    assert len(res) > 0

    chunks = []
    async for item in p.stream_chat("dummy", []):
         chunks.append(item)
    assert len(chunks) > 0
