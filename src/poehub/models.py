"""Domain models for PoeHub with Pydantic validation.

This module provides type-safe data structures for API interactions,
ensuring runtime validation and clear documentation of expected schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TokenUsage(BaseModel):
    """Token usage for a request with runtime validation.

    Replaces the dataclass version to leverage Pydantic's validation.
    Supports both USD pricing and Poe Points.
    """

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost: float = Field(default=0.0, ge=0.0)
    currency: str = Field(default="USD", pattern="^(USD|Points)$")


class ModelInfo(BaseModel):
    """LLM model information from a provider."""

    id: str
    name: str | None = None
    provider: str
    context_length: int | None = Field(default=None, ge=0)
    created: datetime | None = None


class ChatMessage(BaseModel):
    """Chat message structure for API requests.

    Validates role is one of the standard OpenAI-compatible roles.
    """

    role: str = Field(pattern="^(system|user|assistant)$")
    content: str
    name: str | None = None  # For multi-user contexts


class ImageContent(BaseModel):
    """Image content for vision-capable models."""

    type: str = Field(default="image_url", pattern="^image_url$")
    image_url: dict[str, str]  # {"url": "..."}


class TextContent(BaseModel):
    """Text content block."""

    type: str = Field(default="text", pattern="^text$")
    text: str


class ProviderConfig(BaseModel):
    """Provider configuration with validation.

    Stores API credentials and settings for an LLM provider.
    """

    provider: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    base_url: str | None = None
    model: str = Field(default="gpt-4o", min_length=1)


class ConversationData(BaseModel):
    """Conversation data structure for storage.

    Used for encrypted conversation persistence.
    """

    id: str
    title: str | None = None
    messages: list[ChatMessage] = Field(default_factory=list)
    model: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def message_count(self) -> int:
        """Return the number of messages in the conversation."""
        return len(self.messages)


class BudgetStatus(BaseModel):
    """Budget tracking for a guild.

    Tracks both USD and Points spending separately.
    """

    usd_limit: float | None = Field(default=None, ge=0.0)
    usd_spent: float = Field(default=0.0, ge=0.0)
    points_limit: int | None = Field(default=None, ge=0)
    points_spent: int = Field(default=0, ge=0)
    reset_month: str | None = None  # Format: "YYYY-MM"

    @property
    def usd_remaining(self) -> float | None:
        """Return remaining USD budget if limit is set."""
        if self.usd_limit is None:
            return None
        return max(0.0, self.usd_limit - self.usd_spent)

    @property
    def points_remaining(self) -> int | None:
        """Return remaining Points budget if limit is set."""
        if self.points_limit is None:
            return None
        return max(0, self.points_limit - self.points_spent)


class MessageData(BaseModel):
    """Data structure for a chat message to be summarized."""

    author: str
    content: str
    timestamp: str
