"""Chat Service for handling LLM interactions and message processing."""

from __future__ import annotations

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

        # Get preferences & Context
        active_conv_id = await self.context.get_active_conversation_id(user.id)

        # Load conversation to check for specific model
        conv_data = await self._get_conversation(user.id, active_conv_id)
        if conv_data and conv_data.get("model"):
            user_model = conv_data["model"]
        else:
            user_model = await self.config.user(user).model()

        # Load history
        history = await self._get_conversation_messages(user.id, active_conv_id)

        # --- Access & Budget ---
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
            new_message = {"role": "user", "content": formatted_content}
        else:
            new_message = {"role": "user", "content": full_text_input}

            # For text-only, we just use full_text_input as the content to save if it's simpler,
            # but formatted_content is safer if consistent.
            # In original code: msg_content_to_save = formatted_content if image_urls else full_text_input

        # Save to history
        msg_content_to_save = formatted_content if image_urls else full_text_input
        await self._add_message_to_conversation(
            user.id, active_conv_id, "user", msg_content_to_save
        )

        # Combine history
        messages = history + [new_message]

        # System Prompt
        system_prompt = await self.context.get_user_system_prompt(user.id)
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        # --- Response Target ---
        response_target = await self._determine_response_target(
            message, target_channel, content
        )

        # --- Stream Response ---
        await self.stream_response(
            ctx=ctx,
            messages=messages,
            model=user_model,
            target_channel=response_target,
            save_to_conv=(user.id, active_conv_id),
            billing_guild=billing_guild,
        )

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
                    user_id, conv_id = save_to_conv
                    await self._add_message_to_conversation(
                        user_id, conv_id, "assistant", accumulated_content
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

                return await message.create_thread(
                    name=thread_name, auto_archive_duration=60
                )
            except (discord.Forbidden, discord.HTTPException) as e:
                log.warning(f"Could not create thread: {e}")

        return target_channel

    # --- Conversation Helpers (Proxy to Manager + Context) ---
    # We duplicate some logic here because ChatService needs to resolve "active_conv_id" -> "conversation data"
    # The PoeHub class had _get_conversation, _add_message_to_conversation etc.
    # Ideally, we should unify this.

    async def _get_conversation(
        self, user_id: int, conv_id: str
    ) -> dict[str, Any] | None:
        """Get processed conversation data."""
        conversations = await self.config.user_from_id(user_id).conversations()
        if conv_id in conversations:
            return self.conversation_manager.process_conversation_data(
                conversations[conv_id]
            )
        return None

    async def _get_or_create_conversation(
        self, user_id: int, conv_id: str
    ) -> dict[str, Any]:
        """Get or create conversation."""
        conv = await self._get_conversation(user_id, conv_id)
        if conv is None:
            conv = self.conversation_manager.create_conversation(conv_id)
            await self._save_conversation(user_id, conv_id, conv)
        return conv

    async def _save_conversation(
        self, user_id: int, conv_id: str, conv_data: dict[str, Any]
    ):
        """Save conversation data (encrypted)."""
        conversations = await self.config.user_from_id(user_id).conversations()
        conversations[conv_id] = self.conversation_manager.prepare_for_storage(
            conv_data
        )
        await self.config.user_from_id(user_id).conversations.set(conversations)

    async def _get_memory(self, user_id: int, conv_id: str) -> ThreadSafeMemory:
        """Get or initialize the ThreadSafeMemory for a conversation."""
        key = f"{user_id}:{conv_id}"
        if key not in self._memories:
            # Load existing messages from storage
            conv = await self._get_or_create_conversation(user_id, conv_id)
            messages = conv.get("messages", [])
            self._memories[key] = ThreadSafeMemory(messages)
        return self._memories[key]

    async def _clear_conversation_memory(self, user_id: int, conv_id: str) -> None:
        """Clear the in-memory conversation messages using ThreadSafeMemory.clear().
        This should be called when conversation history is cleared to ensure
        the cached memory is also cleared.
        """
        memory = await self._get_memory(user_id, conv_id)
        await memory.clear()



    async def _add_message_to_conversation(
        self, user_id: int, conv_id: str, role: str, content: Any
    ):
        """Add message to conversation using ThreadSafeMemory."""
        memory = await self._get_memory(user_id, conv_id)

        # Prepare the message object (mimicking storage format)
        new_msg = {"role": role, "content": content, "timestamp": time.time()}

        # Add to memory (thread-safe)
        await memory.add_message(new_msg)

        # Write-through to persistence
        # We fetch the full list from memory to ensure we catch any concurrent updates
        # committed to the sequence.
        all_messages = await memory.get_messages()

        # Enforce history limit (redundant but safe to do here or in storage service)
        #Ideally storage service handles this, but since we are bypassing
        # storage.add_message to use direct memory manipulation, we should prune here
        # OR just push the full list to storage and let it handle/overwrite.
        # However, conversation_manager.add_message does the pruning logic.
        # To reuse that logic without race we should probably rely on memory first.

        # Simple Pruning for safer write-back
        MAX_HISTORY = 50
        if len(all_messages) > MAX_HISTORY:
            all_messages = all_messages[-MAX_HISTORY:]
            # Ideally update memory buffer too?
            # ThreadSafeMemory doesn't have a 'replace' method exposed yet easily without clear+add.
            # For now, we just save the pruned list to disk.

        conv = await self._get_or_create_conversation(user_id, conv_id)
        conv["messages"] = all_messages
        conv["updated_at"] = time.time()
        await self._save_conversation(user_id, conv_id, conv)

    async def _get_conversation_messages(
        self, user_id: int, conv_id: str
    ) -> list[dict[str, str]]:
        """Get messages formatted for API from memory."""
        memory = await self._get_memory(user_id, conv_id)
        messages = await memory.get_messages()

        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in messages
        ]

