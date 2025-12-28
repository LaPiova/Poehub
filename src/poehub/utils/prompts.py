"""Shared helpers for working with large system prompts."""

from __future__ import annotations

import io

import discord

PromptPayload = tuple[str, str]

PROMPT_PREFILL_LIMIT = 1200  # Switch modal to append-only mode when exceeded
PROMPT_TEXTINPUT_MAX = 1500  # Discord text input max length


def prompt_to_file(content: str, filename: str) -> discord.File:
    """Return a Discord file attachment containing the full prompt text."""
    buffer = io.BytesIO(content.encode("utf-8"))
    buffer.seek(0)
    return discord.File(buffer, filename=filename)


async def send_prompt_files_dm(
    user: discord.User | discord.Member,
    payloads: list[PromptPayload],
    message: str,
) -> bool:
    """Send prompt text files via DM. Returns True if successful."""
    if not payloads:
        return False

    try:
        dm_channel = user.dm_channel or await user.create_dm()
        files = [prompt_to_file(content, filename) for filename, content in payloads]
        await dm_channel.send(message, files=files)
        return True
    except discord.Forbidden:
        return False
    except discord.HTTPException:
        return False
