"""Logging utilities for PoeHub.

Provides structured logging with request correlation IDs for
tracing operations across async execution.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any

log = logging.getLogger("red.poehub")

# Context variable for request tracking across async calls
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str:
    """Get or create a request ID for the current context."""
    req_id = _request_id.get()
    if req_id is None:
        req_id = str(uuid.uuid4())[:8]
        _request_id.set(req_id)
    return req_id


def set_request_id(request_id: str) -> None:
    """Set a specific request ID for the current context."""
    _request_id.set(request_id)


def clear_request_id() -> None:
    """Clear the request ID for the current context."""
    _request_id.set(None)


class RequestContext:
    """Context manager for tracking a request with correlation ID.

    All log messages within the context will include the request ID,
    making it easy to trace operations in async environments.

    Example:
        async with RequestContext(user_id=12345, model="gpt-4") as ctx:
            ctx.info("Starting chat request")
            # ... do work ...
            ctx.info("Completed", tokens=150)
    """

    def __init__(
        self,
        request_id: str | None = None,
        **initial_context: Any,
    ):
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.context = initial_context
        self.start_time = time.time()
        self._previous_id: str | None = None

    async def __aenter__(self) -> RequestContext:
        self._previous_id = _request_id.get()
        _request_id.set(self.request_id)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        _request_id.set(self._previous_id)
        return False

    def __enter__(self) -> RequestContext:
        self._previous_id = _request_id.get()
        _request_id.set(self.request_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _request_id.set(self._previous_id)
        return False

    @property
    def elapsed(self) -> float:
        """Return elapsed time in seconds since context creation."""
        return time.time() - self.start_time

    def _format_message(self, msg: str, **extra: Any) -> str:
        """Format a log message with request ID and extra context."""
        all_context = {**self.context, **extra}
        if all_context:
            context_str = " ".join(f"{k}={v}" for k, v in all_context.items())
            return f"[{self.request_id}] {msg} | {context_str}"
        return f"[{self.request_id}] {msg}"

    def debug(self, msg: str, **extra: Any) -> None:
        """Log a debug message with context."""
        log.debug(self._format_message(msg, **extra))

    def info(self, msg: str, **extra: Any) -> None:
        """Log an info message with context."""
        log.info(self._format_message(msg, **extra))

    def warning(self, msg: str, **extra: Any) -> None:
        """Log a warning message with context."""
        log.warning(self._format_message(msg, **extra))

    def error(self, msg: str, **extra: Any) -> None:
        """Log an error message with context."""
        log.error(self._format_message(msg, **extra))

    def exception(self, msg: str, **extra: Any) -> None:
        """Log an exception with context."""
        log.exception(self._format_message(msg, **extra))
