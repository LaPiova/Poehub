"""
PoeHub - A Red-DiscordBot Cog for Poe API Integration
"""

from .poehub import PoeHub, setup

__red_end_user_data_statement__ = (
    "This cog stores user preferences (model selection, private mode) and optionally "
    "conversation history. All data is encrypted using Fernet encryption. "
    "Users can purge their data anytime with [p]purge_my_data."
)

__all__ = ["PoeHub", "setup"]

