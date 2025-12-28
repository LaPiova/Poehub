"""Summarizer Service for map-reduce summarization."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from ..core.protocols import IChatService, IContextService
from ..models import MessageData

log = logging.getLogger("red.poehub.services.summarizer")


class SummarizerService:
    """Service to handle complex summarization tasks using Map-Reduce."""

    def __init__(self, chat_service: IChatService, context_service: IContextService):
        self.chat = chat_service
        self.context = context_service

    async def summarize_messages(
        self,
        messages: list[MessageData],
        user_id: int,
        model: str = "gpt-4o",
        billing_guild=None,
    ) -> AsyncIterator[str]:
        """Summarize a list of messages, handling large contexts via chunking.

        Yields strings:
        - prefixed with "STATUS: " for progress updates.
        - prefixed with "RESULT: " for the final summary.
        """
        # 1. Flatten messages
        full_text = self._flatten_messages(messages)
        total_len = len(full_text)

        # 2. Check overlap/chunking
        # Conservative limit for map-reduce trigger (e.g. 12k chars ~3-4k tokens)
        CHUNK_LIMIT = 12000

        if total_len <= CHUNK_LIMIT:
            yield "STATUS: Generating summary (single pass)..."
            summary = await self._generate_summary(full_text, model, billing_guild)
            yield f"RESULT: {summary}"
            return

        # 3. Map Phase
        chunks = self._chunk_text(full_text, CHUNK_LIMIT)
        yield f"STATUS: Content too long ({total_len} chars). Split into {len(chunks)} chunks."

        chunk_summaries = []
        sem = asyncio.Semaphore(3)  # Concurrency limit



        # To yield updates as they finish, we would need as_completed.
        # For now, let's just await_gather to keep it robust.
        # Wrapper to swallow the generator yield if I messed up the async def above?
        # Wait, process_chunk defined above is async gen? No, I defined it to return.
        # Let's redefine properly.

        async def _summarize_chunk_task(text: str) -> str:
            async with sem:
                return await self._generate_summary(text, model, billing_guild, is_chunk=True)

        results = await asyncio.gather(*[_summarize_chunk_task(c) for c in chunks])
        chunk_summaries = list(results)

        yield "STATUS: All chunks summarized. Generating final synthesis..."

        # 4. Reduce Phase
        combined_summaries = "\n\n".join([f"Part {i+1}: {s}" for i, s in enumerate(chunk_summaries)])

        final_summary = await self._generate_summary(combined_summaries, model, billing_guild, is_final=True)
        yield f"RESULT: {final_summary}"

    def _flatten_messages(self, messages: list[MessageData]) -> str:
        lines = []
        for m in messages:
            lines.append(f"[{m.timestamp}] {m.author}: {m.content}")
        return "\n".join(lines)

    def _chunk_text(self, text: str, limit: int) -> list[str]:
        """Split text into chunks by lines."""
        chunks = []
        current_chunk = []
        current_len = 0

        for line in text.splitlines():
            # +1 for newline
            line_len = len(line) + 1
            if current_len + line_len > limit:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    async def _generate_summary(
        self,
        text: str,
        model: str,
        billing_guild=None,
        is_chunk: bool = False,
        is_final: bool = False
    ) -> str:
        if is_chunk:
            prompt = (
                f"Summarize the following conversation segment concisely. "
                f"Capture key points and decisions.\n\n{text}"
            )
        elif is_final:
            prompt = (
                f"Here are summaries of a long conversation split into parts. "
                f"Synthesize them into a single coherent, comprehensive summary. "
                f"Identify the dominant language and write the summary in that language.\n\n{text}"
            )
        else:
            prompt = (
                f"Please provide a comprehensive summary of the conversation below. "
                f"Identify the dominant language and write the summary in that language.\n\n{text}"
            )

        messages = [{"role": "user", "content": prompt}]
        return await self.chat.get_response(messages, model=model, billing_guild=billing_guild)
