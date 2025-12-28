from unittest.mock import AsyncMock, Mock

import pytest

from poehub.utils.retry import RetryContext, async_retry


@pytest.mark.asyncio
async def test_async_retry_success():
    """Test that the decorator allows successful execution without retries."""
    mock_func = Mock(return_value="success")

    @async_retry(max_attempts=3)
    async def decorated_func():
        return mock_func()

    result = await decorated_func()
    assert result == "success"
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_async_retry_eventual_success():
    """Test that the decorator retries on failure and eventually succeeds."""
    mock_func = Mock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

    @async_retry(max_attempts=3, base_delay=0.01, exceptions=(ValueError,))
    async def decorated_func():
        return mock_func()

    result = await decorated_func()
    assert result == "success"
    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_async_retry_max_attempts_exceeded():
    """Test that the decorator raises the last exception after max attempts."""
    mock_func = Mock(side_effect=ValueError("fail"))

    @async_retry(max_attempts=3, base_delay=0.01, exceptions=(ValueError,))
    async def decorated_func():
        return mock_func()

    with pytest.raises(ValueError, match="fail"):
        await decorated_func()

    assert mock_func.call_count == 3

@pytest.mark.asyncio
async def test_async_retry_unexpected_exception():
    """Test that the decorator does not retry on unexpected exceptions."""
    mock_func = Mock(side_effect=KeyError("fail"))

    @async_retry(max_attempts=3, base_delay=0.01, exceptions=(ValueError,))
    async def decorated_func():
        return mock_func()

    with pytest.raises(KeyError, match="fail"):
        await decorated_func()

    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_async_retry_on_retry_callback():
    """Test that the on_retry callback is invoked."""
    mock_func = Mock(side_effect=[ValueError("fail"), "success"])
    mock_callback = Mock()

    @async_retry(
        max_attempts=3,
        base_delay=0.01,
        exceptions=(ValueError,),
        on_retry=mock_callback
    )
    async def decorated_func():
        return mock_func()

    await decorated_func()

    assert mock_callback.call_count == 1
    # Check that called with (exception, attempt_number)
    call_args = mock_callback.call_args
    assert isinstance(call_args[0][0], ValueError)
    assert call_args[0][1] == 1

@pytest.mark.asyncio
async def test_retry_context_manual_control():
    """Test manual control with RetryContext."""
    mock_func = AsyncMock(side_effect=[TimeoutError("fail"), "success"])

    async with RetryContext(max_attempts=3, base_delay=0.01) as ctx:
        for _attempt in ctx:
            try:
                await mock_func()
                break
            except TimeoutError as e:
                await ctx.handle_error(e)

    assert mock_func.call_count == 2
    assert ctx.last_error is not None
    assert isinstance(ctx.last_error, TimeoutError)

@pytest.mark.asyncio
async def test_retry_context_exhaustion():
    """Test RetryContext exhaustion behaves as expected (loop finishes)."""
    mock_func = Mock(side_effect=TimeoutError("fail"))
    attempts = 0

    async with RetryContext(max_attempts=3, base_delay=0.01) as ctx:
        for _attempt in ctx:
            attempts += 1
            try:
                await mock_func()
            except TimeoutError as e:
                await ctx.handle_error(e)

    assert attempts == 3

@pytest.mark.asyncio
async def test_retry_context_no_exception_stored():
    """Test retry context when loop exits without exception."""
    # This tests the safety fallback on line 82
    attempts = 0

    async def always_succeeds():
        nonlocal attempts
        attempts += 1
        return "success"

    async with RetryContext(max_attempts=3, base_delay=0.01) as ctx:
        for _attempt in ctx:
            result = await always_succeeds()
            if result == "success":
                break

    assert attempts == 1
