"""Chat Service for handling LLM interactions and message processing."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

import discord
from redbot.core import commands as red_commands

from ..api_client import BaseLLMClient, get_client
from .billing.oracle import TokenUsage

if TYPE_CHECKING:
    from redbot.core import Config
    from redbot.core.bot import Red

    from .billing import BillingService
    from .context import ContextService
    from .conversation.storage import ConversationStorageService

from ..core import ThreadSafeMemory

log = logging.getLogger("red.poehub.services.chat")


class ChatService:
    """Manages chat interactions, API client state, and message streaming."""

    def __init__(
        self,
        bot: Red,
        config: Config,
        billing_service: BillingService,
        context_service: ContextService,
        conversation_manager: ConversationStorageService,
    ):
        self.bot = bot
        self.config = config
        self.billing = billing_service
        self.context = context_service
        self.conversation_manager = conversation_manager

        self.client: BaseLLMClient | None = None

        # Memory Cache: "user_id:conv_id" -> ThreadSafeMemory
        self._memories: dict[str, ThreadSafeMemory] = {}

        # Allow dummy mode from environment flag (passed down or checked here)
        # For simplicity, we'll check the config directly,
        # but the Cog had an env check. We'll replicate logic or assume Cog handles strict env check via config.
        # Actually, the Cog sets the config value based on env flag on init.
        # We can just trust the config here.

    async def initialize_client(self) -> None:
        """Initialize the LLM client based on configuration."""
        self.client = None

        # Check dummy mode
        use_dummy = await self.config.use_dummy_api()

        # Note: The Cog handled the env flag check (ALLOW_DUMMY_MODE) to force disable if not allowed.
        # We assume the Cog ensures the config state is valid before calling this,
        # or we could pass the flag in __init__.

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
        # Fallback to legacy key (migration logic moved here or kept in Cog?
        # It's cleaner to keep migration logic here so the Service is self-contained)
        if not api_key:
            legacy_key = await self.config.api_key()
            if legacy_key and active_provider == "poe":
                api_key = legacy_key
                # Auto-migrate
                provider_keys["poe"] = legacy_key
                await self.config.provider_keys.set(provider_keys)

        # Resolve Base URL
        base_url = provider_urls.get(active_provider)
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

    async def get_matching_models(self, query: str | None = None) -> list[str]:
        """Fetch and filter models matching the query."""
        if not self.client:
            return []

        try:
            models = await self.client.get_models()
            model_ids = [
                m.get("id") for m in models if isinstance(m, dict) and m.get("id")
            ]

            # Filter distinct
            unique_ids = list(dict.fromkeys(model_ids))

            if query:
                query_lower = query.lower()
                unique_ids = [mid for mid in unique_ids if query_lower in mid.lower()]

            return unique_ids
        except Exception as exc:
            log.warning("Could not fetch models: %s", exc)
            return []

    async def process_chat_request(
        self, message: discord.Message, content: str, ctx: red_commands.Context = None
    ):
        """Unified handler for processing chat requests."""
        if not self.client:
            msg = "❌ API client not initialized. "
            if ctx:
                msg += "Bot owner must use `[p]poeapikey` first."
                await ctx.send(msg)
            else:
                msg += "Please contact the bot owner."
                await message.channel.send(msg)
            return

        target_channel = message.channel
        user = message.author

        # --- Access & Budget (Check first before creating threads) ---
        billing_guild = await self.billing.resolve_billing_guild(user, target_channel)
        if not billing_guild:
            if ctx:
                await ctx.send(
                    "❌ Access denied. No authorized guild found for this context."
                )
            elif isinstance(target_channel, discord.DMChannel):
                await target_channel.send(
                    "❌ Access denied. You do not share a server with the bot that permits DM usage."
                )
            return

        if not await self.billing.check_budget(billing_guild):
            msg = "❌ Monthly budget limit reached for this guild."
            if ctx:
                await ctx.send(msg)
            else:
                await target_channel.send(msg)
            return

        # --- Determine Response Target (Create Thread if needed) ---
        response_target = await self._determine_response_target(
            message, target_channel, content
        )

        # --- Determine Scope (User vs Channel/Thread) ---
        # "chat history stored by user is only for DMs"
        is_dm = isinstance(target_channel, discord.DMChannel)

        if is_dm:
            # User Scope
            scope_group = self.config.user_from_id(user.id)
            conv_id = await self.context.get_active_conversation_id(user.id)
            unique_key = f"user:{user.id}:{conv_id}"

            # Use User's model preference
            active_conv_data = await self._get_conversation(scope_group, conv_id)
            if active_conv_data and active_conv_data.get("model"):
                user_model = active_conv_data["model"]
            else:
                user_model = await self.config.user(user).model()
        else:
            # Channel/Thread Scope (Shared Context)
            # Use the ID of the response target (Thread or Channel)
            context_id = response_target.id
            scope_group = self.config.channel(response_target)
            conv_id = "default" # Threads have a single linear history
            unique_key = f"channel:{context_id}:{conv_id}"

            # For shared context, whose model do we use?
            # We'll use the current user's preference for now, or fall back to a default.
            # But if the conversation has a specific model set (e.g. manually switched), use it.
            active_conv_data = await self._get_conversation(scope_group, conv_id)
            if active_conv_data and active_conv_data.get("model"):
                user_model = active_conv_data["model"]
            else:
                user_model = await self.config.user(user).model()

        # Load history from the determined scope
        history = await self._get_conversation_messages(scope_group, conv_id, unique_key)
        log.info(f"Loaded history for {unique_key}: {len(history)} msgs")

        # --- Quote / Reply Context ---
        quote_context = await self._resolve_quote_context(message)

        # --- Attachments ---
        image_urls = self._extract_image_urls(message)

        # --- Construct Message ---
        full_text_input = f"{quote_context}{content}" if quote_context else content

        if image_urls:
            formatted_content = self.client.format_image_message(
                full_text_input, image_urls
            )
        else:
            # For text-only, we just use full_text_input
            formatted_content = full_text_input

        # Save to history (User or Thread scope)
        await self._add_message_to_conversation(
            scope_group, conv_id, unique_key, "user", formatted_content
        )

        # Combine history
        # Note: formatted_content is for storage, we need dict for API
        new_message = {"role": "user", "content": formatted_content}
        messages = history + [new_message]

        # System Prompt (User's custom prompt - applied even in threads?)
        # User said "Anyone who respond in the thread shares the context".
        # Maybe system prompt should be consistent?
        # For now, applying the current user's system prompt seems safest/most personalized
        # unless we support per-thread system prompts (future feature).
        system_prompt = await self.context.get_user_system_prompt(user.id)
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # --- Stream Response ---
        try:
            await self.stream_response(
                ctx=ctx,
                messages=messages,
                model=user_model,
                target_channel=response_target,
                save_to_conv=(scope_group, conv_id, unique_key),
                billing_guild=billing_guild,
            )
        except Exception as e:
            log.exception("Failed to stream response")
            # Fallback: try to send error to the original channel if the target was a new thread
            if response_target != message.channel:
                 try:
                     await message.channel.send(f"❌ Error occurred in thread: {e}")
                 except Exception:
                     pass
            raise e

    async def get_response(
        self,
        messages: list[dict[str, Any]],
        model: str,
        billing_guild: discord.Guild | None = None,
    ) -> str:
        """Get a complete response string (non-streaming)."""
        if not self.client:
            raise RuntimeError("API client not initialized")

        accumulated_content = []
        try:
            stream = self.client.stream_chat(model, messages)
            async for item in stream:
                if isinstance(item, TokenUsage):
                    log.info(f"Got usage: {item} (Currency: {item.currency})")
                    if billing_guild:
                        await self.billing.update_spend(
                            billing_guild, item.cost, currency=item.currency
                        )
                    continue
                accumulated_content.append(item)

            return "".join(accumulated_content)
        except Exception as exc:
            log.error(f"Error in get_response: {exc}")
            raise

    async def stream_response(
        self,
        ctx: red_commands.Context | None,
        messages: list[dict[str, Any]],
        model: str,
        target_channel=None,
        save_to_conv=None,
        billing_guild: discord.Guild = None,
    ):
        """Stream the AI response and update Discord message."""
        dest = target_channel if target_channel else (ctx.channel if ctx else None)
        if not dest:
            log.error("No destination channel for stream response")
            return

        try:
            response_msg = await dest.send("🤔 Thinking...")
            accumulated_parts = []
            last_update = time.time()

            stream = self.client.stream_chat(model, messages)

            async for item in stream:
                if isinstance(item, TokenUsage):
                    log.info(f"Got usage: {item} (Currency: {item.currency})")
                    if billing_guild:
                        await self.billing.update_spend(
                            billing_guild, item.cost, currency=item.currency
                        )
                    continue

                accumulated_parts.append(item)

                current_time = time.time()
                if current_time - last_update >= 2.0:
                    try:
                        current_full_content = "".join(accumulated_parts)
                        display_content = current_full_content[:1900]
                        if len(current_full_content) > 1900:
                            display_content += "\n...(truncated)"

                        await response_msg.edit(content=display_content)
                        last_update = current_time
                    except discord.HTTPException:
                        pass

            # Final update
            accumulated_content = "".join(accumulated_parts)
            if accumulated_content:
                chunks = self._split_message(accumulated_content)
                await response_msg.edit(content=chunks[0])

                for chunk in chunks[1:]:
                    await dest.send(chunk)

                if save_to_conv:
                    scope_group, conv_id, unique_key = save_to_conv
                    await self._add_message_to_conversation(
                        scope_group, conv_id, unique_key, "assistant", accumulated_content
                    )
            else:
                await response_msg.edit(content="❌ No response received from API.")

        except Exception as exc:
            error_msg = f"❌ Error communicating with Poe API: {exc}"
            log.exception("Error communicating with Poe API")
            await dest.send(error_msg)

    async def send_split_message(self, destination: discord.abc.Messageable, content: str):
        """Send a long message to Discord, splitting if necessary."""
        chunks = self._split_message(content)
        for chunk in chunks:
            await destination.send(chunk)


    def _split_message(self, content: str, max_length: int = 1950) -> list[str]:
        """Split text into Discord-safe chunks."""
        if len(content) <= max_length:
            return [content]

        chunks = []
        remaining = content

        while remaining:
            if len(remaining) <= max_length:
                chunks.append(remaining)
                break

            chunk = remaining[:max_length]
            split_point = max_length

            # Priorities
            split_candidates = [
                ("```\n", 4),
                ("\n\n", 2),
                ("\n", 1),
                (". ", 2),
                (" ", 1),
            ]

            for delimiter, offset in split_candidates:
                last_pos = chunk.rfind(delimiter)
                if last_pos > max_length * 0.5:
                    split_point = last_pos + offset
                    break

            chunks.append(remaining[:split_point].rstrip())
            remaining = remaining[split_point:].lstrip()

            if remaining and not chunks[-1].endswith("```"):
                chunks[-1] = chunks[-1] + "\n\n*(continued...)*"
            if remaining and len(chunks) > 0:
                remaining = "*(continued)*\n\n" + remaining

        return chunks

    # --- Helpers ---

    async def _resolve_quote_context(self, message: discord.Message) -> str:
        """Resolve optional quote context from replies."""
        if not (message.reference and message.reference.message_id):
            return ""

        try:
            ref_msg = message.reference.cached_message
            if not ref_msg:
                ref_msg = await message.channel.fetch_message(
                    message.reference.message_id
                )

            if ref_msg and ref_msg.content:
                return f'[Replying to {ref_msg.author.display_name}: "{ref_msg.content}"]\n\n'
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
        return ""

    def _extract_image_urls(self, message: discord.Message) -> list[str]:
        """Extract valid image URLs from message attachments and references."""
        image_urls = []

        def check_attachments(msg):
            if msg and msg.attachments:
                for attachment in msg.attachments:
                    if attachment.content_type and attachment.content_type.startswith(
                        "image/"
                    ):
                        image_urls.append(attachment.url)

        check_attachments(message)

        # Check referenced message
        if message.reference and message.reference.cached_message:
            check_attachments(message.reference.cached_message)
        # Note: We don't fetch referenced msg again if not cached to avoid double fetch latency,
        # or we could if we passed the fetched ref_msg from _resolve_quote_context if we refactored slightly.
        # For now, simplistic approach.

        return image_urls

    async def _determine_response_target(
        self, message: discord.Message, target_channel, content: str
    ):
        """Determine if we should thread the response."""
        is_already_thread = isinstance(target_channel, discord.Thread)
        if (
            not isinstance(target_channel, discord.DMChannel)
            and not is_already_thread
            and hasattr(message, "create_thread")
        ):
            try:
                thread_name = content[:50] + "..." if len(content) > 50 else content
                if not thread_name.strip():
                    thread_name = "AI Response"

                thread = await message.create_thread(
                    name=thread_name, auto_archive_duration=60
                )
                # Small delay to ensure thread propagation
                await asyncio.sleep(0.5)
                return thread
            except (discord.Forbidden, discord.HTTPException) as e:
                log.warning(f"Could not create thread: {e}")

        return target_channel

    # --- Conversation Helpers (Proxy to Manager + Context) ---

    async def _get_conversation(
        self, scope_group: Any, conv_id: str
    ) -> dict[str, Any] | None:
        """Get processed conversation data from a config group (User or Channel)."""
        conversations = await scope_group.conversations()
        if conv_id in conversations:
            return self.conversation_manager.process_conversation_data(
                conversations[conv_id]
            )
        return None

    async def _get_or_create_conversation(
        self, scope_group: Any, conv_id: str
    ) -> dict[str, Any]:
        """Get or create conversation."""
        conv = await self._get_conversation(scope_group, conv_id)
        if conv is None:
            conv = self.conversation_manager.create_conversation(conv_id)
            await self._save_conversation(scope_group, conv_id, conv)
        return conv

    async def _save_conversation(
        self, scope_group: Any, conv_id: str, conv_data: dict[str, Any]
    ):
        """Save conversation data (encrypted) to the config group."""
        conversations = await scope_group.conversations()
        conversations[conv_id] = self.conversation_manager.prepare_for_storage(
            conv_data
        )
        await scope_group.conversations.set(conversations)

    async def _get_memory(self, scope_group: Any, conv_id: str, unique_key: str) -> ThreadSafeMemory:
        """Get or initialize the ThreadSafeMemory for a conversation.
        unique_key: A unique string identifier for caching (e.g. 'user:123:conv' or 'channel:456:conv')
        """
        if unique_key not in self._memories:
            # Load existing messages from storage
            conv = await self._get_or_create_conversation(scope_group, conv_id)
            messages = conv.get("messages", [])
            self._memories[unique_key] = ThreadSafeMemory(messages)
        return self._memories[unique_key]

    async def _clear_conversation_memory(self, unique_key: str) -> None:
        """Clear the in-memory conversation messages."""
        if unique_key in self._memories:
            await self._memories[unique_key].clear()

    async def _add_message_to_conversation(
        self, scope_group: Any, conv_id: str, unique_key: str, role: str, content: Any
    ):
        """Add message to conversation using ThreadSafeMemory."""
        memory = await self._get_memory(scope_group, conv_id, unique_key)

        # Prepare the message object (mimicking storage format)
        new_msg = {"role": role, "content": content, "timestamp": time.time()}

        # Add to memory (thread-safe)
        await memory.add_message(new_msg)

        # Write-through to persistence
        all_messages = await memory.get_messages()

        # Simple Pruning for safer write-back
        MAX_HISTORY = 50
        if len(all_messages) > MAX_HISTORY:
            all_messages = all_messages[-MAX_HISTORY:]

        conv = await self._get_or_create_conversation(scope_group, conv_id)
        conv["messages"] = all_messages
        conv["updated_at"] = time.time()
        await self._save_conversation(scope_group, conv_id, conv)

    async def _get_conversation_messages(
        self, scope_group: Any, conv_id: str, unique_key: str
    ) -> list[dict[str, str]]:
        """Get messages formatted for API from memory."""
        memory = await self._get_memory(scope_group, conv_id, unique_key)
        messages = await memory.get_messages()

        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]


