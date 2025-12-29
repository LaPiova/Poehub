"""Interactive conversation management UI for PoeHub."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

import discord
from redbot.core import commands as red_commands

from ..core.i18n import tr
from .common import BackButton, CloseMenuButton, preview_content

if TYPE_CHECKING:  # pragma: no cover
    from ..poehub import PoeHub

log = logging.getLogger("red.poehub.ui")


class SwitchConversationSelect(discord.ui.Select):
    """Dropdown to switch the active conversation."""

    def __init__(
        self,
        cog: PoeHub,
        ctx: red_commands.Context,
        options: list[discord.SelectOption],
        lang: str,
    ) -> None:
        super().__init__(
            placeholder=tr(lang, "CONV_SWITCH_PLACEHOLDER"),
            min_values=1,
            max_values=1,
            options=options,
            row=0,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        conv_id = self.values[0]
        await self.cog.context_service.set_active_conversation_id(self.ctx.author.id, conv_id)
        await interaction.response.defer()
        if isinstance(self.view, ConversationMenuView):
            await self.view.refresh_content(interaction)


class DeleteButton(discord.ui.Button):
    """Button to delete the active conversation."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "CONV_BTN_DELETE"),
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=2,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.cog.conversation_manager:
            await interaction.response.send_message(
                tr(self.lang, "CONV_SYSTEM_NOT_INITIALIZED"), ephemeral=True
            )
            return

        active_id = await self.cog.context_service.get_active_conversation_id(self.ctx.author.id)
        if active_id == "default":
            await interaction.response.send_message(
                tr(self.lang, "CONV_DELETE_FAILED", title="Default"),
                ephemeral=True,
            )
            return

        title = active_id  # Fallback
        conv = await self.cog._get_conversation(self.ctx.author.id, active_id)
        if conv:
            title = conv.get("title", active_id)

        success = await self.cog._delete_conversation(self.ctx.author.id, active_id)
        if not success:
            await interaction.response.send_message(
                tr(self.lang, "CONV_DELETE_FAILED", title=title),
                ephemeral=True,
            )
            return

        # Reset to default
        await self.cog.context_service.set_active_conversation_id(self.ctx.author.id, "default")

        await interaction.response.send_message(
            tr(self.lang, "CONV_DELETED_OK", title=title),
            ephemeral=True,
        )
        if isinstance(self.view, ConversationMenuView):
            await self.view.refresh_content(interaction, update_response=True)


class ClearHistoryButton(discord.ui.Button):
    """Button to clear the active conversation's message history."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "CONV_BTN_CLEAR_HISTORY"),
            style=discord.ButtonStyle.danger,
            emoji="🧹",
            row=2,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.cog.conversation_manager:
            await interaction.response.send_message(
                tr(self.lang, "CONV_SYSTEM_NOT_INITIALIZED"),
                ephemeral=True,
            )
            return

        active_conv_id = await self.cog.context_service.get_active_conversation_id(self.ctx.author.id)
        conv = await self.cog._get_conversation(self.ctx.author.id, active_conv_id)
        if not conv:
            await interaction.response.send_message(
                tr(self.lang, "CONV_NO_ACTIVE"),
                ephemeral=True,
            )
            return

        updated_conv = self.cog.conversation_manager.clear_messages(conv)
        await self.cog._save_conversation(
            self.ctx.author.id, active_conv_id, updated_conv
        )

        # Clear the in-memory cache using ThreadSafeMemory.clear()
        await self.cog.chat_service._clear_conversation_memory(
            self.ctx.author.id, active_conv_id
        )

        await interaction.response.send_message(
            tr(
                self.lang,
                "CONV_HISTORY_CLEARED_OK",
                title=updated_conv.get("title", active_conv_id),
            ),
            ephemeral=True,
        )

        if isinstance(self.view, ConversationMenuView):
            await self.view.refresh_content(interaction, update_response=True)


class NewConversationButton(discord.ui.Button):
    """Button to create a new conversation."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        super().__init__(
            label=tr(lang, "CONV_BTN_NEW"),
            style=discord.ButtonStyle.success,
            emoji="➕",
            row=2,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        if not self.cog.conversation_manager:
            await interaction.response.send_message(
                tr(self.lang, "CONV_SYSTEM_NOT_INITIALIZED"), ephemeral=True
            )
            return

        if not self.cog.conversation_manager:
            await interaction.response.send_message(
                tr(self.lang, "CONV_SYSTEM_NOT_INITIALIZED"), ephemeral=True
            )
            return

        # Use helper to create and switch
        await self.cog._create_and_switch_conversation(self.ctx.author.id)

        await interaction.response.send_message(
            tr(self.lang, "UPDATED"), ephemeral=True
        )

        if isinstance(self.view, ConversationMenuView):
            await self.view.refresh_content(interaction, update_response=True)


class RefreshButton(discord.ui.Button):
    """Button to refresh the conversation menu embed/options."""

    def __init__(self, lang: str) -> None:
        super().__init__(
            label=tr(lang, "CONV_BTN_REFRESH"),
            style=discord.ButtonStyle.secondary,
            emoji="🔄",
            row=2,
        )
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if isinstance(self.view, ConversationMenuView):
            await self.view.refresh_content(interaction)


from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:  # pragma: no cover
    from ..poehub import PoeHub

# ... (SwitchConversationSelect, DeleteConversationSelect, ClearHistoryButton, NewConversationButton, RefreshButton classes omitted in replace, assuming they are above)
# Wait, replace_file_content replaces a contiguous block. I need to be careful with imports which are at the top.
# I will do imports separately if they are far apart.
# Imports are lines 7-13. ConversationMenuView starts line 199.



class ConversationModelSelect(discord.ui.Select):
    """Dropdown to select model for the current conversation."""

    def __init__(
        self,
        cog: PoeHub,
        ctx: red_commands.Context,
        options: list[discord.SelectOption],
        lang: str,
        active_model: str | None,
    ) -> None:
        # Mark active model
        if active_model:
            for opt in options:
                opt.default = (opt.value == active_model)

        super().__init__(
            placeholder=tr(lang, "CONFIG_SELECT_MODEL_PLACEHOLDER", default="Select Model..."),
            min_values=1,
            max_values=1,
            options=options,
            row=1,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        model_choice = self.values[0]
        # Get active conv
        active_id = await self.cog.context_service.get_active_conversation_id(self.ctx.author.id)
        conv = await self.cog._get_or_create_conversation(self.ctx.author.id, active_id)

        # Update model
        conv["model"] = model_choice
        await self.cog._save_conversation(self.ctx.author.id, active_id, conv)

        await interaction.response.send_message(
            tr(self.lang, "CONFIG_MODEL_SET_OK", model=model_choice),
            ephemeral=True,
        )

        if isinstance(self.view, ConversationMenuView):
            await self.view.refresh_content(interaction, update_response=True)


class ConversationModelSearchModal(discord.ui.Modal):
    """Modal to search for models in conversation view."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        # Tries to use translations but falls back safely
        title = tr(lang, "CONFIG_SEARCH_MODAL_TITLE")
        if title.startswith("KeyError"):
            title = "Search Models"

        super().__init__(title=title)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

        label = tr(lang, "CONFIG_SEARCH_MODAL_LABEL")
        if label.startswith("KeyError"):
            label = "Model Name"

        placeholder = tr(lang, "CONFIG_SEARCH_MODAL_PLACEHOLDER")
        if placeholder.startswith("KeyError"):
            placeholder = "e.g. claude"

        self.query = discord.ui.TextInput(
            label=label,
            style=discord.TextStyle.short,
            placeholder=placeholder,
            required=True,
            max_length=50,
        )
        self.add_item(self.query)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        query = self.query.value.strip()
        new_options = await self.cog._build_model_select_options(query)

        if not new_options:
            msg = tr(self.lang, "CONFIG_SEARCH_NO_RESULTS", query=query)
            if msg.startswith("KeyError"):
                msg = f"No models found matching '{query}'"
            await interaction.response.send_message(msg, ephemeral=True)
            return

        # Update the view
        if hasattr(self, "origin_view") and self.origin_view:
            view = self.origin_view
            for child in view.children:
                if isinstance(child, ConversationModelSelect):
                    child.options = new_options
                    child.placeholder = f"Found {len(new_options)} matches for '{query}'"
                    break

            await interaction.response.edit_message(view=view)
        else:
             await interaction.response.send_message(
                "❌ Error: Lost context.", ephemeral=True
            )


class ConversationModelSearchButton(discord.ui.Button):
    """Button to search models in conversation view."""

    def __init__(self, cog: PoeHub, ctx: red_commands.Context, lang: str) -> None:
        label = tr(lang, "CONFIG_BTN_SEARCH_MODEL")
        if label.startswith("KeyError"):
            label = "Search Models"

        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            emoji="🔍",
            row=2,
        )
        self.cog = cog
        self.ctx = ctx
        self.lang = lang

    async def callback(self, interaction: discord.Interaction) -> None:
        modal = ConversationModelSearchModal(self.cog, self.ctx, self.lang)
        modal.origin_view = self.view
        await interaction.response.send_modal(modal)


class ConversationMenuView(discord.ui.View):
    """Interactive menu to switch, delete, and clear conversations."""

    def __init__(
        self,
        cog: PoeHub,
        ctx: red_commands.Context,
        lang: str,
        back_callback: Callable[[discord.Interaction], Awaitable[None]] | None = None,
    ) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx
        self.lang = lang
        self.back_callback = back_callback
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                tr(self.lang, "RESTRICTED_MENU"),
                ephemeral=True,
            )
            return False
        return True

    async def build_options(self) -> tuple[list[discord.SelectOption], str]:
        """Return (options, active_conversation_id)."""
        if not self.cog.conversation_manager:
            return [
                discord.SelectOption(
                    label=tr(self.lang, "CONV_DEFAULT_LABEL"),
                    value="default",
                    default=True,
                )
            ], "default"

        conversations = await self.cog.config.user(self.ctx.author).conversations()
        active_conv_id = await self.cog.context_service.get_active_conversation_id(self.ctx.author.id)

        options: list[discord.SelectOption] = []
        if conversations:
            sorted_convs = []
            for conv_id, enc_data in conversations.items():
                data = self.cog.conversation_manager.process_conversation_data(enc_data)
                if data:
                    sorted_convs.append((conv_id, data))

            sorted_convs.sort(key=lambda x: x[1].get("created_at", 0), reverse=True)
            for conv_id, data in sorted_convs[:25]:
                title = data.get("title", conv_id)
                desc = tr(
                    self.lang,
                    "CONV_OPTION_DESC",
                    count=len(data.get("messages", [])),
                )
                is_active = conv_id == active_conv_id
                emoji = "🟢" if is_active else "💬"
                options.append(
                    discord.SelectOption(
                        label=title[:100],
                        value=conv_id,
                        description=desc,
                        default=is_active,
                        emoji=emoji,
                    )
                )

        if not options:
            options.append(
                discord.SelectOption(
                    label=tr(self.lang, "CONV_DEFAULT_LABEL"),
                    value="default",
                    default=True,
                    emoji="🟢",
                )
            )

        return options, active_conv_id

    async def refresh_content(
        self,
        interaction: discord.Interaction | None = None,
        update_response: bool = False,
    ) -> discord.Embed:
        """Rebuild dropdowns/buttons and (optionally) update the message."""
        self.clear_items()

        options, active_id = await self.build_options()
        self.add_item(SwitchConversationSelect(self.cog, self.ctx, options, self.lang))

        # Model Selection
        # Resolve active model for conversation
        conv_temp = await self.cog._get_conversation(self.ctx.author.id, active_id)
        current_model = conv_temp.get("model") if conv_temp else None

        # Build default options (top models)
        model_ops = await self.cog._build_model_select_options()
        self.add_item(ConversationModelSelect(self.cog, self.ctx, model_ops, self.lang, current_model))

        self.add_item(NewConversationButton(self.cog, self.ctx, self.lang))
        self.add_item(DeleteButton(self.cog, self.ctx, self.lang))
        self.add_item(ClearHistoryButton(self.cog, self.ctx, self.lang))
        self.add_item(ConversationModelSearchButton(self.cog, self.ctx, self.lang))
        self.add_item(RefreshButton(self.lang))
        self.add_item(CloseMenuButton(label=tr(self.lang, "CLOSE_MENU")))

        if self.back_callback:
            self.add_item(BackButton(self.back_callback, self.lang))

        conv = await self.cog._get_conversation(self.ctx.author.id, active_id)
        if not conv:
            conv = await self.cog._get_or_create_conversation(
                self.ctx.author.id, active_id
            )

        title = conv.get("title", active_id)
        msg_count = len(conv.get("messages", []))
        embed = discord.Embed(
            title=tr(self.lang, "CONV_TITLE"),
            description=tr(self.lang, "CONV_DESC"),
            color=discord.Color.gold(),
        )
        if not current_model:
            current_model = await self.cog.config.user(self.ctx.author).model()

        embed.add_field(
            name=tr(self.lang, "CONV_FIELD_ACTIVE"),
            value=f"**{title}**\nID: `{active_id}`\n{tr(self.lang, 'CONV_OPTION_DESC', count=msg_count)}",
            inline=True,
        )
        embed.add_field(
            name="Model",
            value=f"`{current_model}`",
            inline=True,
        )

        messages = conv.get("messages") or []
        if messages:
            recent = messages[-3:]
            preview_lines = []
            for msg in recent:
                role_icon = "👤" if msg.get("role") == "user" else "🤖"
                content = preview_content(
                    msg.get("content"),
                    empty_label=tr(self.lang, "CONV_EMPTY"),
                    non_text_label=tr(self.lang, "CONV_NON_TEXT"),
                )
                preview_lines.append(f"{role_icon} {content}")
            embed.add_field(
                name=tr(self.lang, "CONV_FIELD_RECENT"),
                value="\n".join(preview_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name=tr(self.lang, "CONV_FIELD_RECENT"),
                value=tr(self.lang, "CONV_EMPTY"),
                inline=False,
            )

        if not interaction:
            return embed

        try:
            if update_response:
                if self.message:
                    await self.message.edit(embed=embed, view=self)
            else:
                if not interaction.response.is_done():
                    await interaction.response.edit_message(embed=embed, view=self)
                elif self.message:
                    await self.message.edit(embed=embed, view=self)
        except Exception as exc:  # noqa: BLE001 - best-effort UI refresh
            log.warning("Failed to refresh conversation menu: %s", exc)

        return embed
