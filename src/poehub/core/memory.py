import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

log = logging.getLogger("poehub.core.memory")

class ThreadSafeMemory:
    """Thread-safe memory manager using asyncio.Lock.

    This class manages a list of conversation messages, allowing for concurrent
    access and updates. It implements an optimistic concurrency pattern for
    heavy operations like summarization to minimize lock contention.
    """

    def __init__(self, initial_messages: list[dict[str, Any]] | None = None):
        """Initialize the memory buffer.

        Args:
            initial_messages: Optional initial list of message dictionaries.
        """
        self._buffer: list[dict[str, Any]] = list(initial_messages) if initial_messages else []
        self._lock = asyncio.Lock()

    async def add_message(self, message: dict[str, Any]) -> None:
        """Add a message to the buffer in a thread-safe manner.

        Args:
            message: The message dictionary to append.
        """
        async with self._lock:
            self._buffer.append(message)

    async def get_messages(self) -> list[dict[str, Any]]:
        """Retrieve a copy of the current messages.

        Returns:
            List[Dict[str, Any]]: A copy of the message list.
        """
        async with self._lock:
            return list(self._buffer)

    async def clear(self) -> None:
        """Clear the memory buffer."""
        async with self._lock:
            self._buffer.clear()

    async def process_summary(
        self,
        summarizer: Callable[[list[dict[str, Any]]], Awaitable[dict[str, Any]]]
    ) -> None:
        """Summarize memory using optimistic concurrency.

        1. Snaps the buffer (copies current messages).
        2. Releases lock during the potentially long running summarizer (I/O).
        3. Re-acquires lock to update the buffer with the summary, preserving
           any new messages that arrived during the summarization step.

        Args:
            summarizer: A coroutine function that takes a list of messages
                        and returns a single summary message dictionary.
        """
        # 1. Snap the buffer
        async with self._lock:
            if not self._buffer:
                return
            snapshot = list(self._buffer)
            snapshot_count = len(snapshot)

        # 2. I/O Summarization (Lock is released here)
        try:
            summary_message = await summarizer(snapshot)
        except Exception as e:
            log.error(f"Summarization failed: {e}")
            return

        # 3. Re-acquire lock to update
        async with self._lock:
            # We assume the buffer behaves as an append-only log essentially.
            # We want to replace the messages that were summarized with the summary message.
            # Any messages that were added AFTER our snapshot should be preserved.

            # Calculate the messages that arrived during the I/O operation
            # Note: We handle the case where the buffer might have been cleared or shortened
            # externally logic by checking lengths.

            # If buffer length is smaller than snapshot_count, it means it was truncated/cleared.
            # In that case, we might decide to just prepend to current, or (safer) discard summary
            # depending on desired behavior. Here we assume we want to keep current state + summary
            # if possible, or just treat 'new_messages' as whatever is currently there.

            # Standard case: buffer grew.
            if len(self._buffer) >= snapshot_count:
                new_messages = self._buffer[snapshot_count:]
                self._buffer = [summary_message] + new_messages
            else:
                # Buffer shrank (e.g. cleared).
                # Strategy: If cleared, we probably start fresh.
                # If we force summary in, we might resurrect old context.
                # Let's assume if it shrank, we accept the current state as authoritative and discard summary
                # to avoid confusion, OR we just prepend.
                # For safety against race conditions where 'clear' was intentional:
                log.warning("Buffer modification detected during summarization (shrank). Discarding summary update.")
                pass
