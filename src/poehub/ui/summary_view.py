"""Message Summary UI for PoeHub."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import discord
from pydantic import BaseModel
from redbot.core import commands as red_commands

from ..core.i18n import tr
from ..core.protocols import IPoeHub
from ..models import MessageData
from .common import BackButton, CloseMenuButton

log = logging.getLogger("red.poehub.summary")

# --- Pydantic Models for Validation ---





class SummaryChunk(BaseModel):
    chunk_id: int
    text: str


# --- Views ---


class TimeRangeSelect(discord.ui.Select):
    """Dropdown to select time range for message summary."""

    def __init__(self, lang: str) -> None:
        options = [
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_1H"), value="1", emoji="🕐"
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_6H"), value="6", emoji="🕕"
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_24H"), value="24", emoji="📅"
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_CUSTOM"), value="custom", emoji="⚙️"
            ),
        ]
        super().__init__(
            placeholder=tr(lang, "SUMMARY_TIME_RANGE_LABEL"),
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        selected = self.values[0]
        view: SummaryView = self.view  # type: ignore

        if selected == "custom":
            modal = CustomTimeModal(view.cog, view.ctx, self.lang, view)
            await interaction.response.send_modal(modal)
        else:
            view.selected_hours = float(selected)
            await view.update_embed(interaction)


class CustomTimeModal(discord.ui.Modal):
    def __init__(
        self,
        cog: IPoeHub,
        ctx: red_commands.Context,
        lang: str,
        parent_view: SummaryView,
    ) -> None:
        super().__init__(title=tr(lang, "SUMMARY_CUSTOM_MODAL_TITLE"))
        self.parent_view = parent_view
        self.lang = lang
        self.hours = discord.ui.TextInput(
            label=tr(lang, "SUMMARY_CUSTOM_HOURS_LABEL"),
            placeholder="1-168",
            required=True,
            max_length=5,
        )
        self.add_item(self.hours)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            val = float(self.hours.value)
            if val <= 0 or val > 168:
                raise ValueError
            self.parent_view.selected_hours = val
            await self.parent_view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message(
                tr(self.lang, "SUMMARY_INVALID_HOURS"), ephemeral=True
            )


class StartSummaryButton(discord.ui.Button):
    def __init__(self, cog: IPoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "SUMMARY_BTN_START"),
            style=discord.ButtonStyle.success,
            emoji="📊",
            row=1,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        view: SummaryView = self.view  # type: ignore
        channel = self.ctx.channel

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "Guild text channels only.", ephemeral=True
            )

        await interaction.response.defer()

        # Disable UI
        for child in view.children:
            child.disabled = True
        await interaction.edit_original_response(view=view)

        # Start Process
        await self._run_summary_pipeline(channel, view.selected_hours)

    async def _fetch_messages_producer(
        self, channel: discord.TextChannel, after_time: datetime
    ) -> AsyncGenerator[list[MessageData], None]:
        """Producer: Yields chunks of formatted messages."""
        batch = []
        async for msg in channel.history(
            after=after_time, limit=None, oldest_first=True
        ):
            if msg.author.bot or (not msg.content and not msg.attachments):
                continue

            data = MessageData(
                author=msg.author.display_name,
                content=msg.content or "[Image/Attachment]",
                timestamp=msg.created_at.strftime("%Y-%m-%d %H:%M"),
            )
            batch.append(data)

            if len(batch) >= 50:  # Yield every 50 messages
                yield batch
                batch = []

        if batch:
            yield batch

    async def _run_summary_pipeline(self, channel: discord.TextChannel, hours: float):
        initial_msg = await channel.send(f"🔄 Scanning messages from last {hours}h...")

        # 1. Fetch Messages
        now = datetime.now(UTC)
        after_time = now - timedelta(hours=hours)

        messages: list[MessageData] = []
        async for batch in self._fetch_messages_producer(channel, after_time):
            messages.extend(batch)

        if not messages:
            return await initial_msg.edit(content="❌ No messages found in time range.")

        message_count = len(messages)
        await initial_msg.edit(content=f"📝 Found {message_count} messages. Starting summary...")

        # 2. Run Service
        user_model = await self.cog.config.user(self.ctx.author).model()
        final_text = ""

        # We need to verify if summarizer exists (it should via IPoeHub but implementation might be partial in tests)
        if not self.cog.summarizer:
             return await initial_msg.edit(content="❌ Summarizer service not available.")

        async for update in self.cog.summarizer.summarize_messages(
            messages, self.ctx.author.id, model=user_model, billing_guild=self.ctx.guild
        ):
            if update.startswith("RESULT: "):
                final_text = update[8:] # Remove prefix
            elif update.startswith("STATUS: "):
                # Update status message occasionally?
                # To avoid rate limits, we could debounce, but let's just try editing.
                # If too fast, it might error.
                try:
                    await initial_msg.edit(content=f"📝 {update[8:]}")
                except discord.HTTPException:
                    pass

        if not final_text:
            return await initial_msg.edit(content="❌ Failed to generate summary.")

        # 3. Send Result
        try:
            thread = await initial_msg.create_thread(
                name=f"Summary: Last {hours}h", auto_archive_duration=60
            )
            target = thread
        except discord.Forbidden:
            target = channel

        await self.cog.chat_service.send_split_message(target, final_text)

        await initial_msg.edit(
            content=f"✅ Summary generated for {message_count} messages."
        )


class SummaryView(discord.ui.View):
    def __init__(
        self, cog: IPoeHub, ctx: red_commands.Context, lang: str, back_callback=None
    ):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.selected_hours = 1.0
        self.back_callback = back_callback

        self.add_item(TimeRangeSelect(lang))
        self.add_item(StartSummaryButton(cog, ctx, lang))
        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))
        if back_callback:
            self.add_item(BackButton(back_callback, lang))

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=tr(self.lang, "SUMMARY_TITLE"),
            description=tr(self.lang, "SUMMARY_DESC"),
            color=discord.Color.orange(),
        )
        embed.add_field(name="Selected Time", value=f"**{self.selected_hours} Hours**")
        return embed

    async def update_embed(self, interaction: discord.Interaction):
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)
