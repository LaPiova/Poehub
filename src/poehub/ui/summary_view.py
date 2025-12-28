"""Message Summary UI for PoeHub."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, List, Optional, TYPE_CHECKING

import discord
from redbot.core import commands as red_commands

from ..i18n import tr
from .common import BackButton, CloseMenuButton

if TYPE_CHECKING:  # pragma: no cover
    from ..poehub import PoeHub


class TimeRangeSelect(discord.ui.Select):
    """Dropdown to select time range for message summary."""

    def __init__(self, lang: str) -> None:
        options = [
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_1H"),
                value="1",
                emoji="🕐",
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_6H"),
                value="6",
                emoji="🕕",
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_24H"),
                value="24",
                emoji="📅",
            ),
            discord.SelectOption(
                label=tr(lang, "SUMMARY_TIME_CUSTOM"),
                value="custom",
                emoji="⚙️",
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
            # Open modal for custom time input
            modal = CustomTimeModal(view.cog, view.ctx, self.lang, view)
            await interaction.response.send_modal(modal)
        else:
            view.selected_hours = float(selected)
            # Update the embed to show selected time range
            await view.update_embed(interaction)


class CustomTimeModal(discord.ui.Modal):
    """Modal for entering custom hours."""

    def __init__(
        self,
        cog: "PoeHub",
        ctx: red_commands.Context,
        lang: str,
        parent_view: "SummaryView",
    ) -> None:
        super().__init__(title=tr(lang, "SUMMARY_CUSTOM_MODAL_TITLE"))
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.parent_view = parent_view
        
        self.hours = discord.ui.TextInput(
            label=tr(lang, "SUMMARY_CUSTOM_HOURS_LABEL"),
            placeholder=tr(lang, "SUMMARY_CUSTOM_HOURS_PLACEHOLDER"),
            required=True,
            max_length=10,
        )
        self.add_item(self.hours)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            hours = float(self.hours.value)
            if hours <= 0:
                raise ValueError("Hours must be positive")
            self.parent_view.selected_hours = hours
            await self.parent_view.update_embed(interaction)
        except ValueError:
            await interaction.response.send_message(
                tr(self.lang, "SUMMARY_INVALID_HOURS"),
                ephemeral=True,
            )


class StartSummaryButton(discord.ui.Button):
    """Button to initiate message summary."""

    def __init__(self, cog: "PoeHub", ctx: red_commands.Context, lang: str) -> None:
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
        
        # Validate we're in a guild text channel
        channel = self.ctx.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(
                tr(self.lang, "SUMMARY_ERROR_NOT_IN_CHANNEL"),
                ephemeral=True,
            )
            return
        
        # Check API client
        if not self.cog.client:
            await interaction.response.send_message(
                tr(self.lang, "SUMMARY_ERROR_API"),
                ephemeral=True,
            )
            return
        
        # Acknowledge interaction first
        await interaction.response.defer()
        
        # Disable all buttons to prevent double-clicks
        for child in view.children:
            child.disabled = True
        await interaction.edit_original_response(view=view)
        
        # Generate the summary
        await self._generate_summary(channel, view.selected_hours)

    async def _generate_summary(
        self,
        channel: discord.TextChannel,
        hours: float,
    ) -> None:
        """Fetch messages and generate AI summary."""
        # Calculate time range
        now = datetime.now(timezone.utc)
        after_time = now - timedelta(hours=hours)
        
        # Fetch messages
        messages: List[discord.Message] = []
        async for msg in channel.history(after=after_time, limit=500, oldest_first=True):
            # Skip bot messages and empty messages
            if msg.author.bot:
                continue
            if not msg.content and not msg.attachments:
                continue
            messages.append(msg)
        
        if not messages:
            await channel.send(tr(self.lang, "SUMMARY_NO_MESSAGES"))
            return
        
        # Format messages for context
        formatted_messages = []
        for msg in messages:
            timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M")
            content = msg.content or "[attachment]"
            formatted_messages.append(f"[{timestamp}] {msg.author.display_name}: {content}")
        
        context_text = "\n".join(formatted_messages)
        
        # Truncate if too long (keep ~15k characters for context)
        if len(context_text) > 15000:
            context_text = context_text[:15000] + "\n...[truncated]"
        
        # Build the summary prompt - let LLM detect and use the dominant language
        summary_prompt = f"""Please provide a comprehensive summary of the following Discord channel conversation. 
Highlight the main topics discussed, key decisions made, and any important information shared.
Organize your summary with clear sections if there are multiple topics.

**IMPORTANT: Identify the most commonly used language in the conversation below, and write your entire summary in that same language.**

Time range: Last {hours} hour(s)
Number of messages: {len(messages)}

--- MESSAGES START ---
{context_text}
--- MESSAGES END ---

Provide a clear, well-organized summary in the dominant language of the conversation:"""

        # Send initial message
        initial_msg = await channel.send(tr(self.lang, "SUMMARY_STARTING"))
        
        # Create thread under the message
        try:
            thread = await initial_msg.create_thread(
                name=tr(self.lang, "SUMMARY_THREAD_NAME"),
                auto_archive_duration=60,
            )
        except (discord.Forbidden, discord.HTTPException):
            # Fall back to editing the message directly if thread creation fails
            thread = None
        
        # Get user model
        user_model = await self.cog.config.user(self.ctx.author).model()
        
        # Prepare messages for API
        api_messages = [{"role": "user", "content": summary_prompt}]
        
        # Get system prompt if any
        system_prompt = await self.cog._get_system_prompt(self.ctx.author.id)
        if system_prompt:
            api_messages = [{"role": "system", "content": system_prompt}] + api_messages
        
        # Determine target for response
        response_target = thread if thread else channel
        
        # Stream the response
        await self.cog._stream_response(
            ctx=None,
            messages=api_messages,
            model=user_model,
            target_channel=response_target,
            save_to_conv=None,  # Don't save summary to conversation history
            billing_guild=self.ctx.guild,
        )
        
        # Update initial message to show completion
        if thread:
            await initial_msg.edit(
                content=tr(self.lang, "SUMMARY_PROCESSING", count=len(messages))
            )


class SummaryView(discord.ui.View):
    """View for Message Summary functionality."""

    def __init__(
        self,
        cog: "PoeHub",
        ctx: red_commands.Context,
        lang: str,
        back_callback: Optional[Callable[[discord.Interaction], Awaitable[None]]] = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.selected_hours: float = 1.0  # Default to 1 hour
        self.back_callback = back_callback
        
        self.add_item(TimeRangeSelect(lang))
        self.add_item(StartSummaryButton(cog, ctx, lang))
        self.add_item(CloseMenuButton(label=tr(lang, "CLOSE_MENU")))
        
        if back_callback:
            self.add_item(BackButton(back_callback, lang))

    def build_embed(self) -> discord.Embed:
        """Build the summary view embed."""
        embed = discord.Embed(
            title=tr(self.lang, "SUMMARY_TITLE"),
            description=tr(self.lang, "SUMMARY_DESC"),
            color=discord.Color.orange(),
        )
        
        # Show currently selected time range
        if self.selected_hours == 1:
            time_label = tr(self.lang, "SUMMARY_TIME_1H")
        elif self.selected_hours == 6:
            time_label = tr(self.lang, "SUMMARY_TIME_6H")
        elif self.selected_hours == 24:
            time_label = tr(self.lang, "SUMMARY_TIME_24H")
        else:
            time_label = f"{self.selected_hours} hours"
        
        embed.add_field(
            name=tr(self.lang, "SUMMARY_TIME_RANGE_LABEL"),
            value=f"**{time_label}**",
            inline=True,
        )
        
        return embed

    async def update_embed(self, interaction: discord.Interaction) -> None:
        """Update the embed after time range selection."""
        embed = self.build_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                tr(self.lang, "RESTRICTED_MENU"),
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if hasattr(self, "message") and self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass
