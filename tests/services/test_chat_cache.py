"""Test for ChatService._clear_conversation_memory method."""
from unittest.mock import AsyncMock

import pytest

from poehub.core.memory import ThreadSafeMemory
from poehub.services.chat import ChatService


@pytest.mark.asyncio
async def test_clear_conversation_memory():
    """Test that _clear_conversation_memory calls ThreadSafeMemory.clear()."""
    # Create a minimal ChatService instance
    service = ChatService(
        bot=None,
        config=None,
        billing_service=None,
        context_service=None,
        conversation_manager=None
    )

    # Mock the _get_memory method to return a mock ThreadSafeMemory
    mock_memory = AsyncMock(spec=ThreadSafeMemory)
    service._get_memory = AsyncMock(return_value=mock_memory)

    user_id = 123
    conv_id = "test_conv"

    # Call the method
    unique_key = f"user:{user_id}:{conv_id}"

    # Pre-populate memory
    service._memories[unique_key] = mock_memory

    # Call the method
    await service._clear_conversation_memory(unique_key)

    # Verify memory clear called
    mock_memory.clear.assert_awaited_once()

    # Verify _get_memory was NOT called (it avoids it for optimization)
    service._get_memory.assert_not_called()


@pytest.mark.asyncio
async def test_clear_conversation_memory_does_nothing_if_not_exists():
    """Test that _clear_conversation_memory does nothing if memory doesn't exist."""
    service = ChatService(
        bot=None,
        config=None,
        billing_service=None,
        context_service=None,
        conversation_manager=None
    )

    user_id = 456
    conv_id = "conv2"

    # Call the method - should NOT create memory
    unique_key = f"user:{user_id}:{conv_id}"
    await service._clear_conversation_memory(unique_key)

    # Verify memory was NOT created
    assert unique_key not in service._memories


