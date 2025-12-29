from __future__ import annotations

from datetime import UTC, datetime, timedelta

import discord
from discord import ui


class TimezoneSelect(ui.Select):
    def __init__(self, parent_view: ReminderView):
        self.parent_view = parent_view
        options = [
            discord.SelectOption(label="UTC (Coordinated Universal Time)", value="utc", description="Offset: +0"),
            discord.SelectOption(label="New York (Eastern Time)", value="nyc", description="Offset: -5 (Standard) / -4 (DST)"),
            discord.SelectOption(label="Los Angeles (Pacific Time)", value="la", description="Offset: -8 (Standard) / -7 (DST)"),
            discord.SelectOption(label="London (GMT/BST)", value="london", description="Offset: +0 (Standard) / +1 (DST)"),
            discord.SelectOption(label="Paris/Berlin (CET)", value="paris", description="Offset: +1 (Standard) / +2 (DST)"),
            discord.SelectOption(label="Beijing/Taipei (CST)", value="taipei", description="Offset: +8"),
            discord.SelectOption(label="Tokyo (JST)", value="tokyo", description="Offset: +9"),
            discord.SelectOption(label="Sydney (AEST)", value="sydney", description="Offset: +10 (Standard) / +11 (DST)"),
        ]
        super().__init__(placeholder="Select Timezone (Default: UTC)", min_values=1, max_values=1, options=options, custom_id="reminder_timezone_select")

    async def callback(self, interaction: discord.Interaction):
        offset_map = {
            "utc": 0,
            "nyc": -5,
            "la": -8,
            "london": 0,
            "paris": 1,
            "taipei": 8,
            "tokyo": 9,
            "sydney": 10
        }
        self.parent_view.current_offset = offset_map.get(self.values[0], 0)
        # Update embed to show new offset
        await self.parent_view.update_message(interaction)

class UserSelect(ui.UserSelect):
    def __init__(self, parent_view: ReminderView):
        self.parent_view = parent_view
        super().__init__(placeholder="Select Users to Mention", min_values=0, max_values=25, custom_id="reminder_user_select")

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_users = self.values
        await self.parent_view.update_message(interaction)

class RoleSelect(ui.RoleSelect):
    def __init__(self, parent_view: ReminderView):
        self.parent_view = parent_view
        super().__init__(placeholder="Select Roles to Mention", min_values=0, max_values=25, custom_id="reminder_role_select")

    async def callback(self, interaction: discord.Interaction):
        self.parent_view.selected_roles = self.values
        await self.parent_view.update_message(interaction)

class DeleteReminderSelect(ui.Select):
    def __init__(self, parent_view: ReminderView, reminders: list[dict]):
        self.parent_view = parent_view
        options = []
        # sort by timestamp
        reminders.sort(key=lambda x: x.get("timestamp", 0))

        for _, r in enumerate(reminders[:25]): # Max 25 options
            ts = int(r.get("timestamp", 0))
            msg = r.get("message", "No content")
            if len(msg) > 50:
                msg = msg[:47] + "..."

            # Use timestamp as uniqueish identifier logic or index if robust enough for this view session
            # Ideally we'd have unique IDs. Using created_at + timestamp as value
            value = f"{r.get('created_at')}_{r.get('timestamp')}"
            human_time =  datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d %H:%M")
            options.append(discord.SelectOption(
                label=f"{human_time} UTC",
                value=value,
                description=msg,
                emoji="🗑️"
            ))

        if not options:
            options.append(discord.SelectOption(label="No active reminders", value="none", default=True))
            disabled = True
        else:
            disabled = False

        super().__init__(
            placeholder="Select a reminder to DELETE",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="reminder_delete_select",
            disabled=disabled
        )

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "none":
            return

        await interaction.response.defer()
        val = self.values[0]
        # Parse back to identify reminder
        # We rely on parent callback
        if await self.parent_view.delete_callback(val):
            await interaction.followup.send("✅ Reminder deleted!", ephemeral=True)
            self.parent_view.stop()
        else:
            await interaction.followup.send("❌ Could not delete reminder.", ephemeral=True)

class CombinedReminderModal(ui.Modal, title="Schedule Reminder"):
    def __init__(self, parent_view: ReminderView):
        super().__init__()
        self.parent_view = parent_view

    time_input = ui.TextInput(
        label="Time (YYYY-MM-DD HH:MM)",
        placeholder="2025-01-01 12:00",
        required=True,
        min_length=10,
        max_length=20
    )

    message_input = ui.TextInput(
        label="Message content",
        style=discord.TextStyle.paragraph,
        placeholder="Type your reminder message here...",
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        time_str = self.time_input.value
        try:
            # Parse user provided time
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            # Apply offset to get UTC
            utc_dt = dt - timedelta(hours=self.parent_view.current_offset)

            # Ensure it's in the future
            if utc_dt < datetime.utcnow():
                 await interaction.response.send_message("❌ Time must be in the future (UTC check).", ephemeral=True)
                 return

            # Prepare data
            reminder_data = {
                "timestamp": utc_dt.timestamp(),
                "channel_id": self.parent_view.ctx.channel.id,
                "message": self.message_input.value,
                "mentions": [u.id for u in self.parent_view.selected_users] + [r.id for r in self.parent_view.selected_roles],
                "author_id": self.parent_view.ctx.author.id,
                "created_at": datetime.utcnow().timestamp()
            }

            await self.parent_view.confirmation_callback(reminder_data)
            await interaction.response.send_message(f"✅ Reminder scheduled for <t:{int(utc_dt.replace(tzinfo=UTC).timestamp())}:f>!", ephemeral=True)
            self.parent_view.stop()
            # Disable view on message
            if self.parent_view.message:
                await self.parent_view.message.edit(view=None)

        except ValueError:
            await interaction.response.send_message("❌ Invalid format. Please use `YYYY-MM-DD HH:MM`", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

class ReminderView(ui.View):
    def __init__(self, ctx, confirmation_callback, user_reminders=None, delete_callback=None):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.confirmation_callback = confirmation_callback
        self.delete_callback = delete_callback
        self.message: discord.Message | None = None

        # State
        self.current_offset = 0
        self.selected_users = []
        self.selected_roles = []

        # Add components
        self.add_item(TimezoneSelect(self))
        if user_reminders and delete_callback:
            self.add_item(DeleteReminderSelect(self, user_reminders))
        self.add_item(UserSelect(self))
        self.add_item(RoleSelect(self))

    def build_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🔔 Schedule Reminder", description="Select recipients and timezone, then click Confirm to set details.", color=discord.Color.gold())

        embed.add_field(name="🌐 UTC Offset", value=f"{self.current_offset:+d}", inline=True)

        # Targets
        mentions = []
        for u in self.selected_users:
            mentions.append(u.mention)
        for r in self.selected_roles:
            mentions.append(r.mention)

        embed.add_field(name="👥 Mentions", value=", ".join(mentions) if mentions else "None", inline=False)

        return embed

    async def update_message(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @ui.button(label="Confirm & Set Details", style=discord.ButtonStyle.success, row=4, custom_id="reminder_confirm_btn")
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CombinedReminderModal(self))

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=4, custom_id="reminder_cancel_btn")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="❌ Reminder cancelled.", embed=None, view=None)
        self.stop()
