
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from poehub.services.optimizer import RequestOptimizer


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.active_provider = AsyncMock(return_value="poe")
    config.provider_keys = AsyncMock(return_value={"poe": "key"})
    return config

@pytest.fixture
def optimizer(mock_config):
    return RequestOptimizer(mock_config)

@pytest.mark.asyncio
async def test_optimize_request_success(optimizer):
    mock_client = AsyncMock()

    # Mocking stream_chat to yield JSON response
    async def mock_stream(*args, **kwargs):
        yield '{"web_search": false, "thinking_level": "low", "quality": "standard"}'

    mock_client.stream_chat = mock_stream

    with patch("poehub.services.optimizer.get_client", return_value=mock_client):
        result = await optimizer.optimize_request("What is 2+2?")

        assert result["web_search_override"] is False
        assert result["thinking_level"] == "low"
        assert result["quality"] == "standard"

@pytest.mark.asyncio
async def test_optimize_request_complex(optimizer):
    mock_client = AsyncMock()

    # Mocking stream_chat to yield JSON response with markdown code blocks
    async def mock_stream(*args, **kwargs):
        yield '```json\n{"web_search": true, "thinking_level": "high", "quality": "high"}\n```'

    mock_client.stream_chat = mock_stream

    with patch("poehub.services.optimizer.get_client", return_value=mock_client):
        result = await optimizer.optimize_request("What is the stock price of Apple?")

        assert result["web_search_override"] is True
        assert result["thinking_level"] == "high"
        assert result["quality"] == "high"

@pytest.mark.asyncio
async def test_optimize_request_failure(optimizer):
    mock_client = AsyncMock()

    # Mocking stream_chat to yield invalid JSON
    async def mock_stream(*args, **kwargs):
        yield 'Not a JSON'

    mock_client.stream_chat = mock_stream

    with patch("poehub.services.optimizer.get_client", return_value=mock_client):
        result = await optimizer.optimize_request("Bad response")

        assert result == {}
