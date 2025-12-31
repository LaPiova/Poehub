from unittest.mock import AsyncMock, MagicMock

import pytest

from poehub.poehub import PoeHub


@pytest.fixture
def mock_cog():
    cog = MagicMock()
    # Mocking the methods we need
    cog.run_summary_pipeline = AsyncMock()
    return cog

@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.guild = MagicMock()
    ctx.channel = MagicMock()
    ctx.interaction = MagicMock()
    ctx.interaction.response.defer = AsyncMock()
    return ctx

@pytest.mark.asyncio
async def test_summary_command_success(mock_cog, mock_ctx):
    # Bind summary command
    summary_cmd = PoeHub.summary.__get__(mock_cog, PoeHub)

    await summary_cmd(mock_ctx, hours=2.5, language="zh-TW")

    # Verify Defer
    mock_ctx.interaction.response.defer.assert_awaited_with(thinking=True)

    # Verify Pipeline Call
    mock_cog.run_summary_pipeline.assert_awaited_with(
        mock_ctx,
        mock_ctx.channel,
        2.5,
        "zh-TW",
        interaction=mock_ctx.interaction
    )

@pytest.mark.asyncio
async def test_summary_command_no_guild(mock_cog, mock_ctx):
    mock_ctx.guild = None
    mock_ctx.send = AsyncMock()

    summary_cmd = PoeHub.summary.__get__(mock_cog, PoeHub)

    await summary_cmd(mock_ctx, hours=1.0)

    mock_ctx.send.assert_awaited_with("This command can only be used in a server.")
    mock_cog.run_summary_pipeline.assert_not_called()
