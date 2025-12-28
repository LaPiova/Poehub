from unittest.mock import AsyncMock, Mock

import pytest

from poehub.models import MessageData
from poehub.services.summarizer import SummarizerService


@pytest.fixture
def mock_chat_service():
    service = Mock()
    service.get_response = AsyncMock()
    return service

@pytest.fixture
def mock_context_service():
    service = Mock()
    return service

@pytest.fixture
def summarizer(mock_chat_service, mock_context_service):
    return SummarizerService(mock_chat_service, mock_context_service)

@pytest.mark.asyncio
async def test_summarize_messages_short(summarizer, mock_chat_service):
    """Test summarization for short content (single pass)."""
    messages = [
        MessageData(author="User", content="Hello", timestamp="2023-01-01")
    ]
    mock_chat_service.get_response.return_value = "Summary of hello"

    updates = []
    async for update in summarizer.summarize_messages(messages, user_id=123, model="gpt-4"):
        updates.append(update)

    assert len(updates) == 2
    assert updates[0].startswith("STATUS:")
    assert updates[1] == "RESULT: Summary of hello"

    mock_chat_service.get_response.assert_called_once()
    args, kwargs = mock_chat_service.get_response.call_args
    assert kwargs["model"] == "gpt-4"

@pytest.mark.asyncio
async def test_summarize_messages_long(summarizer, mock_chat_service):
    """Test summarization for long content (map-reduce)."""
    # Create long content > 12000 chars with newline to force split
    long_text = "a" * 7000 + "\n" + "b" * 7000
    messages = [
        MessageData(author="User", content=long_text, timestamp="2023-01-01")
    ]

    # Mock responses: 2 chunks + 1 final
    mock_chat_service.get_response.side_effect = [
        "Summary Chunk 1",
        "Summary Chunk 2",
        "Final Summary"
    ]

    updates = []
    async for update in summarizer.summarize_messages(messages, user_id=123):
        updates.append(update)

    # We expect status update for split
    status_updates = [u for u in updates if "STATUS" in u]
    assert any("Split into 2 chunks" in u for u in status_updates)
    assert updates[-1] == "RESULT: Final Summary"

    assert mock_chat_service.get_response.call_count == 3
