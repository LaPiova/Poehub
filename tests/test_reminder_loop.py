from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from poehub.poehub import PoeHub


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.wait_until_ready = AsyncMock()
    # Mock channel and guild
    channel = MagicMock()
    channel.id = 123
    guild = MagicMock()
    member = MagicMock()
    member.id = 456
    member.mention = "<@456>"
    guild.get_member.return_value = member
    guild.get_role.return_value = None
    channel.guild = guild
    channel.send = AsyncMock()
    bot.get_channel.return_value = channel
    return bot

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.all_guilds = AsyncMock(return_value={
        789: {
            "reminders": [
                {
                    "timestamp": datetime.utcnow().timestamp() - 10, # Past time
                    "channel_id": 123,
                    "message": "Test Reminder",
                    "mentions": [456],
                    "author_id": 999
                },
                {
                    "timestamp": datetime.utcnow().timestamp() + 3600, # Future time
                    "channel_id": 123,
                    "message": "Future Reminder",
                    "mentions": [],
                    "author_id": 999
                }
            ]
        }
    })
    guild_config = MagicMock()
    guild_config.reminders.set = AsyncMock()
    config.guild_from_id.return_value = guild_config
    return config

@pytest.mark.asyncio
async def test_reminder_loop_triggers(mock_bot, mock_config):
    cog = PoeHub(mock_bot)
    cog.config = mock_config

    # Run the loop logic once manually
    await cog._reminder_loop()

    # Verify channel.send called for past reminder
    mock_bot.get_channel.assert_called_with(123)
    channel = mock_bot.get_channel.return_value
    assert channel.send.called
    args, kwargs = channel.send.call_args
    content = kwargs.get('content', args[0] if args else "")
    assert "<@456>" in content
    assert "Test Reminder" in kwargs['embed'].description

    # Verify state updated (past reminder removed)
    assert mock_config.guild_from_id.called
    guild_config = mock_config.guild_from_id.return_value
    assert guild_config.reminders.set.called
    saved_reminders = guild_config.reminders.set.call_args[0][0]
    assert len(saved_reminders) == 1
    assert saved_reminders[0]['message'] == "Future Reminder"
