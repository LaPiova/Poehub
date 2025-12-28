"""PoeHub - A Red-DiscordBot cog for Poe API integration.

This package is designed to be copied into a Red-DiscordBot custom cogs path
as `poehub/` (containing `info.json` and this module).
"""

from __future__ import annotations

from .poehub import PoeHub, setup

__red_end_user_data_statement__ = (
    "This cog stores user preferences (model selection, private mode) and "
    "optionally conversation history. All data is encrypted using Fernet "
    "encryption. Users can purge their data anytime with [p]purge_my_data."
)

__all__ = ["PoeHub", "setup"]
