"""Unit tests for voice channel commands."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from poehub.poehub import PoeHub


@pytest.fixture(autouse=True)
def mock_i18n():
    with patch("poehub.core.i18n.tr", return_value="translated"), \
         patch("poehub.core.i18n.LANG_LABELS", {}):
        yield


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.is_owner = AsyncMock(return_value=True)
    bot.wait_for = AsyncMock()
    bot.loop = MagicMock()
    return bot


@pytest.fixture
def mock_config():
    conf_cls = MagicMock()
    conf = MagicMock()
    conf_cls.get_conf.return_value = conf

    enc_key = AsyncMock(return_value="test_key")
    enc_key.set = AsyncMock()
    conf.encryption_key = enc_key
    conf.dynamic_rates = AsyncMock(return_value={})
    conf.active_provider = AsyncMock(return_value="poe")
    conf.use_dummy_api = AsyncMock(return_value=False)
    conf.provider_keys = AsyncMock(return_value={})

    user_group = MagicMock()
    user_group.model = AsyncMock(return_value="gpt-4")
    user_group.language = AsyncMock(return_value="en")
    conf.user.return_value = user_group
    conf.user_from_id.return_value = user_group

    guild_group = MagicMock()
    guild_group.allowed_roles = AsyncMock(return_value=[])
    conf.guild.return_value = guild_group

    return conf_cls


@pytest.fixture
def cog(mock_bot, mock_config):
    with patch("poehub.poehub.Config", mock_config), \
         patch("poehub.poehub.EncryptionHelper"), \
         patch("poehub.poehub.ConversationStorageService"), \
         patch("poehub.poehub.BillingService"), \
         patch("poehub.poehub.ContextService"), \
         patch("poehub.poehub.ChatService"), \
         patch("poehub.poehub.SummarizerService"), \
         patch("poehub.poehub.MusicService") as MockMusic, \
         patch("asyncio.create_task") as mock_create_task:

        mock_create_task.side_effect = lambda c, *a, **k: (c.close(), MagicMock())[1]
        MockMusic.return_value = MagicMock()

        cog_inst = PoeHub(mock_bot)
        yield cog_inst


@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author = MagicMock()
    ctx.author.id = 12345
    ctx.author.voice = None
    ctx.guild = MagicMock()
    ctx.guild.id = 67890
    ctx.voice_client = None
    return ctx


# --- /join Tests ---

@pytest.mark.asyncio
async def test_join_voice_user_not_in_channel(cog, mock_ctx):
    """Test join when user is not in a voice channel."""
    mock_ctx.author.voice = None

    await cog.join_voice(mock_ctx)

    mock_ctx.send.assert_called_once()
    assert "not in a voice channel" in mock_ctx.send.call_args[0][0]


@pytest.mark.asyncio
async def test_join_voice_success(cog, mock_ctx):
    """Test successfully joining a voice channel."""
    channel = MagicMock()
    channel.name = "General"
    channel.connect = AsyncMock()

    mock_ctx.author.voice = MagicMock()
    mock_ctx.author.voice.channel = channel
    mock_ctx.voice_client = None

    await cog.join_voice(mock_ctx)

    channel.connect.assert_called_once()
    mock_ctx.send.assert_called_once()
    assert "Joined" in mock_ctx.send.call_args[0][0]
    assert "General" in mock_ctx.send.call_args[0][0]


@pytest.mark.asyncio
async def test_join_voice_already_connected_same_channel(cog, mock_ctx):
    """Test join when bot is already in the same channel."""
    channel = MagicMock()
    channel.id = 111
    channel.name = "General"

    mock_ctx.author.voice = MagicMock()
    mock_ctx.author.voice.channel = channel

    voice_client = MagicMock()
    voice_client.channel.id = 111
    mock_ctx.voice_client = voice_client

    await cog.join_voice(mock_ctx)

    mock_ctx.send.assert_called_once()
    assert "Already connected" in mock_ctx.send.call_args[0][0]


@pytest.mark.asyncio
async def test_join_voice_move_to_different_channel(cog, mock_ctx):
    """Test moving to a different channel."""
    new_channel = MagicMock()
    new_channel.id = 222
    new_channel.name = "Music"

    mock_ctx.author.voice = MagicMock()
    mock_ctx.author.voice.channel = new_channel

    voice_client = MagicMock()
    voice_client.channel.id = 111
    voice_client.move_to = AsyncMock()
    mock_ctx.voice_client = voice_client

    await cog.join_voice(mock_ctx)

    voice_client.move_to.assert_called_once_with(new_channel)
    mock_ctx.send.assert_called_once()
    assert "Joined" in mock_ctx.send.call_args[0][0]


# --- /leave Tests ---

@pytest.mark.asyncio
async def test_leave_voice_not_connected(cog, mock_ctx):
    """Test leave when bot is not connected."""
    mock_ctx.voice_client = None

    await cog.leave_voice(mock_ctx)

    mock_ctx.send.assert_called_once()
    assert "not connected" in mock_ctx.send.call_args[0][0]


@pytest.mark.asyncio
async def test_leave_voice_success(cog, mock_ctx):
    """Test successfully leaving a voice channel."""
    voice_client = MagicMock()
    voice_client.channel.name = "General"
    voice_client.disconnect = AsyncMock()
    mock_ctx.voice_client = voice_client

    await cog.leave_voice(mock_ctx)

    cog.music_service.clear_queue.assert_called_once_with(mock_ctx.guild.id)
    voice_client.disconnect.assert_called_once()
    mock_ctx.send.assert_called_once()
    assert "Left" in mock_ctx.send.call_args[0][0]
