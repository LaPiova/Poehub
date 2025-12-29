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
    await service._clear_conversation_memory(user_id, conv_id)

    # Verify _get_memory was called with correct args
    service._get_memory.assert_awaited_once_with(user_id, conv_id)

    # Verify clear was called on the memory
    mock_memory.clear.assert_awaited_once()


@pytest.mark.asyncio
async def test_clear_conversation_memory_creates_if_not_exists():
    """Test that _clear_conversation_memory creates memory if it doesn't exist."""
    service = ChatService(
        bot=None,
        config=None,
        billing_service=None,
        context_service=None,
        conversation_manager=None
    )

    # Don't mock _get_memory, let it run naturally
    # Mock the underlying methods it needs
    service._get_or_create_conversation = AsyncMock(return_value={"messages": []})

    user_id = 456
    conv_id = "conv2"

    # Call the method - should create memory and clear it
    await service._clear_conversation_memory(user_id, conv_id)

    # Verify memory was created
    key = f"{user_id}:{conv_id}"
    assert key in service._memories

    # Verify it's empty
    messages = await service._memories[key].get_messages()
    assert messages == []
