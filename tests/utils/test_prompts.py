import io
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from poehub.utils.prompts import prompt_to_file, send_prompt_files_dm


def test_prompt_to_file():
    content = "Hello world"
    filename = "hello.txt"
    f = prompt_to_file(content, filename)
    assert isinstance(f, discord.File)
    assert f.filename == filename
    # discord.File takes fp, we can check if it's readable
    assert isinstance(f.fp, io.BytesIO)
    f.fp.seek(0)
    assert f.fp.read().decode('utf-8') == content

@pytest.mark.asyncio
async def test_send_prompt_files_dm_success():
    mock_user = Mock(spec=discord.User)
    mock_channel = AsyncMock()
    # Mocking dm_channel property is tricky on a Mock object if not configured right,
    # but let's assume standard behavior.
    # However, user.dm_channel is an attribute.
    mock_user.dm_channel = None
    mock_user.create_dm = AsyncMock(return_value=mock_channel)

    payloads = [("test.txt", "content")]

    result = await send_prompt_files_dm(mock_user, payloads, "Here are files")

    assert result is True
    mock_user.create_dm.assert_called_once()
    mock_channel.send.assert_called_once()
    assert len(mock_channel.send.call_args[1]['files']) == 1

@pytest.mark.asyncio
async def test_send_prompt_files_dm_existing_channel():
    mock_user = Mock(spec=discord.User)
    mock_channel = AsyncMock()
    mock_user.dm_channel = mock_channel

    payloads = [("test.txt", "content")]

    result = await send_prompt_files_dm(mock_user, payloads, "Here are files")

    assert result is True
    # Should not call create_dm if dm_channel exists
    # Wait, the code is: dm_channel = user.dm_channel or await user.create_dm()
    # If user.dm_channel is set, create_dm is NOT called.
    # But mock_user.create_dm might not be called.

    mock_channel.send.assert_called_once()

@pytest.mark.asyncio
async def test_send_prompt_files_dm_empty():
    mock_user = Mock()
    result = await send_prompt_files_dm(mock_user, [], "msg")
    assert result is False

@pytest.mark.asyncio
async def test_send_prompt_files_dm_forbidden():
    mock_user = Mock()
    mock_user.dm_channel = None
    # Mock create_dm to raise Forbidden
    response = Mock()
    response.status = 403
    mock_user.create_dm = AsyncMock(side_effect=discord.Forbidden(response, "no"))

    payloads = [("a", "b")]
    result = await send_prompt_files_dm(mock_user, payloads, "msg")
    assert result is False

@pytest.mark.asyncio
async def test_send_prompt_files_dm_http_error():
    mock_user = Mock()
    mock_user.dm_channel = None
    response = Mock()
    response.status = 500
    mock_user.create_dm = AsyncMock(side_effect=discord.HTTPException(response, "error"))

    payloads = [("a", "b")]
    result = await send_prompt_files_dm(mock_user, payloads, "msg")
    assert result is False
