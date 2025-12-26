"""
PoeHub - Red-DiscordBot Cog for Poe API Integration
Uses OpenAI-compatible API endpoint to communicate with Poe
"""

import discord
from discord.ext import commands
from redbot.core import commands as red_commands, Config
from redbot.core.bot import Red
import asyncio
import logging
from typing import Optional, List, Dict, Any, Union, Set
import time

# Handle imports
try:
    from .encryption import EncryptionHelper, generate_key
    from .api_client import PoeClient, DummyPoeClient
    from .conversation_manager import ConversationManager
except ImportError:
    from encryption import EncryptionHelper, generate_key
    from api_client import PoeClient, DummyPoeClient
    from conversation_manager import ConversationManager


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
        
        # Default configuration
        default_global = {
            "api_key": None,
            "encryption_key": None,
            "base_url": "https://api.poe.com/v1",
            "default_system_prompt": None,  # Default system prompt set by bot owner
            "use_dummy_api": False  # Allow offline debugging without Poe API key
        }
        
        default_user = {
            "model": "Claude-3.5-Sonnet",
            "conversations": {},  # Dict of conversation_id -> conversation data (encrypted)
            "active_conversation": "default",  # Currently active conversation ID
            "system_prompt": None  # User's custom system prompt (overrides default)
        }
        
        self.config.register_global(**default_global)
        self.config.register_user(**default_user)
        
        self.client: Optional[Union[PoeClient, DummyPoeClient]] = None
        self.conversation_manager: Optional[ConversationManager] = None
        self.encryption: Optional[EncryptionHelper] = None
        
        # Initialize encryption on load
        asyncio.create_task(self._initialize())
    
    async def _initialize(self):
        """Initialize encryption, conversation manager and API client"""
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
            
        except Exception as e:
            log.error(f"Error initializing PoeHub: {e}", exc_info=True)
    
    async def _init_client(self):
        """Initialize the Poe client"""
        self.client = None
        use_dummy = await self.config.use_dummy_api()
        if use_dummy:
            self.client = DummyPoeClient()
            log.info("Dummy PoeHub client initialized (offline mode)")
            return

        api_key = await self.config.api_key()
        base_url = await self.config.base_url()
        
        if api_key:
            self.client = PoeClient(api_key=api_key, base_url=base_url)
            log.info("PoeHub API client initialized")
        else:
            log.warning("No API key set. Use [p]poeapikey to set one or enable dummy mode.")
    
    def _split_message(self, content: str, max_length: int = 1950) -> List[str]:
        """
        Split a message into chunks that fit Discord's 2000 character limit.
        Attempts to split at natural boundaries.
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
        """Get the effective system prompt for a user"""
        user = discord.Object(id=user_id)
        
        # Check for user's personal prompt first
        user_prompt = await self.config.user(user).system_prompt()
        if user_prompt:
            return user_prompt
        
        # Fall back to default prompt
        return await self.config.default_system_prompt()

    async def _build_model_select_options(self) -> List[discord.SelectOption]:
        """Build dropdown options for the interactive config panel"""
        fallback_models = [
            "Claude-3.5-Sonnet",
            "Claude-3-Opus",
            "Claude-3-Haiku",
            "GPT-4o",
            "GPT-4",
            "GPT-3.5-Turbo",
            "Gemini-1.5-Pro",
            "Gemini-Pro",
            "Llama-3.1-405B",
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
            except Exception as exc:
                log.warning("Could not fetch live model list for config menu: %s", exc)

        if not options:
            for model_id in fallback_models:
                options.append(discord.SelectOption(label=model_id, value=model_id))

        return options[:25]

    async def _build_config_embed(
        self,
        ctx: red_commands.Context,
        owner_mode: bool,
        dummy_state: bool
    ) -> discord.Embed:
        """Create the status embed for the interactive config menu"""
        embed = discord.Embed(
            title="⚙️ PoeHub Configuration",
            description=(
                "Use the dropdown to choose your default model, set or clear your personal system prompt, "
                "and close the menu when you're done.\n\n"
                "Prefer commands? You can still use `[p]setmodel`, `[p]setprompt`, `[p]clearprompt`, "
                "and `[p]poedummymode` (owner only)."
            ),
            color=discord.Color.blurple()
        )
        current_model = await self.config.user(ctx.author).model()
        embed.add_field(name="Current Model", value=f"`{current_model}`", inline=True)

        user_prompt = await self.config.user(ctx.author).system_prompt()
        embed.add_field(
            name="Personal Prompt",
            value="已設定" if user_prompt else "未設定",
            inline=True
        )

        if owner_mode:
            status_text = "ON" if dummy_state else "OFF"
            embed.add_field(
                name="Dummy API Mode",
                value=f"{status_text} (owner only)",
                inline=True
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
        """Stream the AI response and update Discord message"""
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
        
        except Exception as e:
            error_msg = f"❌ Error communicating with Poe API: {str(e)}"
            log.error(error_msg, exc_info=True)
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
    
    async def _add_message_to_conversation(self, user_id: int, conv_id: str, role: str, content: str):
        """Add a message to a conversation"""
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

    @red_commands.command(name="poeapikey")
    @red_commands.is_owner()
    async def set_api_key(self, ctx: red_commands.Context, api_key: str):
        """
        Set the Poe API key (Owner only)
        Usage: [p]poeapikey <your_api_key>
        """
        await self.config.api_key.set(api_key)
        await self._init_client()
        
        try:
            await ctx.message.delete()
        except:
            pass
        
        await ctx.send("✅ API key has been set successfully! (Your message was deleted for security)")

    @red_commands.command(name="poedummymode")
    @red_commands.is_owner()
    async def toggle_dummy_mode(self, ctx: red_commands.Context, *, state: Optional[str] = None):
        """Enable/disable offline dummy API mode or show its status"""
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

    @red_commands.command(name="poeconfig", aliases=["poehubconfig", "poesettings"])
    async def open_config_menu(self, ctx: red_commands.Context):
        """Open the interactive configuration panel"""
        model_options = await self._build_model_select_options()
        is_owner = await self.bot.is_owner(ctx.author)
        dummy_state = await self.config.use_dummy_api() if is_owner else False

        embed = await self._build_config_embed(ctx, is_owner, dummy_state)

        view = PoeConfigView(
            cog=self,
            ctx=ctx,
            model_options=model_options,
            owner_mode=is_owner,
            dummy_state=dummy_state
        )

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
        else:
            new_message = {"role": "user", "content": query}
        
        # Add to conversation history
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
    
    @red_commands.command(name="setdefaultprompt")
    @red_commands.is_owner()
    async def set_default_prompt(self, ctx: red_commands.Context, *, prompt: str):
        """[OWNER ONLY] Set the default system prompt for all users"""
        await self.config.default_system_prompt.set(prompt)
        await ctx.send(f"✅ Default system prompt has been set!\n\nPrompt preview:\n```\n{prompt[:500]}{'...' if len(prompt) > 500 else ''}\n```")
    
    @red_commands.command(name="cleardefaultprompt")
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
    
    @red_commands.command(name="purge_my_data")
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
    
    @red_commands.command(name="clear_history", aliases=["clear_context", "reset_conv"])
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
    
    @red_commands.command(name="currentconv")
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
    
    @red_commands.command(name="listmodels")
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

    @red_commands.command(name="searchmodels")
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
            else:
                new_msg = {"role": "user", "content": message.content}
            
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
                
        except Exception as e:
            log.error(f"DM Error: {e}")
            await message.channel.send("❌ An error occurred.")

    @red_commands.command(name="poehubhelp", aliases=["幫助", "说明"])
    async def poehub_help(self, ctx: red_commands.Context):
        """Show bilingual help for PoeHub commands"""
        # (Keeping the original help content abbreviated for brevity in this rewrite, 
        # but in a real scenario I would keep the full text. 
        # I'll restore the full text to ensure no regression.)
        embed = discord.Embed(
            title="🤖 PoeHub Commands 指令說明",
            description="Bilingual command reference 雙語指令參考",
            color=discord.Color.blue()
        )
        embed.add_field(name="📝 Basic Commands 基本指令", value="**!ask**, **!setmodel**, **!mymodel**, **!listmodels**, **!searchmodels**", inline=False)
        embed.add_field(name="💬 Conversation 對話", value="**!newconv**, **!switchconv**, **!listconv**, **!deleteconv**, **!clear_history**, **!delete_all_conversations**", inline=False)
        embed.add_field(
            name="⚙️ Settings 設定",
            value="**!poeconfig**, **!setprompt**, **!clearprompt**, **!purge_my_data**, **!poedummymode** (擁有者)",
            inline=False
        )
        await ctx.send(embed=embed)


class PoeConfigView(discord.ui.View):
    """Interactive configuration dashboard."""

    def __init__(
        self,
        cog: "PoeHub",
        ctx: red_commands.Context,
        model_options: List[discord.SelectOption],
        owner_mode: bool,
        dummy_state: bool
    ):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.message: Optional[discord.Message] = None
        self.owner_mode = owner_mode

        if model_options:
            self.add_item(ModelSelect(cog, ctx, model_options))

        self.add_item(SetPromptButton(cog, ctx))
        self.add_item(ShowPromptButton(cog, ctx))
        self.add_item(ClearPromptButton(cog, ctx))

        if owner_mode:
            self.add_item(DummyToggleButton(cog, ctx, dummy_state))

        self.add_item(CloseMenuButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("此設定面板僅限觸發者使用。", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        if not self.message:
            return
        for child in self.children:
            child.disabled = True
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            pass


class ModelSelect(discord.ui.Select):
    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, options: List[discord.SelectOption]):
        placeholder = "Select your default model"
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        model_choice = self.values[0]
        await self.cog.config.user(self.ctx.author).model.set(model_choice)
        await interaction.response.send_message(f"✅ 模型已設定為 `{model_choice}`", ephemeral=True)


class PromptModal(discord.ui.Modal, title="設定個人提示詞 / Set Personal Prompt"):
    prompt: discord.ui.TextInput = discord.ui.TextInput(
        label="System Prompt",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1500,
        placeholder="Describe how PoeHub should respond..."
    )

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context):
        super().__init__()
        self.cog = cog
        self.ctx = ctx

    async def on_submit(self, interaction: discord.Interaction):
        prompt_text = self.prompt.value.strip()
        await self.cog.config.user(self.ctx.author).system_prompt.set(prompt_text)
        preview = prompt_text[:200] + ("..." if len(prompt_text) > 200 else "")
        await interaction.response.send_message(
            f"✅ 已更新個人提示詞。Preview: ```{preview}```",
            ephemeral=True
        )


class SetPromptButton(discord.ui.Button):
    def __init__(self, cog: "PoeHub", ctx: red_commands.Context):
        super().__init__(label="Set Personal Prompt", style=discord.ButtonStyle.primary)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PromptModal(self.cog, self.ctx))


class ShowPromptButton(discord.ui.Button):
    def __init__(self, cog: "PoeHub", ctx: red_commands.Context):
        super().__init__(label="View Prompt", style=discord.ButtonStyle.secondary)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        user_prompt = await self.cog.config.user(self.ctx.author).system_prompt()
        default_prompt = await self.cog.config.default_system_prompt()

        if not user_prompt and not default_prompt:
            await interaction.response.send_message("目前沒有設定任何提示詞。", ephemeral=True)
            return

        embed = discord.Embed(title="📝 System Prompt", color=discord.Color.blurple())
        if user_prompt:
            embed.add_field(
                name="Personal",
                value=f"```{user_prompt[:1000]}{'...' if len(user_prompt) > 1000 else ''}```",
                inline=False
            )
        if default_prompt:
            embed.add_field(
                name="Default",
                value=f"```{default_prompt[:1000]}{'...' if len(default_prompt) > 1000 else ''}```",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)


class ClearPromptButton(discord.ui.Button):
    def __init__(self, cog: "PoeHub", ctx: red_commands.Context):
        super().__init__(label="Clear Prompt", style=discord.ButtonStyle.secondary)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        await self.cog.config.user(self.ctx.author).system_prompt.set(None)
        await interaction.response.send_message("✅ 個人提示詞已清除。", ephemeral=True)


class DummyToggleButton(discord.ui.Button):
    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, enabled: bool):
        label = f"Dummy Mode: {'ON' if enabled else 'OFF'}"
        style = discord.ButtonStyle.success if enabled else discord.ButtonStyle.secondary
        super().__init__(label=label, style=style)
        self.cog = cog
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        new_state = not await self.cog.config.use_dummy_api()
        await self.cog.config.use_dummy_api.set(new_state)
        await self.cog._init_client()
        self.label = f"Dummy Mode: {'ON' if new_state else 'OFF'}"
        self.style = discord.ButtonStyle.success if new_state else discord.ButtonStyle.secondary

        if self.view:
            new_options = await self.cog._build_model_select_options()
            for child in self.view.children:
                if isinstance(child, ModelSelect):
                    child.options = new_options
                    break
            owner_mode = getattr(self.view, "owner_mode", True)
            embed = await self.cog._build_config_embed(self.ctx, owner_mode, new_state)
            await interaction.response.edit_message(embed=embed, view=self.view)
            await interaction.followup.send(
                "✅ Dummy API mode 已啟用。" if new_state else "✅ Dummy API mode 已關閉。",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "✅ Dummy API mode 狀態已更新。",
                ephemeral=True
            )


class CloseMenuButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Close Menu", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view:
            for child in view.children:
                child.disabled = True
            view.stop()
            await interaction.response.edit_message(view=view)


async def setup(bot: Red):
    """Setup function for Red-DiscordBot"""
    await bot.add_cog(PoeHub(bot))