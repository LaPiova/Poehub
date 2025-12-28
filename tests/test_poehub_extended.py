from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from poehub.poehub import PoeHub

# --- Copied Fixtures from test_poehub.py ---

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
    # bot.user needs to be set for some tests
    bot.user = MagicMock()
    bot.user.id = 999
    # bot.get_context needs to return valid=False by default for on_message tests
    bot.get_context = AsyncMock(return_value=MagicMock(valid=False))
    return bot

@pytest.fixture
def mock_config():
    conf_cls = MagicMock()
    conf = MagicMock()
    conf_cls.get_conf.return_value = conf

    # Global
    enc_key = AsyncMock(return_value="test_key")
    enc_key.set = AsyncMock()
    conf.encryption_key = enc_key

    dyn_rates = AsyncMock(return_value={})
    dyn_rates.set = AsyncMock()
    conf.dynamic_rates = dyn_rates

    act_prov = AsyncMock(return_value="poe")
    act_prov.set = AsyncMock()
    conf.active_provider = act_prov

    dummy = AsyncMock(return_value=False)
    dummy.set = AsyncMock()
    conf.use_dummy_api = dummy

    prov_keys = AsyncMock(return_value={})
    prov_keys.set = AsyncMock()
    conf.provider_keys = prov_keys

    def_prompt = AsyncMock(return_value=None)
    def_prompt.set = AsyncMock()
    conf.default_system_prompt = def_prompt

    # User/Guild Group Mocks
    user_group = MagicMock()
    user_group.model = AsyncMock(return_value="gpt-4")
    user_group.model.set = AsyncMock()
    user_group.system_prompt = AsyncMock(return_value=None)
    user_group.system_prompt.set = AsyncMock()
    user_group.language = AsyncMock(return_value="en")
    user_group.language.set = AsyncMock()
    user_group.conversations = AsyncMock(return_value={})
    user_group.conversations.set = AsyncMock()
    user_group.active_conversation = AsyncMock(return_value="default")
    user_group.active_conversation.set = AsyncMock()
    user_group.clear = AsyncMock()

    conf.user.return_value = user_group
    conf.user_from_id.return_value = user_group

    guild_group = MagicMock()
    conf.guild.return_value = guild_group

    return conf_cls

@pytest.fixture
def cog(mock_bot, mock_config):
    with patch("poehub.poehub.Config", mock_config), \
         patch("poehub.poehub.EncryptionHelper") as MockEnc, \
         patch("poehub.poehub.ConversationStorageService") as MockCSS, \
         patch("poehub.poehub.BillingService") as MockBilling, \
         patch("poehub.poehub.ContextService") as MockContext, \
         patch("poehub.poehub.ChatService") as MockChat, \
         patch("poehub.poehub.SummarizerService") as MockSum, \
         patch("asyncio.create_task") as mock_create_task, \
         patch("poehub.poehub.generate_key", return_value="generated_key"):

        mock_create_task.side_effect = lambda c, *a, **k: (c.close(), MagicMock())[1]

        MockChat.return_value.initialize_client = AsyncMock()
        MockBilling.return_value.start_pricing_loop = AsyncMock()
        MockContext.return_value.get_user_language = AsyncMock(return_value="en")
        MockContext.return_value.get_active_conversation_id = AsyncMock(return_value="conv_1")

        MockEnc.return_value = MagicMock()
        MockCSS.return_value = MagicMock()
        MockSum.return_value = MagicMock()

        cog_inst = PoeHub(mock_bot)
        yield cog_inst

@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.author.id = 12345
    ctx.channel = AsyncMock()
    ctx.guild = MagicMock()
    ctx.message.delete = AsyncMock()
    ctx.send = AsyncMock() # Ensure send is AsyncMock
    return ctx

# --- New Tests ---



@pytest.mark.asyncio
async def test_set_provider_invalid(cog, mock_ctx):
    await cog._initialize()
    await cog.set_provider(mock_ctx, "invalid_provider")
    mock_ctx.send.assert_called()
    assert "Invalid provider" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_set_provider_dummy_disabled(cog, mock_ctx):
    cog.allow_dummy_mode = False
    await cog._initialize()
    await cog.set_provider(mock_ctx, "dummy")
    mock_ctx.send.assert_called()
    assert "not enabled" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_set_provider_warning(cog, mock_ctx, mock_config):
    await cog._initialize()
    cog.chat_service.client = None
    await cog.set_provider(mock_ctx, "poe")
    mock_ctx.send.assert_called()
    assert "Warning" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_poehub_help(cog, mock_ctx):
    await cog._initialize()
    mock_ctx.clean_prefix = "!"
    await cog.poehub_help(mock_ctx)
    mock_ctx.send.assert_called()
    embed = mock_ctx.send.call_args[1]['embed']
    assert embed.title is not None

    cog.context_service.get_user_language = AsyncMock(return_value="zh_TW")
    await cog.poehub_help(mock_ctx)
    mock_ctx.send.assert_called()

@pytest.mark.asyncio
async def test_helper_methods_missing_manager(cog):
    cog.conversation_manager = None
    assert await cog._get_conversation(123, "c1") is None
    await cog._save_conversation(123, "c1", {})
    assert await cog._delete_conversation(123, "c1") is False
    with pytest.raises(RuntimeError):
        await cog._get_or_create_conversation(123, "c1")
    await cog._add_message_to_conversation(123, "c1", "user", "msg")
    assert await cog._get_conversation_messages(123, "c1") == []

    ctx = AsyncMock()
    ctx.author.id = 123
    await cog.list_conversations(ctx)
    ctx.send.assert_not_called()

    await cog.clear_history(ctx)
    ctx.send.assert_called_with("❌ System not initialized.")

    await cog.conversation_menu(ctx)
    ctx.send.assert_called_with("❌ System not initialized.")

    await cog.new_conversation(ctx)
    ctx.send.assert_called_with("❌ System not initialized.")

@pytest.mark.asyncio
async def test_switch_conversation_not_found(cog, mock_ctx, mock_config):
    await cog._initialize()
    conf_inst = mock_config.get_conf.return_value
    conf_inst.user_from_id.return_value.conversations = AsyncMock(return_value={})
    await cog.switch_conversation(mock_ctx, "nonexistent")
    mock_ctx.send.assert_called()
    assert "not found" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_active_conversation_delete(cog, mock_ctx, mock_config):
    await cog._initialize()
    conf_inst = mock_config.get_conf.return_value
    conf_inst.user_from_id.return_value.conversations = AsyncMock(return_value={
        "active_c": {"encrypted": "data"}
    })
    cog.conversation_manager.process_conversation_data.return_value = {"title": "Active"}
    cog.context_service.get_active_conversation_id.return_value = "active_c"
    await cog.delete_conversation(mock_ctx, "active_c")
    mock_ctx.send.assert_called()
    assert "Cannot delete the active conversation" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_list_conversations_empty(cog, mock_ctx, mock_config):
    await cog._initialize()
    conf_inst = mock_config.get_conf.return_value
    conf_inst.user.return_value.conversations = AsyncMock(return_value={})
    await cog.list_conversations(mock_ctx)
    mock_ctx.send.assert_called()
    assert "don't have any conversations" in mock_ctx.send.call_args[0][0]

@pytest.mark.asyncio
async def test_list_conversations_populated(cog, mock_ctx, mock_config):
    await cog._initialize()
    conf_inst = mock_config.get_conf.return_value
    conf_inst.user.return_value.conversations = AsyncMock(return_value={
        "c1": {"data": "enc"},
        "c2": {"data": "enc"}
    })
    cog.conversation_manager.process_conversation_data.side_effect = [
        {"title": "Conv 1", "messages": [], "created_at": 1600000000},
        {"title": "Conv 2", "messages": [], "created_at": 1600000000}
    ]
    cog.context_service.get_active_conversation_id.return_value = "c1"
    await cog.list_conversations(mock_ctx)
    mock_ctx.send.assert_called()
    embed = mock_ctx.send.call_args[1]['embed']
    assert len(embed.fields) == 2

@pytest.mark.asyncio
async def test_list_models_error(cog, mock_ctx):
    await cog._initialize()
    cog.chat_service.client = MagicMock()
    cog.chat_service.client.get_models = AsyncMock(side_effect=Exception("API Error"))
    await cog.list_models(mock_ctx)
    mock_msg = mock_ctx.send.return_value
    assert mock_msg.edit.called
    args = mock_msg.edit.call_args[1] if mock_msg.edit.call_args else mock_msg.edit.call_args_list[0][1]
    assert "Error" in (args.get('content') or "")

@pytest.mark.asyncio
async def test_list_models_no_client(cog, mock_ctx):
    await cog._initialize()
    cog.chat_service.client = None
    await cog.list_models(mock_ctx)
    mock_ctx.send.assert_called_with("❌ API client not initialized.")

@pytest.mark.asyncio
async def test_on_message_dm_not_mentioned(cog):
    await cog._initialize()
    # bot.get_context check happens early, already mocked in fixture

    message = AsyncMock()
    message.author.bot = False
    message.channel.__class__ = discord.DMChannel
    message.mentions = []
    message.content = "hello"

    cog._process_chat_request = AsyncMock()
    await cog.on_message(message)
    cog._process_chat_request.assert_called()
