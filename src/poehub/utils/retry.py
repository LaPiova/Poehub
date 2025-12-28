"""Retry utilities with exponential backoff for PoeHub.

Provides decorators for resilient async operations with configurable
retry behavior, exponential backoff, and jitter.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import random
from collections.abc import Callable
from typing import TypeVar

log = logging.getLogger("red.poehub.retry")

T = TypeVar("T")


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[Exception, int], None] | None = None,
):
    """Decorator for async functions with exponential backoff retry.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        base_delay: Initial delay between retries in seconds.
        max_delay: Maximum delay cap in seconds.
        jitter: Random jitter factor (0.0 to 1.0) to prevent thundering herd.
        exceptions: Tuple of exception types to retry on.
        on_retry: Optional callback(exception, attempt) called before each retry.

    Example:
        @async_retry(max_attempts=3, exceptions=(TimeoutError, ConnectionError))
        async def fetch_data():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (2**attempt), max_delay)

                        # Add jitter to prevent thundering herd
                        if jitter > 0:
                            delay = delay * (1 + random.uniform(-jitter, jitter))

                        log.warning(
                            f"Retry {attempt + 1}/{max_attempts} for {func.__name__} "
                            f"after {delay:.2f}s: {type(e).__name__}: {e}"
                        )

                        if on_retry:
                            on_retry(e, attempt + 1)

                        await asyncio.sleep(delay)
                    else:
                        log.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: "
                            f"{type(e).__name__}: {e}"
                        )

            # Should not reach here, but satisfy type checker
            if last_exception:
                raise last_exception
            raise RuntimeError("Retry loop exited unexpectedly")

        return wrapper

    return decorator


class RetryContext:
    """Context manager for manual retry control.

    Useful when you need more control over the retry loop than
    the decorator provides.

    Example:
        async with RetryContext(max_attempts=3) as ctx:
            for attempt in ctx:
                try:
                    result = await fetch_data()
                    break
                except TimeoutError:
                    await ctx.handle_error()
    """

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.attempt = 0
        self.last_error: Exception | None = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return False

    def __iter__(self):
        for i in range(self.max_attempts):
            self.attempt = i + 1
            yield i

    async def handle_error(self, error: Exception | None = None):
        """Handle an error by waiting before next retry."""
        if error:
            self.last_error = error

        if self.attempt < self.max_attempts:
            delay = min(self.base_delay * (2 ** (self.attempt - 1)), self.max_delay)
            log.info(f"Retry {self.attempt}/{self.max_attempts} after {delay:.2f}s")
            await asyncio.sleep(delay)
