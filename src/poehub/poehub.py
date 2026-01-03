"""PoeHub - Red-DiscordBot cog for Poe API integration.

PoeHub connects to Poe's OpenAI-compatible endpoint and provides:
- multi-model chat
- encrypted per-user conversation storage
- image attachments (OpenAI vision format)
- optional DM/private mode
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import deque
from datetime import datetime
from typing import Any

import discord
from discord.ext import tasks
from redbot.core import Config
from redbot.core import commands as red_commands
from redbot.core.bot import Red, app_commands

from .core.encryption import EncryptionHelper, generate_key
from .core.i18n import LANG_EN, LANG_LABELS, LANG_ZH_TW, tr
from .services.billing import BillingService
from .services.billing.crawler import PricingCrawler
from .services.billing.oracle import PricingOracle
from .services.chat import ChatService
from .services.context import ContextService
from .services.conversation.storage import ConversationStorageService
from .services.music import MusicService
from .services.summarizer import SummarizerService
from .ui.config_view import PoeConfigView
from .ui.conversation_view import ConversationMenuView
from .ui.home_view import HomeMenuView
from .ui.language_view import LanguageView
from .ui.provider_view import ProviderConfigView
from .ui.reminder_view import ReminderView
from .utils.prompts import prompt_to_file


def _env_flag(name: str, default: str = "0") -> bool:
    """Return True if the env var is set to a truthy value."""
    value = os.getenv(name, default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


ALLOW_DUMMY_MODE = _env_flag("POEHUB_ENABLE_DUMMY_MODE", "0")


log = logging.getLogger("red.poehub")


class PoeHub(red_commands.Cog):
    """
    PoeHub Cog - Connect to Poe API using OpenAI-compatible endpoints
    PoeHub 模組 - 使用 OpenAI 相容端點連接到 Poe API

    Features 功能:
    - Multi-model support (Claude, GPT-4, etc.)
      多模型支援（Claude、GPT-4 等）
    - Encrypted local data storage
      加密本地資料儲存
    - Image attachment support
      圖片附件支援
    - Private mode for DM responses
      私訊回覆的私密模式
    - Conversation context management
      對話上下文管理
    """

    def __init__(self, bot: Red):
        self.bot = bot
        # Changed identifier to force fresh DB and avoid corruption/migration issues
        self.config = Config.get_conf(
            self, identifier=1234567891, force_registration=True
        )
        self.allow_dummy_mode = ALLOW_DUMMY_MODE

        # Default configuration
        default_global = {
            "active_provider": "poe",
            "provider_keys": {},  # Dict[str, str] mapping provider -> api_key
            "provider_urls": {
                "poe": "https://api.poe.com/v1",
                "openai": "https://api.openai.com/v1",
                "deepseek": "https://api.deepseek.com",
                "openrouter": "https://openrouter.ai/api/v1",
            },
            # Legacy fields kept for migration/fallback
            "api_key": None,
            "base_url": "https://api.poe.com/v1",
            "default_system_prompt": None,
            "use_dummy_api": False,
            "dynamic_rates": {},  # Dict[str, Tuple[float, float, str]] - Provider/Model -> (In, Out, Currency)
            "encryption_key": None,
        }

        default_guild = {
            "access_allowed": True,
            "monthly_limit": 5,  # Float (USD), None = infinite
            "current_spend": 0.0,  # Float (USD)
            "monthly_limit_points": 250000,  # Int (Points), None = infinite
            "current_spend_points": 0.0,  # Float/Int (Points)
            "last_reset_month": None,  # Str "YYYY-MM"
            "reminders": [],  # List[Dict] {timestamp, channel_id, message, mentions, author_id, created_at}
            "allowed_roles": [],  # List[int] Role IDs allowed to access the bot (empty = all)
        }

        default_user = {
            "model": "Gemini-3-Pro",
            "conversations": {},  # Dict of conversation_id -> conversation data (encrypted)
            "active_conversation": "default",  # Currently active conversation ID
            "system_prompt": None,  # User's custom system prompt (overrides default)
            "language": LANG_EN,  # Output language for menus/help
        }

        default_channel = {
            "conversations": {},  # Dict of conversation_id -> conversation data
            "updated_at": 0,
        }

        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        self.config.register_guild(**default_guild)
        self.config.register_channel(**default_channel)

        self.conversation_manager: ConversationStorageService | None = None
        self.encryption: EncryptionHelper | None = None
        self.billing: BillingService | None = None
        self.music_service: MusicService = MusicService()

        # Idempotency
        self._processed_messages = deque(maxlen=50)

        # Initialize encryption on load
        asyncio.create_task(self._initialize())

    async def _initialize(self) -> None:
        """Initialize encryption, conversation manager, and API client."""
        try:
            # Check for encryption key
            encryption_key = await self.config.encryption_key()
            if not encryption_key:
                # Generate new key
                encryption_key = generate_key()
                await self.config.encryption_key.set(encryption_key)
                log.info("Generated new encryption key")

            # Initialize helpers
            self.encryption = EncryptionHelper(encryption_key)
            self.conversation_manager = ConversationStorageService(self.encryption)
            self.billing = BillingService(self.bot, self.config)
            self.context_service = ContextService(self.config)
            self.chat_service = ChatService(
                self.bot,
                self.config,
                self.billing,
                self.context_service,
                self.conversation_manager,
            )
            self.summarizer = SummarizerService(self.chat_service, self.context_service)

            # Load dynamic rates
            stored_rates = await self.config.dynamic_rates()
            if stored_rates:
                PricingOracle.load_dynamic_rates(stored_rates)
                log.info(f"Loaded {len(stored_rates)} dynamic pricing rates.")

            # Initialize API client if key exists
            await self._init_client()

        except Exception:
            log.exception("Error initializing PoeHub")
            return

        # Start background tasks
        await self.billing.start_pricing_loop()
        self._auto_clear_loop.start()
        self._reminder_loop.start()
        # Initialize client via service
        await self.chat_service.initialize_client()

    def cog_unload(self):
        """Clean up when cog is unloaded."""
        if self._auto_clear_loop.is_running():
            self._auto_clear_loop.cancel()
        if self._reminder_loop.is_running():
            self._reminder_loop.cancel()
        if self.billing:
            asyncio.create_task(self.billing.stop_pricing_loop())

    async def _init_client(self) -> None:
        """Initialize the LLM client based on configuration."""
        if self.chat_service:
            await self.chat_service.initialize_client()

    async def _get_matching_models(self, query: str | None = None) -> list[str]:
        """Fetch and filter models matching the query."""
        if self.chat_service:
            return await self.chat_service.get_matching_models(query)
        return []

    async def _build_model_select_options(
        self, query: str | None = None
    ) -> list[discord.SelectOption]:
        """Build dropdown options for the interactive config panel."""
        fallback_models = [
            "Claude-Sonnet-4.5",
            "GPT-5.2-Pro",
            "Gemini-3-Pro",
            "Claude-Opus-4.5",
            "Claude-3.5-Sonnet",
            "GPT-4o",
            "o1-preview",
            "Gemini-1.5-Pro",
            "Llama-3.1-405B",
            "Claude-3-Haiku",
            "GPT-4",
            "GPT-3.5-Turbo",
        ]
        options: list[discord.SelectOption] = []

        matching_ids = await self._get_matching_models(query)

        for model_id in matching_ids:
            options.append(discord.SelectOption(label=model_id[:100], value=model_id))
            if len(options) >= 25:
                break

        if not options and not query:
            # Only show fallbacks if no query was provided AND no live models found
            for model_id in fallback_models:
                options.append(discord.SelectOption(label=model_id, value=model_id))

        return options[:25]

    async def _build_config_embed(
        self,
        ctx: red_commands.Context,
        owner_mode: bool,
        dummy_state: bool,
        lang: str,
    ) -> discord.Embed:
        """Create the status embed for the interactive config menu."""
        embed = discord.Embed(
            title=tr(lang, "CONFIG_TITLE"),
            description=tr(lang, "CONFIG_DESC"),
            color=discord.Color.blurple(),
        )
        current_model = await self.config.user(ctx.author).model()

        # Determine effective provider for display
        active_provider = await self.config.active_provider()

        embed.add_field(
            name=tr(lang, "CONFIG_FIELD_MODEL"),
            value=f"`{current_model}`",
            inline=True,
        )
        embed.add_field(
            name="Provider",
            value=f"`{active_provider}`",
            inline=True,
        )

        user_prompt = await self.config.user(ctx.author).system_prompt()
        embed.add_field(
            name=tr(lang, "CONFIG_FIELD_PROMPT"),
            value=tr(lang, "CONFIG_PROMPT_SET")
            if user_prompt
            else tr(lang, "CONFIG_PROMPT_NOT_SET"),
            inline=True,
        )

        return embed

    async def _process_chat_request(
        self, message: discord.Message, content: str, ctx: red_commands.Context = None
    ):
        """Unified handler for processing chat requests."""
        if self.chat_service:
            await self.chat_service.process_chat_request(message, content, ctx)

    # --- Conversation Management Methods (Refactored) ---

    async def _get_conversation(
        self, user_id: int, conv_id: str
    ) -> dict[str, Any] | None:
        """Get a conversation by ID for a user"""
        if not self.conversation_manager:
            return None

        conversations = await self.config.user_from_id(user_id).conversations()
        if conv_id in conversations:
            return self.conversation_manager.process_conversation_data(
                conversations[conv_id]
            )
        return None

    async def _save_conversation(
        self, user_id: int, conv_id: str, conv_data: dict[str, Any]
    ):
        """Save a conversation for a user (encrypted)"""
        if not self.conversation_manager:
            return

        conversations = await self.config.user_from_id(user_id).conversations()

        # Use manager to encrypt
        conversations[conv_id] = self.conversation_manager.prepare_for_storage(
            conv_data
        )

        await self.config.user_from_id(user_id).conversations.set(conversations)

    async def _delete_conversation(self, user_id: int, conv_id: str) -> bool:
        """Delete a conversation"""
        conversations = await self.config.user_from_id(user_id).conversations()

        if conv_id in conversations:
            del conversations[conv_id]
            await self.config.user_from_id(user_id).conversations.set(conversations)
            return True
        return False

    async def _get_or_create_conversation(
        self, user_id: int, conv_id: str
    ) -> dict[str, Any]:
        """Get or create a conversation"""
        if not self.conversation_manager:
            raise RuntimeError("Conversation manager not initialized")

        conv = await self._get_conversation(user_id, conv_id)

        if conv is None:
            conv = self.conversation_manager.create_conversation(conv_id)
            await self._save_conversation(user_id, conv_id, conv)

        return conv



    async def _get_language(self, user_id: int) -> str:
        """Get the user's preferred language."""
        if self.context_service:
            return await self.context_service.get_user_language(user_id)
        return LANG_EN

    # --- Auto-Clear Loop ---

    @tasks.loop(minutes=5)
    async def _auto_clear_loop(self):
        """Check for inactive conversations and clear history."""
        try:
            now = time.time()
            limit = 2 * 60 * 60  # 2 hours in seconds

            all_users = await self.config.all_users()
            for user_id, user_data in all_users.items():
                conversations = user_data.get("conversations", {})
                if not conversations:
                    continue

                changed = False
                for conv_id, enc_data in conversations.items():
                    # Decrypt to check timestamp
                    data = self.conversation_manager.process_conversation_data(enc_data)
                    if not data:
                        continue

                    messages = data.get("messages", [])
                    if not messages:
                        continue

                    updated_at = data.get("updated_at")
                    # If updated_at is missing, use created_at, or assume active to be safe
                    if not updated_at:
                        updated_at = data.get("created_at", now)

                    if now - updated_at > limit:
                        # Clear messages
                        log.info(f"Auto-clearing inactive conversation {conv_id} for user {user_id}")
                        self.conversation_manager.clear_messages(data)

                        # Re-encrypt
                        conversations[conv_id] = self.conversation_manager.prepare_for_storage(data)
                        changed = True

                        # Clear memory cache
                        # We pass the unique key for user scope
                        unique_key = f"user:{user_id}:{conv_id}"
                        if self.chat_service:
                            await self.chat_service._clear_conversation_memory(unique_key)

                if changed:
                    await self.config.user_from_id(user_id).conversations.set(conversations)

            # --- Thread/Channel Cleanup (48h) ---
            limit_thread = 48 * 60 * 60  # 2 days
            all_channels = await self.config.all_channels()

            for channel_id, channel_data in all_channels.items():
                conversations = channel_data.get("conversations", {})
                if not conversations:
                    continue

                changed = False
                for conv_id, enc_data in conversations.items():
                    data = self.conversation_manager.process_conversation_data(enc_data)
                    if not data:
                        continue

                    updated_at = data.get("updated_at")
                    if not updated_at:
                         updated_at = data.get("created_at", now)

                    if now - updated_at > limit_thread:
                        log.info(f"Auto-clearing inactive thread {channel_id}")
                        self.conversation_manager.clear_messages(data)
                        conversations[conv_id] = self.conversation_manager.prepare_for_storage(data)
                        changed = True

                        unique_key = f"channel:{channel_id}:{conv_id}"
                        if self.chat_service:
                            await self.chat_service._clear_conversation_memory(unique_key)

                if changed:
                    await self.config.channel_from_id(channel_id).conversations.set(conversations)

        except Exception:
            log.exception("Error in auto-clear loop")

    @_auto_clear_loop.before_loop
    async def _before_auto_clear(self):
        await self.bot.wait_until_ready()

    # --- Reminder Loop ---

    @tasks.loop(seconds=60)
    async def _reminder_loop(self):
        """Check for pending reminders."""
        try:
            now_ts = datetime.utcnow().timestamp()
            all_guilds = await self.config.all_guilds()

            for guild_id, guild_data in all_guilds.items():
                reminders = guild_data.get("reminders", [])
                if not reminders:
                    continue

                remaining_reminders = []
                changed = False

                for r in reminders:
                    trigger_ts = r.get("timestamp", 0)
                    if trigger_ts <= now_ts:
                        # Trigger reminder
                        channel_id = r.get("channel_id")
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            mentions = []
                            for m_id in r.get("mentions", []):
                                # Try to get user or role
                                user = channel.guild.get_member(m_id)
                                if user:
                                    mentions.append(user.mention)
                                    continue
                                role = channel.guild.get_role(m_id)
                                if role:
                                    mentions.append(role.mention)

                            mention_str = " ".join(mentions)
                            embed = discord.Embed(
                                title="🔔 Reminder",
                                description=r.get("message", "No content"),
                                color=discord.Color.gold()
                            )
                            embed.set_footer(text=f"Scheduled by <@{r.get('author_id')}>")

                            try:
                                await channel.send(content=f"{mention_str}", embed=embed)
                            except discord.Forbidden:
                                log.warning(f"Missing permissions to send reminder in channel {channel_id}")
                            except Exception as e:
                                log.error(f"Error sending reminder: {e}")

                        changed = True
                    else:
                        remaining_reminders.append(r)

                if changed:
                    await self.config.guild_from_id(guild_id).reminders.set(remaining_reminders)

        except Exception:
            log.exception("Error in reminder loop")

    @_reminder_loop.before_loop
    async def _before_reminder_loop(self):
        await self.bot.wait_until_ready()

    # --- Commands ---

    @red_commands.command(name="provider")
    @red_commands.is_owner()
    async def provider_menu(self, ctx: red_commands.Context):
        """Open the interactive provider configuration menu."""
        lang = await self._get_language(ctx.author.id)

        view = ProviderConfigView(self, ctx, lang)

        # Initial status embed
        active = await self.config.active_provider()
        dummy = await self.config.use_dummy_api()

        embed = discord.Embed(
            title="Provider Configuration",
            description="Select an AI provider and set your API key.",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Active Provider", value=f"**{active}**", inline=True)
        embed.add_field(name="Dummy Mode", value="ON" if dummy else "OFF", inline=True)

        # Check key
        if active != "dummy":
            keys = await self.config.provider_keys()
            has_key = bool(keys.get(active))
            embed.add_field(
                name="API Key Set", value="✅ Yes" if has_key else "❌ No", inline=True
            )

        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    # Legacy command aliases kept for backward compatibility...
    @red_commands.command(name="setprovider", hidden=True)
    @red_commands.is_owner()
    async def set_provider(self, ctx: red_commands.Context, provider: str):
        """
        Set the active AI provider (Legacy: use [p]provider menu instead).
        """
        provider = provider.lower()
        valid_providers = [
            "poe",
            "openai",
            "anthropic",
            "google",
            "deepseek",
            "openrouter",
            "dummy",
        ]

        if provider not in valid_providers:
            await ctx.send(
                f"❌ Invalid provider. Choose from: {', '.join(valid_providers)}"
            )
            return

        if provider == "dummy" and not self.allow_dummy_mode:
            await ctx.send("❌ Dummy mode is not enabled in this build.")
            return

        if provider == "dummy":
            await self.config.use_dummy_api.set(True)
        else:
            await self.config.use_dummy_api.set(False)

        await self.config.active_provider.set(provider)
        await self._init_client()

        msg = f"✅ Active provider set to **{provider}**."

        if not (self.chat_service and self.chat_service.client) and provider != "dummy":
            msg += f"\n⚠️ **Warning**: Client not initialized. You probably need to set an API key for {provider}.\nUse `[p]setapikey {provider} <key>`."

        await ctx.send(msg)

    @red_commands.command(name="setapikey", aliases=["setkey"])
    @red_commands.is_owner()
    async def set_provider_key(
        self, ctx: red_commands.Context, provider: str, api_key: str
    ):
        """
        Set the API key for a specific provider.
        Usage: [p]setkey <provider> <key>
        """
        provider = provider.lower()
        provider_keys = await self.config.provider_keys()
        provider_keys[provider] = api_key
        await self.config.provider_keys.set(provider_keys)

        # If setting key for active provider, re-init
        active = await self.config.active_provider()
        if active == provider:
            await self._init_client()

        try:
            await ctx.message.delete()
        except Exception:
            pass

        await ctx.send(
            f"✅ API key for **{provider}** updated successfully! (Message deleted)"
        )

    @red_commands.command(name="poeapikey", aliases=["pkey"])
    @red_commands.is_owner()
    async def set_api_key(self, ctx: red_commands.Context, api_key: str):
        """
        Set the Poe API key (Legacy alias).
        Equivalent to: [p]setkey poe <key>
        """
        await self.set_provider_key(ctx, "poe", api_key)

    @red_commands.command(name="updatepricing")
    @red_commands.is_owner()
    async def update_pricing(self, ctx: red_commands.Context):
        """
        Manually trigger a pricing update from web/API sources.
        """
        msg = await ctx.send(
            "🔄 Fetching latest pricing data (OpenRouter + LiteLLM Repository)..."
        )

        # 1. Fetch from LiteLLM (Crawler)
        crawler_rates = await PricingCrawler.fetch_rates()
        count_crawler = len(crawler_rates)

        # 2. Fetch from OpenRouter (if client supports it)
        openrouter_rates = {}
        if self.chat_service.client and hasattr(
            self.chat_service.client, "fetch_openrouter_pricing"
        ):
            openrouter_rates = await self.chat_service.client.fetch_openrouter_pricing()

        # Merge: OpenRouter takes precedence for its own models if overlap?
        # Actually, let's just merge crawler first, then openrouter
        final_rates = {}
        final_rates.update(crawler_rates)
        final_rates.update(openrouter_rates)

        if not final_rates:
            await msg.edit(content="❌ Could not fetch any pricing data.")
            return

        PricingOracle.load_dynamic_rates(final_rates)
        current_rates = await self.config.dynamic_rates()
        current_rates.update(final_rates)
        await self.config.dynamic_rates.set(current_rates)

        await msg.edit(
            content=f"✅ Pricing updated!\n- Fetched {count_crawler} rates from LiteLLM\n- Fetched {len(openrouter_rates)} rates from OpenRouter"
        )

    @red_commands.command(name="poedummymode", aliases=["pdummy", "dummy"])
    @red_commands.is_owner()
    async def toggle_dummy_mode(
        self, ctx: red_commands.Context, *, state: str | None = None
    ):
        """Enable/disable offline dummy API mode or show its status"""
        if not self.allow_dummy_mode:
            await ctx.send("❌ Dummy API mode is disabled in this release build.")
            return
        if state is None:
            enabled = await self.config.use_dummy_api()
            status_text = "ON" if enabled else "OFF"
            await ctx.send(f"🔧 Dummy API mode is currently **{status_text}**.")
            return

        normalized = state.strip().lower()
        if normalized in {"on", "true", "enable", "enabled", "1"}:
            enabled = True
        elif normalized in {"off", "false", "disable", "disabled", "0"}:
            enabled = False
        else:
            await ctx.send("❌ Please specify `on` or `off`.")
            return

        await self.config.use_dummy_api.set(enabled)
        await self._init_client()

        if enabled:
            await ctx.send(
                "✅ Dummy API mode enabled. PoeHub will return local stub responses for debugging."
            )
        else:
            await ctx.send(
                "✅ Dummy API mode disabled. Remember to set a valid Poe API key with `[p]poeapikey`."
            )

    @red_commands.hybrid_command(name="menu", aliases=["poehub", "home"])
    async def poehub_menu(self, ctx: red_commands.Context):
        """Open the unified PoeHub Home Menu."""
        lang = await self._get_language(ctx.author.id)
        view = HomeMenuView(self, ctx, lang)

        embed = discord.Embed(
            title=tr(lang, "HOME_TITLE"),
            description=tr(lang, "HOME_DESC"),
            color=discord.Color.blue(),
        )
        msg = await ctx.send(embed=embed, view=view, ephemeral=True)
        view.message = msg

    @red_commands.hybrid_command(name="reminder")
    @red_commands.guild_only()
    async def reminder_command(self, ctx: red_commands.Context):
        """Set a scheduled reminder with mentions."""
        async def confirm_callback(data):
            async with self.config.guild(ctx.guild).reminders() as reminders:
                import time
                data["created_at"] = time.time()
                reminders.append(data)

        async def delete_callback(value):
            async with self.config.guild(ctx.guild).reminders() as reminders:
                # Value is "created_at_timestamp"
                # Find mismatching reminder to remove
                # We iterate and find key match
                to_remove = None
                for r in reminders:
                    k = f"{r.get('created_at')}_{r.get('timestamp')}"
                    if k == value:
                        to_remove = r
                        break

                if to_remove:
                    reminders.remove(to_remove)
                    return True
                return False

        # Fetch existing reminders for this user
        all_reminders = await self.config.guild(ctx.guild).reminders()
        user_reminders = [r for r in all_reminders if r.get("author_id") == ctx.author.id]

        view = ReminderView(ctx, confirm_callback, user_reminders, delete_callback)
        embed = view.build_embed()
        view.message = await ctx.send(embed=embed, view=view, ephemeral=True)

    @red_commands.hybrid_command(name="config", aliases=["poeconfig"])
    async def open_config_menu(self, ctx: red_commands.Context):
        """Open the interactive configuration panel"""
        lang = await self._get_language(ctx.author.id)
        model_options = await self._build_model_select_options()
        is_owner = await self.bot.is_owner(ctx.author)
        dummy_state = (
            await self.config.use_dummy_api()
            if (is_owner and self.allow_dummy_mode)
            else False
        )

        embed = await self._build_config_embed(ctx, is_owner, dummy_state, lang)

        view = PoeConfigView(
            cog=self,
            ctx=ctx,
            model_options=model_options,
            owner_mode=is_owner,
            dummy_state=dummy_state,
            lang=lang,
        )

        msg = await ctx.send(embed=embed, view=view, ephemeral=True)
        view.message = msg

    @red_commands.command(name="language", aliases=["lang"])
    async def language_menu(self, ctx: red_commands.Context):
        """Open the language selection menu."""
        lang = await self._get_language(ctx.author.id)
        current = LANG_LABELS.get(lang, lang)
        embed = discord.Embed(
            title=tr(lang, "LANG_TITLE"),
            description=tr(lang, "LANG_DESC"),
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name=tr(lang, "LANG_CURRENT"), value=f"`{current}`", inline=False
        )
        view = LanguageView(self, ctx, lang)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    @red_commands.command(name="ask")
    async def ask(self, ctx: red_commands.Context, *, query: str):
        """
        Ask a question to Poe AI (with conversation context)
        Usage: [p]ask <your question>
        """
        await self._process_chat_request(ctx.message, query, ctx)

    @red_commands.command(name="setmodel")
    async def set_model(self, ctx: red_commands.Context, *, model_name: str):
        """Set your preferred AI model"""
        await self.config.user(ctx.author).model.set(model_name)
        await ctx.send(f"✅ Your model has been set to: **{model_name}**")

    @red_commands.command(name="mymodel")
    async def my_model(self, ctx: red_commands.Context):
        """Check your current model setting"""
        model = await self.config.user(ctx.author).model()
        await ctx.send(f"🤖 Your current model: **{model}**")

    @red_commands.hybrid_command(name="websearch")
    async def web_search(self, ctx: red_commands.Context, state: bool):
        """
        Enable or disable web search for the current conversation.
        Usage: [p]websearch True/False (or On/Off)
        """
        # Determine context scope
        is_dm = isinstance(ctx.channel, discord.DMChannel)

        if is_dm:
            # User scope
            user_id = ctx.author.id
            conv_id = await self.context_service.get_active_conversation_id(user_id)
            conv = await self._get_or_create_conversation(user_id, conv_id)
            scope_desc = "DM"
        else:
            # Channel/Thread scope
            # Note: We need to use the channel ID as scope group logic in chat service uses config.channel(target)
            # But here we are in the main cog. The helper _get_conversation uses USER ID by default.
            # We need to manually handle channel scope here or add a helper.
            # Let's inspect _get_conversation... it takes user_id.
            # We need a channel equivalent.

            # Direct config access for channel/thread
            scope_group = self.config.channel(ctx.channel)
            conversations = await scope_group.conversations()
            conv_id = "default"

            if conv_id in conversations:
                 conv = self.conversation_manager.process_conversation_data(conversations[conv_id])
            else:
                 conv = self.conversation_manager.create_conversation(conv_id)

            scope_desc = "Channel/Thread"

        if not conv:
             await ctx.send("❌ Could not retrieve conversation data.")
             return

        # Update setting
        # We store it in optimizer_settings which ChatService reads
        if "optimizer_settings" not in conv or conv["optimizer_settings"] is None:
            conv["optimizer_settings"] = {}

        conv["optimizer_settings"]["web_search_override"] = state

        # Save back
        if is_dm:
            await self._save_conversation(ctx.author.id, conv_id, conv)
        else:
            # Manual save for channel since _save_conversation is user-centric
            conversations = await self.config.channel(ctx.channel).conversations()
            conversations[conv_id] = self.conversation_manager.prepare_for_storage(conv)
            await self.config.channel(ctx.channel).conversations.set(conversations)

        status_text = "Enabled" if state else "Disabled"
        await ctx.send(f"✅ Web Search **{status_text}** for this {scope_desc} conversation.")

    @red_commands.hybrid_command(name="threadmodel", aliases=["tmodel"])
    async def thread_model(self, ctx: red_commands.Context, *, model_name: str):
        """
        Set the model for the current thread.
        Only works in threads.
        """
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.send("❌ This command can only be used in a thread.")
            return

        # Check if bot can manage this thread (or at least read/write)
        # We assume if it's processing commands, it can.

        # We need the conversation data for this thread.
        # ID is "default" for linear thread history.
        channel_group = self.config.channel(ctx.channel)
        conversations = await channel_group.conversations()

        # Get or create current conversation
        conv_id = "default"
        if conv_id not in conversations:
             # Initialize if not present (although chat usually does this)
             conversations[conv_id] = self.conversation_manager.prepare_for_storage(
                 {"id": conv_id, "messages": [], "model": model_name}
             )
        else:
            # Update existing
            data = self.conversation_manager.process_conversation_data(conversations[conv_id])
            if not data:
                data = {"id": conv_id, "messages": []}

            data["model"] = model_name
            conversations[conv_id] = self.conversation_manager.prepare_for_storage(data)

        await channel_group.conversations.set(conversations)
        await ctx.send(f"✅ Thread model set to: **{model_name}**")

    @red_commands.command(name="setdefaultprompt", aliases=["defprompt"])
    @red_commands.is_owner()
    async def set_default_prompt(self, ctx: red_commands.Context, *, prompt: str):
        """[OWNER ONLY] Set the default system prompt for all users"""
        await self.config.default_system_prompt.set(prompt)
        await ctx.send(
            f"✅ Default system prompt has been set!\n\nPrompt preview:\n```\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}\n```"
        )

    @red_commands.command(name="cleardefaultprompt", aliases=["clrdefprompt"])
    @red_commands.is_owner()
    async def clear_default_prompt(self, ctx: red_commands.Context):
        """[OWNER ONLY] Clear the default system prompt"""
        await self.config.default_system_prompt.set(None)
        await ctx.send("✅ Default system prompt has been cleared.")

    @red_commands.command(name="setprompt")
    async def set_user_prompt(self, ctx: red_commands.Context, *, prompt: str):
        """Set your personal system prompt"""
        await self.config.user(ctx.author).system_prompt.set(prompt)
        await ctx.send(
            f"✅ Your personal system prompt has been set!\n\nPrompt preview:\n```\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}\n```"
        )

    @red_commands.command(name="myprompt")
    async def my_prompt(self, ctx: red_commands.Context):
        """View your current system prompt"""
        user_prompt = await self.config.user(ctx.author).system_prompt()
        default_prompt = await self.config.default_system_prompt()
        lang = await self._get_language(ctx.author.id)

        embed = discord.Embed(
            title=tr(lang, "MY_PROMPT_EMBED_TITLE"), color=discord.Color.blue()
        )

        prompt_files: list[discord.File] = []
        response_text: str | None = None
        show_embed = True

        if user_prompt:
            if len(user_prompt) > 1000:
                prompt_files.append(
                    prompt_to_file(user_prompt, f"personal_prompt_{ctx.author.id}.txt")
                )
                response_text = tr(lang, "MY_PROMPT_ATTACHMENT_PERSONAL")
                show_embed = False
            else:
                embed.add_field(
                    name=tr(lang, "MY_PROMPT_FIELD_PERSONAL"),
                    value=f"```\n{user_prompt}\n```",
                    inline=False,
                )
                embed.add_field(
                    name=tr(lang, "MY_PROMPT_FIELD_STATUS"),
                    value=tr(lang, "MY_PROMPT_STATUS_PERSONAL"),
                    inline=False,
                )
        elif default_prompt:
            if len(default_prompt) > 1000:
                prompt_files.append(
                    prompt_to_file(default_prompt, "default_prompt.txt")
                )
                response_text = tr(lang, "MY_PROMPT_ATTACHMENT_DEFAULT")
                show_embed = False
            else:
                embed.add_field(
                    name=tr(lang, "MY_PROMPT_FIELD_DEFAULT"),
                    value=f"```\n{default_prompt}\n```",
                    inline=False,
                )
                embed.add_field(
                    name=tr(lang, "MY_PROMPT_FIELD_STATUS"),
                    value=tr(lang, "MY_PROMPT_STATUS_DEFAULT"),
                    inline=False,
                )
        else:
            embed.description = tr(lang, "MY_PROMPT_NONE")

        if prompt_files:
            await ctx.send(
                response_text or tr(lang, "MY_PROMPT_ATTACHMENT_GENERIC"),
                files=prompt_files,
            )
        elif show_embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send(tr(lang, "MY_PROMPT_NONE"))

    @red_commands.command(name="clearprompt")
    async def clear_user_prompt(self, ctx: red_commands.Context):
        """Clear your personal system prompt"""
        await self.config.user(ctx.author).system_prompt.set(None)
        await ctx.send("✅ Your personal prompt has been cleared.")

    @red_commands.command(name="purge_my_data", aliases=["purgeme", "resetme"])
    async def purge_user_data(self, ctx: red_commands.Context):
        """Delete all your stored data from the bot"""
        confirm_msg = await ctx.send(
            "⚠️ This will delete ALL your data. React with ✅ to confirm."
        )
        await confirm_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) == "✅"
                and reaction.message.id == confirm_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await self.config.user(ctx.author).clear()
            await ctx.send("✅ Your data has been purged successfully.")
        except TimeoutError:
            await ctx.send("❌ Confirmation timeout.")

    @red_commands.command(name="clear_history", aliases=["clear"])
    async def clear_history(self, ctx: red_commands.Context):
        """Clear the history of the current conversation"""
        if not self.conversation_manager:
            await ctx.send("❌ System not initialized.")
            return

        active_conv_id = await self.context_service.get_active_conversation_id(
            ctx.author.id
        )
        conv = await self._get_conversation(ctx.author.id, active_conv_id)

        if conv is None:
            await ctx.send("⚠️ No active conversation to clear.")
            return

        # Use manager to clear messages
        updated_conv = self.conversation_manager.clear_messages(conv)
        await self._save_conversation(ctx.author.id, active_conv_id, updated_conv)

        # Clear the in-memory cache using ThreadSafeMemory.clear()
        unique_key = f"user:{ctx.author.id}:{active_conv_id}"
        await self.chat_service._clear_conversation_memory(unique_key)

        await ctx.send(
            f"✅ Conversation history cleared for **{updated_conv.get('title', active_conv_id)}**."
        )

    @red_commands.command(
        name="delete_all_conversations", aliases=["delallconvs", "reset_all"]
    )
    async def delete_all_conversations(self, ctx: red_commands.Context):
        """Delete ALL your conversations"""
        confirm_msg = await ctx.send(
            "⚠️ This will delete **ALL** your conversations history. This cannot be undone.\nReact with ✅ to confirm."
        )
        await confirm_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) == "✅"
                and reaction.message.id == confirm_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)

            # Reset conversations
            await self.config.user(ctx.author).conversations.set({})
            # Reset active conversation pointer
            await self.config.user(ctx.author).active_conversation.set("default")

            await ctx.send("✅ All conversations have been deleted.")
        except TimeoutError:
            await ctx.send("❌ Confirmation timeout.")

    @red_commands.command(name="clear_all_histories", hidden=True)
    @red_commands.is_owner()
    async def clear_all_histories(self, ctx: red_commands.Context):
        """[OWNER ONLY] Clear conversation history for ALL users (temporary maintenance command)"""
        confirm_msg = await ctx.send(
            "⚠️ **WARNING**: This will clear ALL conversation history for EVERY user.\n"
            "This cannot be undone. React with ✅ to confirm."
        )
        await confirm_msg.add_reaction("✅")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji) == "✅"
                and reaction.message.id == confirm_msg.id
            )

        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)

            # Get all users
            all_users = await self.config.all_users()
            cleared_count = 0

            for user_id in all_users:
                # Clear conversations in storage
                await self.config.user_from_id(user_id).conversations.set({})
                # Reset active conversation
                await self.config.user_from_id(user_id).active_conversation.set("default")
                cleared_count += 1

            # Clear all in-memory caches
            if self.chat_service:
                self.chat_service._memories.clear()

            await ctx.send(
                f"✅ Successfully cleared conversation history for {cleared_count} users.\n"
                f"In-memory caches also cleared."
            )
        except TimeoutError:
            await ctx.send("❌ Confirmation timeout.")

    async def _create_and_switch_conversation(
        self, user_id: int, title: str | None = None
    ) -> tuple[str, dict[str, Any]]:
        """Helper to create a new conversation and switch to it."""
        if not self.conversation_manager:
            raise RuntimeError("Conversation manager not initialized")

        conv_id = f"conv_{int(time.time())}"

        # Use manager to create
        conv_data = self.conversation_manager.create_conversation(conv_id, title)

        await self._save_conversation(user_id, conv_id, conv_data)
        await self.context_service.set_active_conversation_id(user_id, conv_id)

        return conv_id, conv_data

    @red_commands.command(name="newconv")
    async def new_conversation(self, ctx: red_commands.Context, *, title: str = None):
        """Create a new conversation"""
        if not self.conversation_manager:
            await ctx.send("❌ System not initialized.")
            return

        conv_id, conv_data = await self._create_and_switch_conversation(
            ctx.author.id, title
        )

        await ctx.send(
            f"✅ Created and switched to new conversation: **{conv_data['title']}**\nID: `{conv_id}`"
        )

    @red_commands.command(name="switchconv")
    async def switch_conversation(self, ctx: red_commands.Context, conv_id: str):
        """Switch to a different conversation"""
        conv = await self._get_conversation(ctx.author.id, conv_id)

        if conv is None:
            await ctx.send(f"❌ Conversation `{conv_id}` not found.")
            return

        await self.context_service.set_active_conversation_id(ctx.author.id, conv_id)

        title = conv.get("title", conv_id)
        msg_count = len(conv.get("messages", []))

        await ctx.send(
            f"✅ Switched to conversation: **{title}**\nID: `{conv_id}`\nMessages: {msg_count}"
        )

    @red_commands.command(name="listconv")
    async def list_conversations(self, ctx: red_commands.Context):
        """List all your conversations"""
        if not self.conversation_manager:
            return

        conversations = await self.config.user(ctx.author).conversations()
        active_conv_id = await self.context_service.get_active_conversation_id(
            ctx.author.id
        )

        if not conversations:
            await ctx.send("📭 You don't have any conversations yet.")
            return

        embed = discord.Embed(
            title="💬 Your Conversations",
            description=f"Active conversation: `{active_conv_id}`",
            color=discord.Color.blue(),
        )

        for conv_id, encrypted_data in conversations.items():
            conv_data = self.conversation_manager.process_conversation_data(
                encrypted_data
            )

            if conv_data:
                title = conv_data.get("title", conv_id)
                msg_count = len(conv_data.get("messages", []))
                created = conv_data.get("created_at", 0)

                # Format timestamp
                from datetime import datetime

                created_str = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M")

                status = "🟢 Active" if conv_id == active_conv_id else ""

                embed.add_field(
                    name=f"{status} {title}",
                    value=f"ID: `{conv_id}`\nMessages: {msg_count}\nCreated: {created_str}",
                    inline=False,
                )

        embed.set_footer(text="Use [p]switchconv <id> to switch conversations")
        await ctx.send(embed=embed)

    @red_commands.command(name="deleteconv")
    async def delete_conversation(self, ctx: red_commands.Context, conv_id: str):
        """Delete a conversation"""
        conv = await self._get_conversation(ctx.author.id, conv_id)

        if conv is None:
            await ctx.send(f"❌ Conversation `{conv_id}` not found.")
            return

        active_conv_id = await self.context_service.get_active_conversation_id(
            ctx.author.id
        )
        if conv_id == active_conv_id:
            await ctx.send("❌ Cannot delete the active conversation.")
            return

        title = conv.get("title", conv_id)
        await self._delete_conversation(ctx.author.id, conv_id)
        await ctx.send(f"✅ Conversation **{title}** deleted successfully.")

    @red_commands.command(name="currentconv", aliases=["curr", "cconv"])
    async def current_conversation(self, ctx: red_commands.Context):
        """Show details about your current conversation"""
        active_conv_id = await self.context_service.get_active_conversation_id(
            ctx.author.id
        )
        conv = await self._get_conversation(ctx.author.id, active_conv_id)

        if conv is None:
            conv = await self._get_or_create_conversation(ctx.author.id, active_conv_id)

        title = conv.get("title", active_conv_id)
        messages = conv.get("messages", [])

        embed = discord.Embed(title=f"💬 {title}", color=discord.Color.green())
        embed.add_field(name="ID", value=f"`{active_conv_id}`", inline=True)
        embed.add_field(name="Messages", value=str(len(messages)), inline=True)

        # Show last few messages
        if messages:
            recent = messages[-3:]
            history_text = ""
            for msg in recent:
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                content_preview = msg["content"][:100]
                if len(msg["content"]) > 100:
                    content_preview += "..."
                history_text += f"{role_icon} {content_preview}\n\n"

            embed.add_field(
                name="Recent Messages",
                value=history_text or "No messages yet",
                inline=False,
            )

        await ctx.send(embed=embed)

    @red_commands.hybrid_command(name="conv", aliases=["conversations", "chatmenu"])
    async def conversation_menu(self, ctx: red_commands.Context):
        """Open the interactive conversation management menu"""
        if not self.conversation_manager:
            await ctx.send("❌ System not initialized.")
            return

        lang = await self._get_language(ctx.author.id)
        view = ConversationMenuView(self, ctx, lang)
        embed = await view.refresh_content(None)
        msg = await ctx.send(embed=embed, view=view, ephemeral=True)
        view.message = msg

    @red_commands.command(name="listmodels", aliases=["lm", "models"])
    async def list_models(self, ctx: red_commands.Context, refresh: bool = False):
        """Show available AI models"""
        if not self.chat_service.client:
            await ctx.send("❌ API client not initialized.")
            return

        status_msg = await ctx.send("🔄 Fetching available models...")

        try:
            # Use client to fetch models
            models = await self.chat_service.client.get_models(force_refresh=refresh)

            if not models:
                await status_msg.edit(content="❌ Could not fetch models.")
                return

            embed = discord.Embed(
                title="🤖 Available AI Models",
                description=f"Found **{len(models)}** models",
                color=discord.Color.blue(),
            )

            # Grouping logic
            groups = {"Claude": [], "GPT": [], "Other": []}
            for m in models:
                mid = m["id"].lower()
                if "claude" in mid:
                    groups["Claude"].append(m["id"])
                elif "gpt" in mid:
                    groups["GPT"].append(m["id"])
                else:
                    groups["Other"].append(m["id"])

            for cat, m_list in groups.items():
                if not m_list:
                    continue

                # Sort alphabetically
                m_list.sort()

                # Chunking logic for Discord embed field limit (1024 chars)
                current_chunk = []
                current_len = 0
                part = 1

                for _i, m in enumerate(m_list):
                    entry = f"`{m}`"
                    # Check if adding this entry + newline would exceed safe limit (1000 chars)
                    # or if we are at the last element
                    if current_len + len(entry) + 1 > 1000:
                        # Flush current chunk
                        val = "\n".join(current_chunk)
                        name = (
                            f"{cat} (Part {part})"
                            if (len(m_list) > len(current_chunk) or part > 1)
                            else cat
                        )
                        embed.add_field(name=name, value=val, inline=False)

                        # Start new chunk
                        current_chunk = [entry]
                        current_len = len(entry)
                        part += 1
                    else:
                        current_chunk.append(entry)
                        current_len += len(entry) + 1  # +1 for newline

                # Flush remaining
                if current_chunk:
                    val = "\n".join(current_chunk)
                    # Adjust name for the last part
                    name = f"{cat} (Part {part})" if part > 1 else cat
                    embed.add_field(name=name, value=val, inline=False)

            embed.set_footer(
                text=f"Cached {self.chat_service.client.get_cache_age()}s ago"
            )
            await status_msg.edit(content=None, embed=embed)

        except Exception as e:
            await status_msg.edit(content=f"❌ Error: {str(e)}")

    @red_commands.command(name="searchmodels", aliases=["findm"])
    async def search_models(self, ctx: red_commands.Context, *, query: str):
        """Search for specific models"""
        if not self.chat_service.client:
            await ctx.send("❌ API client not initialized.")
            return

        try:
            matching = await self._get_matching_models(query)

            if not matching:
                await ctx.send(f"No models found matching `{query}`")
                return

            embed = discord.Embed(
                title=f"🔍 Results for '{query}'",
                description="\n".join([f"• `{m}`" for m in matching[:25]]),
                color=discord.Color.green(),
            )
            if len(matching) > 25:
                embed.description += f"\n...and {len(matching) - 25} more"

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @red_commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for messages (DMs, Mentions, or Bot-owned Threads)"""
        # Ignore bot messages
        if message.author.bot:
            return

        # Check if this is a command first for ALL messages (DM or Server)
        # This prevents commands triggering AI responses
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # 1. Listen for DM messages
        is_dm = isinstance(message.channel, discord.DMChannel)

        # Idempotency check
        if message.id in self._processed_messages:
            return
        self._processed_messages.append(message.id)

        # 2. Listen for mentions in Guilds
        # We check if the bot is actually mentioned in the message text or reply
        is_mentioned = self.bot.user in message.mentions

        # 3. Listen for messages in threads owned by the bot
        # This allows conversational replies without requiring mentions
        is_bot_thread = (
            isinstance(message.channel, discord.Thread)
            and message.channel.owner_id == self.bot.user.id
        )

        # Respond if: DM, mentioned, or in a bot-owned thread
        if not is_dm and not is_mentioned and not is_bot_thread:
            # Debug logging for thread ignoring
            if isinstance(message.channel, discord.Thread):
                 log.debug(f"Ignoring thread msg: owner={message.channel.owner_id}, bot={self.bot.user.id}, content={message.content}")
            return

        log.info(f"Processing msg: dm={is_dm}, mention={is_mentioned}, bot_thread={is_bot_thread}")

        # Prepare content
        content = message.content

        # If it's a mention, we might want to strip the mention format so the bot doesn't read its own name
        # But usually LLMs handle names fine. Let's strict it slightly to avoid confusion if it's like "<@123> hello"
        if is_mentioned:
            # Strip the bot's mention from content to keep it clean
            # We can use regex or simple replace
            mention_strings = [f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"]
            for m in mention_strings:
                content = content.replace(m, "").strip()

            # If content is empty after stripping (e.g. just a ping), we might want to ignore or say "Yes?"
            # But let's pass it to processor; maybe user sent an image only.
            if not content and not message.attachments:
                # Just a ping with no content?
                return

        # Check API client readiness (processor handles it, but context is different)
        # Processor handles it.

        # Process
        await self._process_chat_request(message, content)

    @red_commands.command(name="poehubhelp", aliases=["phelp"])
    async def poehub_help(self, ctx: red_commands.Context):
        """Show help for PoeHub commands (localized)."""
        lang = await self._get_language(ctx.author.id)
        prefix = ctx.clean_prefix

        def line(cmd: str, desc: str) -> str:
            return tr(lang, "HELP_LINE", cmd=f"{prefix}{cmd}", desc=desc)

        embed = discord.Embed(
            title=tr(lang, "HELP_TITLE"),
            description=tr(lang, "HELP_DESC"),
            color=discord.Color.blurple(),
        )

        if lang == LANG_ZH_TW:
            embed.add_field(
                name=tr(lang, "HELP_SECTION_CHAT"),
                value="\n".join(
                    [
                        line("ask", "提問並取得回覆（支援圖片）。"),
                    ]
                ),
                inline=False,
            )
            embed.add_field(
                name=tr(lang, "HELP_SECTION_MODELS"),
                value="\n".join(
                    [
                        line("setmodel", "設定你的預設模型。"),
                        line("mymodel", "查看目前模型。"),
                        line("listmodels", "列出可用模型。"),
                        line("searchmodels", "搜尋模型。"),
                    ]
                ),
                inline=False,
            )
            embed.add_field(
                name=tr(lang, "HELP_SECTION_CONV"),
                value="\n".join(
                    [
                        line("conv", "開啟對話管理選單。"),
                        line("newconv", "建立新對話。"),
                        line("switchconv", "切換對話。"),
                        line("listconv", "列出你的對話。"),
                        line("deleteconv", "刪除對話。"),
                        line("clear_history", "清除目前對話紀錄。"),
                    ]
                ),
                inline=False,
            )
            settings_lines = [
                line("config", "開啟設定選單。"),
                line("language", "切換 PoeHub 語言。"),
                line("setprompt", "設定個人提示詞。"),
                line("clearprompt", "清除個人提示詞。"),
                line("purge_my_data", "刪除你的資料。"),
            ]
            if self.allow_dummy_mode:
                settings_lines.append(
                    line("poedummymode", "切換 Dummy API（僅擁有者）。")
                )
            embed.add_field(
                name=tr(lang, "HELP_SECTION_SETTINGS"),
                value="\n".join(settings_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name=tr(lang, "HELP_SECTION_CHAT"),
                value="\n".join(
                    [
                        line("ask", "Ask a question (supports images)."),
                    ]
                ),
                inline=False,
            )
            embed.add_field(
                name=tr(lang, "HELP_SECTION_MODELS"),
                value="\n".join(
                    [
                        line("setmodel", "Set your default model."),
                        line("mymodel", "Show your current model."),
                        line("listmodels", "List available models."),
                        line("searchmodels", "Search models."),
                    ]
                ),
                inline=False,
            )
            embed.add_field(
                name=tr(lang, "HELP_SECTION_CONV"),
                value="\n".join(
                    [
                        line("conv", "Open the conversation menu."),
                        line("newconv", "Create a new conversation."),
                        line("switchconv", "Switch conversations."),
                        line("listconv", "List your conversations."),
                        line("deleteconv", "Delete a conversation."),
                        line("clear_history", "Clear the active conversation history."),
                    ]
                ),
                inline=False,
            )
            settings_lines = [
                line("config", "Open the settings menu."),
                line("language", "Switch PoeHub language."),
                line("setprompt", "Set a personal system prompt."),
                line("clearprompt", "Clear your personal prompt."),
                line("purge_my_data", "Delete your stored data."),
            ]
            if self.allow_dummy_mode:
                settings_lines.append(
                    line("poedummymode", "Toggle Dummy API (owner only).")
                )
            embed.add_field(
                name=tr(lang, "HELP_SECTION_SETTINGS"),
                value="\n".join(settings_lines),
                inline=False,
            )

        embed.set_footer(text=tr(lang, "HELP_LANG_HINT", cmd=f"{prefix}lang"))
        await ctx.send(embed=embed)


    async def run_summary_pipeline(
        self,
        ctx: red_commands.Context | Any,
        channel: discord.TextChannel | Any,
        hours: float,
        language: str | None = None,
        interaction: discord.Interaction | None = None,
    ) -> None:
        """Run the summary pipeline (shared logic)."""
        # 1. Initial response
        # If we have an interaction, we use its followup or edit capability
        initial_msg = None

        if interaction and not interaction.response.is_done():
             # Should not happen if deferred properly, but just in case
             await interaction.response.send_message(f"🔄 Scanning messages from last {hours}h...", ephemeral=False)
             initial_msg = await interaction.original_response()
        elif interaction:
             # Already deferred, use webhook to send followup or edit original if deferred with 'thinking'
             # If deferred with thinking=True, we can edit the original response
             try:
                 initial_msg = await interaction.original_response()
                 await initial_msg.edit(content=f"🔄 Scanning messages from last {hours}h...")
             except Exception:
                 # Fallback
                 initial_msg = await interaction.followup.send(f"🔄 Scanning messages from last {hours}h...", wait=True)
        else:
             initial_msg = await channel.send(f"🔄 Scanning messages from last {hours}h...")

        try:
            # 2. Fetch Messages
            # Ensure we use UTC aware datetime
            from datetime import UTC, datetime, timedelta

            from .models import MessageData

            now = datetime.now(UTC)
            after_time = now - timedelta(hours=hours)

            messages: list[MessageData] = []

            async for message in channel.history(limit=None, after=after_time, oldest_first=True):
                 if message.author.bot:
                     continue
                 if not message.content:
                     continue

                 messages.append(
                     MessageData(
                         author=message.author.display_name,
                         content=message.content,
                         timestamp=message.created_at.strftime("%Y-%m-%d %H:%M"),
                     )
                 )

            if not messages:
                return await initial_msg.edit(content="❌ No messages found in time range.")

            message_count = len(messages)
            await initial_msg.edit(content=f"📝 Found {message_count} messages. Starting summary...")

            # 3. Resolve Language
            if language:
                user_lang_name = language
            else:
                user_id = ctx.author.id if hasattr(ctx, "author") else ctx.user.id
                user_lang_code = await self.context_service.get_user_language(user_id)
                from .core.i18n import LANG_LABELS
                user_lang_name = LANG_LABELS.get(user_lang_code, "English")

            # 4. Resolve Model
            # use ctx.author or ctx.user
            user_obj = ctx.author if hasattr(ctx, "author") else ctx.user
            user_model = await self.config.user(user_obj).model()

            if not self.summarizer:
                 return await initial_msg.edit(content="❌ Summarizer service not available.")

            # 5. Run Service
            final_text = ""
            guild_obj = ctx.guild # works for both Context and Interaction (usually)

            async for update in self.summarizer.summarize_messages(
                messages,
                user_obj.id,
                model=user_model,
                billing_guild=guild_obj,
                language=user_lang_name
            ):
                if update.startswith("RESULT: "):
                    final_text = update[8:]
                elif update.startswith("STATUS: "):
                    try:
                        await initial_msg.edit(content=f"📝 {update[8:]}")
                    except discord.HTTPException:
                        pass

            if not final_text:
                return await initial_msg.edit(content="❌ Summary generation failed (no result).")

            # 6. Create Thread & Reply
            try:
                # thread_name_key = "SUMMARY_THREAD_NAME" # We might want to localize this too eventually
                thread_name = f"Summary: Last {hours}h"

                thread = await initial_msg.create_thread(
                    name=thread_name, auto_archive_duration=60
                )

                # Sleep to propagate
                import asyncio
                await asyncio.sleep(0.5)

                target = thread

                # --- Thread History Initialization ---
                # We need to set the model for this new thread context so replies use it.
                if self.chat_service:
                    scope_group = self.config.channel(target)
                    conv_id = "default"
                    unique_key = f"channel:{target.id}:{conv_id}" # Redbot config key style

                    # 1. Initialize Conversation Data
                    conv_data = {"id": conv_id, "messages": [], "model": user_model}
                    conversations = await scope_group.conversations()

                    if conv_id not in conversations:
                        if self.conversation_manager:
                             conversations[conv_id] = self.conversation_manager.prepare_for_storage(conv_data)
                        else:
                             conversations[conv_id] = conv_data
                        await scope_group.conversations.set(conversations)

                    # 2. Add Trigger Message (User)
                    trigger_text = f"Summarize messages from last {hours} hours."
                    await self.chat_service.add_message_to_conversation(
                        scope_group, conv_id, unique_key, "user", trigger_text
                    )

                    # 3. Add Summary (Assistant)
                    await self.chat_service.add_message_to_conversation(
                        scope_group, conv_id, unique_key, "assistant", final_text
                    )

            except discord.Forbidden:
                # Fallback if cannot create thread
                target = channel

            # Send the final long message
            await self.chat_service.send_split_message(target, final_text)

            await initial_msg.edit(
                content=f"✅ Summary generated for {message_count} messages."
            )

        except Exception as e:
            log.error("Summary pipeline error", exc_info=True)
            await initial_msg.edit(content=f"❌ Error: {str(e)}")


    @red_commands.hybrid_command(name="summary", description="Summarize recent messages.")
    @app_commands.describe(
        hours="Number of hours to look back (default 1)",
        language="Language for the summary (optional)"
    )
    async def summary(self, ctx: red_commands.Context, hours: float = 1.0, language: str = None):
        """Summarize recent messages in this channel."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")

        # Defer if interaction
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=True)

        await self.run_summary_pipeline(ctx, ctx.channel, hours, language, interaction=ctx.interaction)

    # --- Voice Channel Commands ---

    @red_commands.hybrid_command(name="join")
    @red_commands.guild_only()
    async def join_voice(self, ctx: red_commands.Context):
        """Join the voice channel you are currently in."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ You are not in a voice channel.")
            return

        channel = ctx.author.voice.channel

        if ctx.voice_client:
            if ctx.voice_client.channel.id == channel.id:
                await ctx.send(f"✅ Already connected to **{channel.name}**")
                return
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()

        await ctx.send(f"✅ Joined **{channel.name}**")

    @red_commands.hybrid_command(name="vcleave")
    @red_commands.guild_only()
    async def leave_voice(self, ctx: red_commands.Context):
        """Leave the current voice channel."""
        if not ctx.voice_client:
            await ctx.send("❌ I'm not connected to any voice channel.")
            return

        channel_name = ctx.voice_client.channel.name
        self.music_service.clear_queue(ctx.guild.id)
        await ctx.voice_client.disconnect()
        await ctx.send(f"👋 Left **{channel_name}**")

    # --- Music Commands ---

    @red_commands.hybrid_group(name="music", fallback="help")
    @red_commands.guild_only()
    async def music_group(self, ctx: red_commands.Context):
        """Music commands - search, add, play, skip, stop, queue, clear."""
        embed = discord.Embed(
            title="🎵 Music Commands",
            description=(
                "`/music search <query>` - Search for songs\n"
                "`/music add <index>` - Add song to queue\n"
                "`/music play <index>` - Force play a song\n"
                "`/music skip` - Skip current song\n"
                "`/music stop` - Stop playback\n"
                "`/music queue` - View queue\n"
                "`/music clear` - Clear the queue\n"
                "`/music volume [0-100]` - Set volume\n"
                "\n🔁 *Queue loops automatically*"
            ),
            color=discord.Color.purple(),
        )
        await ctx.send(embed=embed, ephemeral=True)

    @music_group.command(name="search")
    @app_commands.describe(query="Song name or artist to search for")
    async def music_search(self, ctx: red_commands.Context, *, query: str):
        """Search for songs."""
        await ctx.defer(ephemeral=True)
        results = await self.music_service.search(query, limit=10)

        if not results:
            await ctx.send("❌ No results found.", ephemeral=True)
            return

        self.music_service.cache_search_results(ctx.author.id, results)

        embed = discord.Embed(
            title=f"🔍 Search: {query}",
            color=discord.Color.blue(),
        )
        lines = []
        for i, song in enumerate(results[:10], 1):
            lines.append(f"`{i}.` **{song['name']}** - {song['artist']} ({song['platform']})")
        embed.description = "\n".join(lines)
        embed.set_footer(text="Use /music add <number> or /music play <number>")

        await ctx.send(embed=embed, ephemeral=True)

    @music_group.command(name="add")
    @app_commands.describe(index="Song number from search results")
    async def music_add(self, ctx: red_commands.Context, index: int):
        """Add a song to the queue. Auto-plays if queue was empty."""
        song = self.music_service.get_cached_result(ctx.author.id, index)
        if not song:
            await ctx.send("❌ Invalid index. Search first with `/music search`.", ephemeral=True)
            return

        # Check if queue was empty before adding
        queue_was_empty = len(self.music_service.get_queue(ctx.guild.id)) == 0
        not_playing = self.music_service.get_now_playing(ctx.guild.id) is None

        position = self.music_service.add_to_queue(ctx.guild.id, song)

        # Auto-play if queue was empty and we're in a voice channel
        if queue_was_empty and not_playing and ctx.voice_client and not ctx.voice_client.is_playing():
            await ctx.defer(ephemeral=True)
            next_song = await self.music_service.play_next(
                ctx.voice_client,
                self._create_after_callback(ctx.guild.id, ctx.voice_client)
            )
            if next_song:
                await ctx.send(f"🎵 Now playing: **{next_song['name']}** - {next_song['artist']}", ephemeral=True)
                return

        await ctx.send(f"✅ Added **{song['name']}** to queue (position {position})", ephemeral=True)

    def _create_after_callback(self, guild_id: int, voice_client: discord.VoiceClient):
        """Create a callback for when a song finishes."""
        def after_callback(error):
            if error:
                log.error(f"Playback error: {error}")
            # Schedule next song
            asyncio.run_coroutine_threadsafe(
                self._play_next_song(guild_id, voice_client),
                self.bot.loop
            )
        return after_callback

    async def _play_next_song(self, guild_id: int, voice_client: discord.VoiceClient):
        """Play the next song in the queue."""
        if not voice_client.is_connected():
            return
        await self.music_service.play_next(
            voice_client,
            self._create_after_callback(guild_id, voice_client)
        )

    @music_group.command(name="play")
    @app_commands.describe(index="Song number from search results")
    async def music_play(self, ctx: red_commands.Context, index: int):
        """Force play a song (removes current, keeps queue)."""
        if not ctx.voice_client:
            await ctx.send("❌ I'm not in a voice channel. Use `/join` first.", ephemeral=True)
            return

        song = self.music_service.get_cached_result(ctx.author.id, index)
        if not song:
            await ctx.send("❌ Invalid index. Search first with `/music search`.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)
        success = await self.music_service.play_song(
            ctx.voice_client,
            song,
            self._create_after_callback(ctx.guild.id, ctx.voice_client)
        )

        if success:
            await ctx.send(f"🎵 Now playing: **{song['name']}** - {song['artist']}", ephemeral=True)
        else:
            await ctx.send("❌ Failed to play the song.", ephemeral=True)

    @music_group.command(name="skip")
    async def music_skip(self, ctx: red_commands.Context):
        """Skip to the next song."""
        if not ctx.voice_client:
            await ctx.send("❌ I'm not in a voice channel.", ephemeral=True)
            return

        if self.music_service.skip(ctx.voice_client):
            await ctx.send("⏭️ Skipped!", ephemeral=True)
        else:
            await ctx.send("❌ Nothing is playing.", ephemeral=True)

    @music_group.command(name="stop")
    async def music_stop(self, ctx: red_commands.Context):
        """Stop playback and clear the queue."""
        if not ctx.voice_client:
            await ctx.send("❌ I'm not in a voice channel.", ephemeral=True)
            return

        self.music_service.clear_queue(ctx.guild.id)
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

        await ctx.send("⏹️ Stopped playback and cleared queue.", ephemeral=True)

    @music_group.command(name="queue")
    async def music_queue(self, ctx: red_commands.Context):
        """View the current queue."""
        queue = self.music_service.get_queue(ctx.guild.id)
        now_playing = self.music_service.get_now_playing(ctx.guild.id)

        embed = discord.Embed(title="🎵 Music Queue", color=discord.Color.purple())

        if now_playing:
            embed.add_field(
                name="Now Playing",
                value=f"**{now_playing['name']}** - {now_playing['artist']}",
                inline=False
            )

        if queue:
            lines = []
            for i, song in enumerate(queue[:10], 1):
                lines.append(f"`{i}.` **{song['name']}** - {song['artist']}")
            if len(queue) > 10:
                lines.append(f"... and {len(queue) - 10} more")
            embed.add_field(name="Up Next", value="\n".join(lines), inline=False)
        elif not now_playing:
            embed.description = "Queue is empty. Use `/music search` to find songs!"

        await ctx.send(embed=embed, ephemeral=True)

    @music_group.command(name="volume")
    @app_commands.describe(level="Volume level (0-100)")
    async def music_volume(self, ctx: red_commands.Context, level: int = None):
        """Set or view the volume (0-100)."""
        if level is None:
            # Show current volume
            current = int(self.music_service.get_volume(ctx.guild.id) * 100)
            await ctx.send(f"🔊 Current volume: **{current}%**", ephemeral=True)
            return

        if level < 0 or level > 100:
            await ctx.send("❌ Volume must be between 0 and 100.", ephemeral=True)
            return

        normalized = self.music_service.set_volume(ctx.guild.id, level)

        # Update current source if playing
        if ctx.voice_client and ctx.voice_client.source:
            if hasattr(ctx.voice_client.source, 'volume'):
                ctx.voice_client.source.volume = normalized

        await ctx.send(f"🔊 Volume set to **{level}%**", ephemeral=True)

    @music_group.command(name="clear")
    async def music_clear(self, ctx: red_commands.Context):
        """Clear the queue (keeps current song playing)."""
        queue_len = len(self.music_service.get_queue(ctx.guild.id))
        self.music_service.clear_queue(ctx.guild.id)
        await ctx.send(f"🗑️ Cleared {queue_len} songs from the queue.", ephemeral=True)


async def setup(bot: Red):
    """Setup function for Red-DiscordBot"""
    await bot.add_cog(PoeHub(bot))
