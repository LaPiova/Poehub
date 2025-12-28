"""Shared UI helpers for PoeHub views."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import discord

from ..i18n import tr


class BackButton(discord.ui.Button):
    """Button to navigate back to a parent view."""

    def __init__(
        self, callback: Callable[[discord.Interaction], Awaitable[None]], lang: str
    ) -> None:
        super().__init__(
            label=tr(lang, "BTN_BACK"),
            style=discord.ButtonStyle.secondary,
            emoji="⬅️",
            row=3,  # Place at bottom
        )
        self.go_back = callback

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.go_back(interaction)


def preview_content(
    content: Any,
    max_len: int = 60,
    *,
    empty_label: str = "*Empty*",
    non_text_label: str = "[non-text content]",
) -> str:
    """Return a short preview string for a stored message content.

    PoeHub stores message content as either a plain string or an OpenAI-Vision
    compatible list of blocks (e.g. text + image_url). This helper converts
    either form into a short, display-friendly string.

    Args:
        content: Message content (string or list-of-blocks).
        max_len: Maximum length of the returned preview.

    Returns:
        A display string, possibly truncated.
    """
    text = ""
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, Mapping) and block.get("type") == "text":
                value = block.get("text")
                if isinstance(value, str) and value:
                    parts.append(value)
        text = " ".join(parts)
        if not text:
            text = non_text_label
    else:
        text = str(content) if content is not None else ""

    text = text.strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text or empty_label


class CloseMenuButton(discord.ui.Button):
    """Button to disable and close a view."""

    def __init__(self, *, label: str = "Close") -> None:
        super().__init__(label=label, style=discord.ButtonStyle.danger, row=3)

    async def callback(self, interaction: discord.Interaction) -> None:
        view = self.view
        if not view:
            return
        for child in view.children:
            child.disabled = True
        view.stop()
        await interaction.response.edit_message(view=view)
