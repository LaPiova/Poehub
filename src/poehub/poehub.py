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
from typing import Any, Dict, List, Optional, Set, Union

import discord
from redbot.core import Config, commands as red_commands
from redbot.core.bot import Red

from .api_client import get_client, BaseLLMClient
from .conversation_manager import ConversationManager
from .encryption import EncryptionHelper, generate_key
from .i18n import LANG_EN, LANG_LABELS, LANG_ZH_TW, SUPPORTED_LANGS, tr
from .ui.config_view import PoeConfigView
from .ui.conversation_view import ConversationMenuView
from .ui.language_view import LanguageView
from .ui.provider_view import ProviderConfigView


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
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)
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
            "use_dummy_api": False
        }
        
        default_user = {
            "model": "Claude-3.5-Sonnet",
            "conversations": {},  # Dict of conversation_id -> conversation data (encrypted)
            "active_conversation": "default",  # Currently active conversation ID
            "system_prompt": None,  # User's custom system prompt (overrides default)
            "language": LANG_EN,  # Output language for menus/help
        }
        
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        
        self.client: Optional[BaseLLMClient] = None
        self.conversation_manager: Optional[ConversationManager] = None
        self.encryption: Optional[EncryptionHelper] = None
        
        # Initialize encryption on load
        asyncio.create_task(self._initialize())

    async def _get_language(self, user_id: int) -> str:
        """Return the user's language code."""
        lang = await self.config.user_from_id(user_id).language()
        if lang in SUPPORTED_LANGS:
            return lang
        return LANG_EN

    async def _t(self, user_id: int, key: str, **kwargs: object) -> str:
        """Translate a string key for a specific user."""
        lang = await self._get_language(user_id)
        return tr(lang, key, **kwargs)
    
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
            self.conversation_manager = ConversationManager(self.encryption)
            
            # Initialize API client if key exists
            await self._init_client()
            
        except Exception:
            log.exception("Error initializing PoeHub")
    
    async def _init_client(self) -> None:
        """Initialize the LLM client based on configuration."""
        self.client = None
        
        # Check dummy mode
        use_dummy = await self.config.use_dummy_api()
        if use_dummy and not self.allow_dummy_mode:
            await self.config.use_dummy_api.set(False)
            use_dummy = False
            
        if use_dummy:
            self.client = get_client("dummy", "dummy")
            log.info("Initialized Dummy Provider (Offline)")
            return

        # Get configuration
        active_provider = await self.config.active_provider()
        provider_keys = await self.config.provider_keys()
        provider_urls = await self.config.provider_urls()
        
        # Resolve API Key
        api_key = provider_keys.get(active_provider)
        # Fallback to legacy key if not found and provider is Poe (migration path)
        if not api_key:
            legacy_key = await self.config.api_key()
            if legacy_key and active_provider == "poe":
                api_key = legacy_key
                # Auto-migrate
                provider_keys["poe"] = legacy_key
                await self.config.provider_keys.set(provider_keys)
        
        # Resolve Base URL
        base_url = provider_urls.get(active_provider)
        # Fallback to legacy URL
        if not base_url:
             legacy_url = await self.config.base_url()
             if legacy_url and active_provider == "poe":
                 base_url = legacy_url

        if api_key:
            try:
                self.client = get_client(active_provider, api_key, base_url)
                log.info(f"Initialized client for provider: {active_provider}")
            except Exception as e:
                log.error(f"Failed to initialize client for {active_provider}: {e}")
        else:
            log.warning(f"No API key found for active provider: {active_provider}")
    
    def _split_message(self, content: str, max_length: int = 1950) -> List[str]:
        """Split text into Discord-safe chunks.

        Args:
            content: Full content to split.
            max_length: Maximum chunk length. (Discord hard limit is 2000.)

        Returns:
            A list of chunks in send order.
        """
        if len(content) <= max_length:
            return [content]
        
        chunks = []
        remaining = content
        
        while remaining:
            if len(remaining) <= max_length:
                chunks.append(remaining)
                break
            
            # Try to find a good split point
            chunk = remaining[:max_length]
            split_point = max_length
            
            # Priorities for splitting
            split_candidates = [
                ("```\n", 4),       # Code block end
                ("\n\n", 2),        # Paragraph
                ("\n", 1),          # Line
                (". ", 2),          # Sentence
                (" ", 1)            # Word
            ]
            
            for delimiter, offset in split_candidates:
                last_pos = chunk.rfind(delimiter)
                if last_pos > max_length * 0.5:  # Only if it's in the latter half
                    split_point = last_pos + offset
                    break
            
            # Add the chunk
            chunks.append(remaining[:split_point].rstrip())
            remaining = remaining[split_point:].lstrip()
            
            # Add continuation indicator if there's more content
            if remaining and not chunks[-1].endswith("```"):
                chunks[-1] = chunks[-1] + "\n\n*(continued...)*"
            if remaining and len(chunks) > 0:
                remaining = "*(continued)*\n\n" + remaining
        
        return chunks
    
    async def _get_system_prompt(self, user_id: int) -> Optional[str]:
        """Return the effective system prompt for a user."""
        user = discord.Object(id=user_id)
        
        # Check for user's personal prompt first
        user_prompt = await self.config.user(user).system_prompt()
        if user_prompt:
            return user_prompt
        
        # Fall back to default prompt
        return await self.config.default_system_prompt()

    async def _build_model_select_options(self) -> List[discord.SelectOption]:
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
        options: List[discord.SelectOption] = []
        seen: Set[str] = set()

        if self.client:
            try:
                models = await self.client.get_models()
                for model in models:
                    model_id = model.get("id") if isinstance(model, dict) else None
                    if not model_id or model_id in seen:
                        continue
                    seen.add(model_id)
                    options.append(discord.SelectOption(label=model_id[:100], value=model_id))
                    if len(options) >= 25:
                        break
            except Exception as exc:  # noqa: BLE001 - best-effort UI hydration
                log.warning("Could not fetch live model list for config menu: %s", exc)

        if not options:
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
            value=tr(lang, "CONFIG_PROMPT_SET") if user_prompt else tr(lang, "CONFIG_PROMPT_NOT_SET"),
            inline=True,
        )

        return embed
    
    async def _stream_response(
        self, 
        ctx: red_commands.Context, 
        messages: List[Dict[str, Any]], 
        model: str,
        target_channel=None,
        save_to_conv=None
    ):
        """Stream the AI response and update Discord message."""
        if not self.client:
            await ctx.send("❌ API client not initialized. Please set your API key first.")
            return
        
        try:
            # Create initial response message
            if target_channel:
                response_msg = await target_channel.send("🤔 Thinking...")
            else:
                response_msg = await ctx.send("🤔 Thinking...")
            
            accumulated_content = ""
            last_update = time.time()
            
            # Use the new client wrapper for streaming
            stream = self.client.stream_chat(model, messages)
            
            async for content in stream:
                accumulated_content += content
                
                # Update message every 2 seconds to avoid rate limits
                current_time = time.time()
                if current_time - last_update >= 2.0:
                    try:
                        # Discord has a 2000 char limit
                        display_content = accumulated_content[:1900]
                        if len(accumulated_content) > 1900:
                            display_content += "\n...(truncated)"
                        
                        await response_msg.edit(content=display_content)
                        last_update = current_time
                    except discord.HTTPException:
                        pass  # Ignore rate limit errors during streaming
            
            # Final update
            if accumulated_content:
                # Split into chunks intelligently (Discord 2000 char limit)
                chunks = self._split_message(accumulated_content)
                
                # Update first message
                await response_msg.edit(content=chunks[0])
                
                # Send additional chunks if needed
                for chunk in chunks[1:]:
                    if target_channel:
                        await target_channel.send(chunk)
                    else:
                        await ctx.send(chunk)
                
                # Save assistant response to conversation
                if save_to_conv:
                    user_id, conv_id = save_to_conv
                    await self._add_message_to_conversation(user_id, conv_id, "assistant", accumulated_content)
            else:
                await response_msg.edit(content="❌ No response received from API.")
        
        except Exception as exc:  # noqa: BLE001 - surface errors to user
            error_msg = f"❌ Error communicating with Poe API: {exc}"
            log.exception("Error communicating with Poe API")
            await ctx.send(error_msg)
    
    # --- Conversation Management Methods (Refactored) ---
    
    async def _get_conversation(self, user_id: int, conv_id: str) -> Optional[Dict[str, Any]]:
        """Get a conversation by ID for a user"""
        if not self.conversation_manager:
            return None
            
        conversations = await self.config.user_from_id(user_id).conversations()
        if conv_id in conversations:
            return self.conversation_manager.process_conversation_data(conversations[conv_id])
        return None
    
    async def _save_conversation(self, user_id: int, conv_id: str, conv_data: Dict[str, Any]):
        """Save a conversation for a user (encrypted)"""
        if not self.conversation_manager:
            return
            
        conversations = await self.config.user_from_id(user_id).conversations()
        
        # Use manager to encrypt
        conversations[conv_id] = self.conversation_manager.prepare_for_storage(conv_data)
        
        await self.config.user_from_id(user_id).conversations.set(conversations)
    
    async def _delete_conversation(self, user_id: int, conv_id: str) -> bool:
        """Delete a conversation"""
        conversations = await self.config.user_from_id(user_id).conversations()
        
        if conv_id in conversations:
            del conversations[conv_id]
            await self.config.user_from_id(user_id).conversations.set(conversations)
            return True
        return False
    
    async def _get_active_conversation_id(self, user_id: int) -> str:
        """Get the active conversation ID for a user"""
        conv_id = await self.config.user_from_id(user_id).active_conversation()
        return conv_id or "default"
    
    async def _set_active_conversation(self, user_id: int, conv_id: str):
        """Set the active conversation for a user"""
        await self.config.user_from_id(user_id).active_conversation.set(conv_id)
    
    async def _get_or_create_conversation(self, user_id: int, conv_id: str) -> Dict[str, Any]:
        """Get or create a conversation"""
        if not self.conversation_manager:
            raise RuntimeError("Conversation manager not initialized")
            
        conv = await self._get_conversation(user_id, conv_id)
        
        if conv is None:
            conv = self.conversation_manager.create_conversation(conv_id)
            await self._save_conversation(user_id, conv_id, conv)
        
        return conv
    
    async def _add_message_to_conversation(
        self,
        user_id: int,
        conv_id: str,
        role: str,
        content: Union[str, List[Dict[str, Any]]],
    ) -> None:
        """Add a message to a conversation."""
        if not self.conversation_manager:
            return
            
        conv = await self._get_or_create_conversation(user_id, conv_id)
        
        # Update using manager logic
        updated_conv = self.conversation_manager.add_message(conv, role, content)
        
        await self._save_conversation(user_id, conv_id, updated_conv)
    
    async def _get_conversation_messages(self, user_id: int, conv_id: str) -> List[Dict[str, str]]:
        """Get messages for API call"""
        if not self.conversation_manager:
            return []
            
        conv = await self._get_conversation(user_id, conv_id)
        return self.conversation_manager.get_api_messages(conv)
    
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
            color=discord.Color.blue()
        )
        embed.add_field(name="Active Provider", value=f"**{active}**", inline=True)
        embed.add_field(name="Dummy Mode", value="ON" if dummy else "OFF", inline=True)
        
        # Check key
        if active != "dummy":
            keys = await self.config.provider_keys()
            has_key = bool(keys.get(active))
            embed.add_field(name="API Key Set", value="✅ Yes" if has_key else "❌ No", inline=True)

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
        valid_providers = ["poe", "openai", "anthropic", "google", "deepseek", "openrouter", "dummy"]
        
        if provider not in valid_providers:
            await ctx.send(f"❌ Invalid provider. Choose from: {', '.join(valid_providers)}")
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
        
        # Check if key needs to be set
        if not self.client and provider != "dummy":
             msg += f"\n⚠️ **Warning**: Client not initialized. You probably need to set an API key for {provider}.\nUse `[p]setapikey {provider} <key>`."
        
        await ctx.send(msg)

    @red_commands.command(name="setapikey", aliases=["setkey"])
    @red_commands.is_owner()
    async def set_provider_key(self, ctx: red_commands.Context, provider: str, api_key: str):
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
        except:
            pass
            
        await ctx.send(f"✅ API key for **{provider}** updated successfully! (Message deleted)")

    @red_commands.command(name="poeapikey", aliases=["pkey"])
    @red_commands.is_owner()
    async def set_api_key(self, ctx: red_commands.Context, api_key: str):
        """
        Set the Poe API key (Legacy alias).
        Equivalent to: [p]setkey poe <key>
        """
        await self.set_provider_key(ctx, "poe", api_key)

    @red_commands.command(name="poedummymode", aliases=["pdummy", "dummy"])
    @red_commands.is_owner()
    async def toggle_dummy_mode(self, ctx: red_commands.Context, *, state: Optional[str] = None):
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
            await ctx.send("✅ Dummy API mode enabled. PoeHub will return local stub responses for debugging.")
        else:
            await ctx.send("✅ Dummy API mode disabled. Remember to set a valid Poe API key with `[p]poeapikey`.")

    @red_commands.command(name="poeconfig", aliases=["config", "menu"])
    async def open_config_menu(self, ctx: red_commands.Context):
        """Open the interactive configuration panel"""
        lang = await self._get_language(ctx.author.id)
        model_options = await self._build_model_select_options()
        is_owner = await self.bot.is_owner(ctx.author)
        dummy_state = await self.config.use_dummy_api() if (is_owner and self.allow_dummy_mode) else False

        embed = await self._build_config_embed(ctx, is_owner, dummy_state, lang)

        view = PoeConfigView(
            cog=self,
            ctx=ctx,
            model_options=model_options,
            owner_mode=is_owner,
            dummy_state=dummy_state,
            lang=lang,
        )

        msg = await ctx.send(embed=embed, view=view)
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
        embed.add_field(name=tr(lang, "LANG_CURRENT"), value=f"`{current}`", inline=False)
        view = LanguageView(self, ctx, lang)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
    
    @red_commands.command(name="ask")
    async def ask(self, ctx: red_commands.Context, *, query: str):
        """
        Ask a question to Poe AI (with conversation context)
        Usage: [p]ask <your question>
        """
        if not self.client:
            await ctx.send("❌ API key not set. Bot owner must use `[p]poeapikey` first.")
            return
        
        # Get user's preferences
        user_model = await self.config.user(ctx.author).model()
        active_conv_id = await self._get_active_conversation_id(ctx.author.id)
        
        # Load conversation history
        history = await self._get_conversation_messages(ctx.author.id, active_conv_id)
        
        # Check for image attachments
        image_urls = []
        if ctx.message.attachments:
            for attachment in ctx.message.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    image_urls.append(attachment.url)
        
        # Format new message
        if image_urls:
            content = self.client.format_image_message(query, image_urls)
            new_message = {"role": "user", "content": content}
            # Save structured content with images to conversation history
            await self._add_message_to_conversation(ctx.author.id, active_conv_id, "user", content)
        else:
            new_message = {"role": "user", "content": query}
            # Save text-only content to conversation history
            await self._add_message_to_conversation(ctx.author.id, active_conv_id, "user", query)
        
        # Combine history with new message
        messages = history + [new_message]
        
        # Get system prompt and prepend if exists
        system_prompt = await self._get_system_prompt(ctx.author.id)
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        # Stream the response
        await self._stream_response(ctx, messages, user_model, None, 
                                    save_to_conv=(ctx.author.id, active_conv_id))
    
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
    
    @red_commands.command(name="setdefaultprompt", aliases=["defprompt"])
    @red_commands.is_owner()
    async def set_default_prompt(self, ctx: red_commands.Context, *, prompt: str):
        """[OWNER ONLY] Set the default system prompt for all users"""
        await self.config.default_system_prompt.set(prompt)
        await ctx.send(f"✅ Default system prompt has been set!\n\nPrompt preview:\n```\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}\n```")
    
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
        await ctx.send(f"✅ Your personal system prompt has been set!\n\nPrompt preview:\n```\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}\n```")
    
    @red_commands.command(name="myprompt")
    async def my_prompt(self, ctx: red_commands.Context):
        """View your current system prompt"""
        user_prompt = await self.config.user(ctx.author).system_prompt()
        default_prompt = await self.config.default_system_prompt()
        
        embed = discord.Embed(
            title="📝 Your System Prompt 您的系統提示詞",
            color=discord.Color.blue()
        )
        
        if user_prompt:
            embed.add_field(
                name="🔷 Personal Prompt 個人提示詞",
                value=f"```\n{user_prompt[:1000]}{'...' if len(user_prompt) > 1000 else ''}\n```",
                inline=False
            )
            embed.add_field(name="ℹ️ Status 狀態", value="Using your personal prompt", inline=False)
        elif default_prompt:
            embed.add_field(
                name="🔹 Default Prompt 預設提示詞",
                value=f"```\n{default_prompt[:1000]}{'...' if len(default_prompt) > 1000 else ''}\n```",
                inline=False
            )
            embed.add_field(name="ℹ️ Status 狀態", value="Using default prompt", inline=False)
        else:
            embed.description = "No system prompt set"
        
        await ctx.send(embed=embed)
    
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
            return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == confirm_msg.id
        
        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            await self.config.user(ctx.author).clear()
            await ctx.send("✅ Your data has been purged successfully.")
        except asyncio.TimeoutError:
            await ctx.send("❌ Confirmation timeout.")
    
    @red_commands.command(name="clear_history", aliases=["clear"])
    async def clear_history(self, ctx: red_commands.Context):
        """Clear the history of the current conversation"""
        if not self.conversation_manager:
            await ctx.send("❌ System not initialized.")
            return

        active_conv_id = await self._get_active_conversation_id(ctx.author.id)
        conv = await self._get_conversation(ctx.author.id, active_conv_id)
        
        if conv is None:
            await ctx.send("⚠️ No active conversation to clear.")
            return

        # Use manager to clear messages
        updated_conv = self.conversation_manager.clear_messages(conv)
        await self._save_conversation(ctx.author.id, active_conv_id, updated_conv)
        
        await ctx.send(f"✅ Conversation history cleared for **{updated_conv.get('title', active_conv_id)}**.")

    @red_commands.command(name="delete_all_conversations", aliases=["delallconvs", "reset_all"])
    async def delete_all_conversations(self, ctx: red_commands.Context):
        """Delete ALL your conversations"""
        confirm_msg = await ctx.send(
            "⚠️ This will delete **ALL** your conversations history. This cannot be undone.\nReact with ✅ to confirm."
        )
        await confirm_msg.add_reaction("✅")
        
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == confirm_msg.id
        
        try:
            await self.bot.wait_for("reaction_add", timeout=30.0, check=check)
            
            # Reset conversations
            await self.config.user(ctx.author).conversations.set({})
            # Reset active conversation pointer
            await self.config.user(ctx.author).active_conversation.set("default")
            
            await ctx.send("✅ All conversations have been deleted.")
        except asyncio.TimeoutError:
            await ctx.send("❌ Confirmation timeout.")

    @red_commands.command(name="newconv")
    async def new_conversation(self, ctx: red_commands.Context, *, title: str = None):
        """Create a new conversation"""
        if not self.conversation_manager:
            await ctx.send("❌ System not initialized.")
            return

        conv_id = f"conv_{int(time.time())}"
        
        # Use manager to create
        conv_data = self.conversation_manager.create_conversation(conv_id, title)
        
        await self._save_conversation(ctx.author.id, conv_id, conv_data)
        await self._set_active_conversation(ctx.author.id, conv_id)
        
        await ctx.send(f"✅ Created and switched to new conversation: **{conv_data['title']}**\nID: `{conv_id}`")
    
    @red_commands.command(name="switchconv")
    async def switch_conversation(self, ctx: red_commands.Context, conv_id: str):
        """Switch to a different conversation"""
        conv = await self._get_conversation(ctx.author.id, conv_id)
        
        if conv is None:
            await ctx.send(f"❌ Conversation `{conv_id}` not found.")
            return
        
        await self._set_active_conversation(ctx.author.id, conv_id)
        
        title = conv.get("title", conv_id)
        msg_count = len(conv.get("messages", []))
        
        await ctx.send(f"✅ Switched to conversation: **{title}**\nID: `{conv_id}`\nMessages: {msg_count}")
    
    @red_commands.command(name="listconv")
    async def list_conversations(self, ctx: red_commands.Context):
        """List all your conversations"""
        if not self.conversation_manager:
            return

        conversations = await self.config.user(ctx.author).conversations()
        active_conv_id = await self._get_active_conversation_id(ctx.author.id)
        
        if not conversations:
            await ctx.send("📭 You don't have any conversations yet.")
            return
        
        embed = discord.Embed(
            title="💬 Your Conversations",
            description=f"Active conversation: `{active_conv_id}`",
            color=discord.Color.blue()
        )
        
        for conv_id, encrypted_data in conversations.items():
            conv_data = self.conversation_manager.process_conversation_data(encrypted_data)
            
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
                    inline=False
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
        
        active_conv_id = await self._get_active_conversation_id(ctx.author.id)
        if conv_id == active_conv_id:
            await ctx.send("❌ Cannot delete the active conversation.")
            return
        
        title = conv.get("title", conv_id)
        await self._delete_conversation(ctx.author.id, conv_id)
        await ctx.send(f"✅ Conversation **{title}** deleted successfully.")
    
    @red_commands.command(name="currentconv", aliases=["curr", "cconv"])
    async def current_conversation(self, ctx: red_commands.Context):
        """Show details about your current conversation"""
        active_conv_id = await self._get_active_conversation_id(ctx.author.id)
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
            
            embed.add_field(name="Recent Messages", value=history_text or "No messages yet", inline=False)
        
        await ctx.send(embed=embed)

    @red_commands.command(name="conv", aliases=["conversations", "chatmenu"])
    async def conversation_menu(self, ctx: red_commands.Context):
        """Open the interactive conversation management menu"""
        if not self.conversation_manager:
            await ctx.send("❌ System not initialized.")
            return

        lang = await self._get_language(ctx.author.id)
        view = ConversationMenuView(self, ctx, lang)
        embed = await view.refresh_content(None)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
    
    @red_commands.command(name="listmodels", aliases=["lm", "models"])
    async def list_models(self, ctx: red_commands.Context, refresh: bool = False):
        """Show available AI models"""
        if not self.client:
            await ctx.send("❌ API client not initialized.")
            return
        
        status_msg = await ctx.send("🔄 Fetching available models...")
        
        try:
            # Use client to fetch models
            models = await self.client.get_models(force_refresh=refresh)
            
            if not models:
                await status_msg.edit(content="❌ Could not fetch models.")
                return
            
            embed = discord.Embed(
                title="🤖 Available AI Models",
                description=f"Found **{len(models)}** models",
                color=discord.Color.blue()
            )
            
            # Grouping logic
            groups = {"Claude": [], "GPT": [], "Other": []}
            for m in models:
                mid = m['id'].lower()
                if "claude" in mid: groups["Claude"].append(m['id'])
                elif "gpt" in mid: groups["GPT"].append(m['id'])
                else: groups["Other"].append(m['id'])
            
            for cat, m_list in groups.items():
                if not m_list:
                    continue
                
                # Sort alphabetically
                m_list.sort()
                
                # Chunking logic for Discord embed field limit (1024 chars)
                current_chunk = []
                current_len = 0
                part = 1
                
                for i, m in enumerate(m_list):
                    entry = f"`{m}`"
                    # Check if adding this entry + newline would exceed safe limit (1000 chars)
                    # or if we are at the last element
                    if current_len + len(entry) + 1 > 1000:
                        # Flush current chunk
                        val = "\n".join(current_chunk)
                        name = f"{cat} (Part {part})" if (len(m_list) > len(current_chunk) or part > 1) else cat
                        embed.add_field(name=name, value=val, inline=False)
                        
                        # Start new chunk
                        current_chunk = [entry]
                        current_len = len(entry)
                        part += 1
                    else:
                        current_chunk.append(entry)
                        current_len += len(entry) + 1 # +1 for newline

                # Flush remaining
                if current_chunk:
                    val = "\n".join(current_chunk)
                    # Adjust name for the last part
                    name = f"{cat} (Part {part})" if part > 1 else cat
                    embed.add_field(name=name, value=val, inline=False)
            
            embed.set_footer(text=f"Cached {self.client.get_cache_age()}s ago")
            await status_msg.edit(content=None, embed=embed)
            
        except Exception as e:
            await status_msg.edit(content=f"❌ Error: {str(e)}")

    @red_commands.command(name="searchmodels", aliases=["findm"])
    async def search_models(self, ctx: red_commands.Context, *, query: str):
        """Search for specific models"""
        if not self.client:
            await ctx.send("❌ API client not initialized.")
            return
        
        try:
            models = await self.client.get_models()
            query_lower = query.lower()
            matching = [m['id'] for m in models if query_lower in m['id'].lower()]
            
            if not matching:
                await ctx.send(f"No models found matching `{query}`")
                return
            
            embed = discord.Embed(
                title=f"🔍 Results for '{query}'",
                description="\n".join([f"• `{m}`" for m in matching[:25]]),
                color=discord.Color.green()
            )
            if len(matching) > 25:
                embed.description += f"\n...and {len(matching)-25} more"
            
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"❌ Error: {str(e)}")

    @red_commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listen for DM messages"""
        if message.author.bot or not isinstance(message.channel, discord.DMChannel):
            return
            
        ctx = await self.bot.get_context(message)
        if ctx.valid or not self.client:
            return
            
        try:
            user_model = await self.config.user(message.author).model()
            active_conv_id = await self._get_active_conversation_id(message.author.id)
            
            history = await self._get_conversation_messages(message.author.id, active_conv_id)
            
            # Format message
            image_urls = []
            if message.attachments:
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith("image/"):
                        image_urls.append(attachment.url)
            
            if image_urls:
                content = self.client.format_image_message(message.content, image_urls)
                new_msg = {"role": "user", "content": content}
                # Save structured content with images to conversation history
                await self._add_message_to_conversation(message.author.id, active_conv_id, "user", content)
            else:
                new_msg = {"role": "user", "content": message.content}
                # Save text-only content to conversation history
                await self._add_message_to_conversation(message.author.id, active_conv_id, "user", message.content)
            messages = history + [new_msg]
            
            system_prompt = await self._get_system_prompt(message.author.id)
            if system_prompt:
                messages = [{"role": "system", "content": system_prompt}] + messages
            
            response_msg = await message.channel.send("🤔 Thinking...")
            
            # Stream response (DM version)
            accumulated_content = ""
            last_update = time.time()
            stream = self.client.stream_chat(user_model, messages)
            
            async for content in stream:
                accumulated_content += content
                if time.time() - last_update >= 2.0:
                    try:
                        await response_msg.edit(content=accumulated_content[:1900] + "...")
                        last_update = time.time()
                    except:
                        pass
            
            if accumulated_content:
                chunks = self._split_message(accumulated_content)
                await response_msg.edit(content=chunks[0])
                for chunk in chunks[1:]:
                    await message.channel.send(chunk)
                await self._add_message_to_conversation(message.author.id, active_conv_id, "assistant", accumulated_content)
            else:
                await response_msg.edit(content="❌ No response.")
                
        except Exception:
            log.exception("DM handler error")
            await message.channel.send("❌ An error occurred.")

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
                settings_lines.append(line("poedummymode", "切換 Dummy API（僅擁有者）。"))
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
                settings_lines.append(line("poedummymode", "Toggle Dummy API (owner only)."))
            embed.add_field(
                name=tr(lang, "HELP_SECTION_SETTINGS"),
                value="\n".join(settings_lines),
                inline=False,
            )

        embed.set_footer(text=tr(lang, "HELP_LANG_HINT", cmd=f"{prefix}lang"))
        await ctx.send(embed=embed)


async def setup(bot: Red):
    """Setup function for Red-DiscordBot"""
    await bot.add_cog(PoeHub(bot))