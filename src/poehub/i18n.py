"""Internationalization (i18n) strings for PoeHub.

PoeHub supports per-user language selection. Keep translations short and clear.
"""

from __future__ import annotations

from typing import Dict

LANG_EN = "en"
LANG_ZH_TW = "zh-TW"

SUPPORTED_LANGS = (LANG_EN, LANG_ZH_TW)

LANG_LABELS: Dict[str, str] = {
    LANG_EN: "English",
    LANG_ZH_TW: "繁體中文",
}


STRINGS: Dict[str, Dict[str, str]] = {
    LANG_EN: {
        # Generic / shared
        "CLOSE_MENU": "Close",
        "RESTRICTED_MENU": "This menu is restricted to the user who opened it.",
        "UPDATED": "✅ Updated.",
        # Language
        "LANG_TITLE": "🌐 Language",
        "LANG_DESC": "Choose the language PoeHub will use for menus and help.",
        "LANG_CURRENT": "Current language",
        "LANG_SET_OK": "✅ Language set to: {language}.",
        "LANG_SELECT_PLACEHOLDER": "Select language",
        # Config UI
        "CONFIG_TITLE": "⚙️ PoeHub Settings",
        "CONFIG_DESC": (
            "Use the menu below to update your default model and personal system prompt."
        ),
        "CONFIG_FIELD_MODEL": "Default Model",
        "CONFIG_FIELD_PROMPT": "Personal Prompt",
        "CONFIG_PROMPT_SET": "Set",
        "CONFIG_PROMPT_NOT_SET": "Not set",
        "CONFIG_FIELD_DUMMY": "Dummy API Mode",
        "CONFIG_DUMMY_ON": "ON (owner only)",
        "CONFIG_DUMMY_OFF": "OFF (owner only)",
        "CONFIG_SELECT_MODEL_PLACEHOLDER": "Select your default model",
        "CONFIG_BTN_SET_PROMPT": "Set Prompt",
        "CONFIG_BTN_VIEW_PROMPT": "View Prompt",
        "CONFIG_BTN_CLEAR_PROMPT": "Clear Prompt",
        "CONFIG_BTN_DUMMY_ON": "Dummy: ON",
        "CONFIG_BTN_DUMMY_OFF": "Dummy: OFF",
        "CONFIG_MODEL_SET_OK": "✅ Default model set to `{model}`.",
        "CONFIG_NO_PROMPT": "No prompt is set.",
        "CONFIG_PROMPT_EMBED_TITLE": "📝 System Prompt",
        "CONFIG_PROMPT_FIELD_PERSONAL": "Personal",
        "CONFIG_PROMPT_FIELD_DEFAULT": "Default",
        "CONFIG_PROMPT_MODAL_TITLE": "Set Personal Prompt",
        "CONFIG_PROMPT_MODAL_LABEL": "System Prompt",
        "CONFIG_PROMPT_MODAL_PLACEHOLDER": "Describe how PoeHub should respond...",
        "CONFIG_PROMPT_APPEND_PLACEHOLDER": "Current prompt exceeds {limit} characters. New text will be appended.",
        "CONFIG_PROMPT_DEFAULT_TOO_LONG": "Default prompt too long to display. Paste portions you want to use.",
        "CONFIG_PROMPT_UPDATED": "✅ Personal prompt updated.",
        "CONFIG_PROMPT_APPENDED": "✅ Personal prompt updated (appended).",
        "CONFIG_PROMPT_MODAL_EMPTY": "❌ Please enter some text.",
        "CONFIG_PROMPT_CLEARED": "✅ Personal prompt cleared.",
        "CONFIG_PROMPT_DM_SENT": "📄 Full prompt files sent to your DMs.",
        "CONFIG_PROMPT_DM_BLOCKED": "⚠️ Unable to send DM. Use !myprompt to retrieve the full text.",
        "CONFIG_DUMMY_DISABLED": "❌ Dummy API mode is disabled in this build.",
        "CONFIG_DUMMY_STATUS": "🔧 Dummy API mode is **{status}**.",
        "CONFIG_DUMMY_ENABLED_OK": "✅ Dummy API mode enabled (offline stub replies).",
        "CONFIG_DUMMY_DISABLED_OK": "✅ Dummy API mode disabled. Set a real API key with `[p]poeapikey`.",
        "MY_PROMPT_EMBED_TITLE": "📝 Your System Prompt",
        "MY_PROMPT_FIELD_PERSONAL": "🔷 Personal Prompt",
        "MY_PROMPT_FIELD_DEFAULT": "🔹 Default Prompt",
        "MY_PROMPT_FIELD_STATUS": "ℹ️ Status",
        "MY_PROMPT_STATUS_PERSONAL": "Using your personal prompt",
        "MY_PROMPT_STATUS_DEFAULT": "Using the default prompt",
        "MY_PROMPT_ATTACHMENT_PERSONAL": "📄 Full personal prompt attached as a file.",
        "MY_PROMPT_ATTACHMENT_DEFAULT": "📄 Full default prompt attached as a file.",
        "MY_PROMPT_ATTACHMENT_GENERIC": "📄 Full prompt attached as a file.",
        "MY_PROMPT_DM_BODY": "📄 Full prompt attached.",
        "MY_PROMPT_NONE": "No system prompt set",
        # Conversation UI
        "CONV_TITLE": "💬 Conversations",
        "CONV_DESC": "Switch, delete, or clear conversation history.",
        "CONV_FIELD_ACTIVE": "Active conversation",
        "CONV_FIELD_RECENT": "Recent context",
        "CONV_SWITCH_PLACEHOLDER": "Switch conversation",
        "CONV_DELETE_PLACEHOLDER": "Delete conversation",
        "CONV_BTN_CLEAR_HISTORY": "Clear history",
        "CONV_BTN_REFRESH": "Refresh",
        "CONV_BTN_NEW": "New Conversation",
        "CONV_DEFAULT_LABEL": "Default",
        "CONV_OPTION_DESC": "Messages: {count}",
        "CONV_DELETED_OK": "✅ Deleted conversation **{title}**.",
        "CONV_DELETE_FAILED": "❌ Could not delete **{title}**.",
        "CONV_HISTORY_CLEARED_OK": "✅ History cleared for **{title}**.",
        "CONV_NO_ACTIVE": "⚠️ No active conversation found.",
        "CONV_SYSTEM_NOT_INITIALIZED": "❌ System not initialized.",
        "CONV_EMPTY": "*Empty*",
        "CONV_NON_TEXT": "[non-text content]",
        # Help
        "HELP_TITLE": "📖 PoeHub Help",
        "HELP_DESC": "Core commands and tips.",
        "HELP_SECTION_CHAT": "Chat",
        "HELP_SECTION_MODELS": "Models",
        "HELP_SECTION_CONV": "Conversations",
        "HELP_SECTION_SETTINGS": "Settings",
        "HELP_LINE": "`{cmd}` — {desc}",
        "HELP_LANG_HINT": "Tip: Use `{cmd}` to switch language.",
    },
    LANG_ZH_TW: {
        # Generic / shared
        "CLOSE_MENU": "關閉",
        "RESTRICTED_MENU": "此選單僅限開啟者使用。",
        "UPDATED": "✅ 已更新。",
        # Language
        "LANG_TITLE": "🌐 語言",
        "LANG_DESC": "選擇 PoeHub 在選單與說明中使用的語言。",
        "LANG_CURRENT": "目前語言",
        "LANG_SET_OK": "✅ 語言已設定為：{language}。",
        "LANG_SELECT_PLACEHOLDER": "選擇語言",
        # Config UI
        "CONFIG_TITLE": "⚙️ PoeHub 設定",
        "CONFIG_DESC": "使用下方選單更新預設模型與個人提示詞。",
        "CONFIG_FIELD_MODEL": "預設模型",
        "CONFIG_FIELD_PROMPT": "個人提示詞",
        "CONFIG_PROMPT_SET": "已設定",
        "CONFIG_PROMPT_NOT_SET": "未設定",
        "CONFIG_FIELD_DUMMY": "Dummy API 模式",
        "CONFIG_DUMMY_ON": "開啟（僅擁有者）",
        "CONFIG_DUMMY_OFF": "關閉（僅擁有者）",
        "CONFIG_SELECT_MODEL_PLACEHOLDER": "選擇你的預設模型",
        "CONFIG_BTN_SET_PROMPT": "設定提示詞",
        "CONFIG_BTN_VIEW_PROMPT": "查看提示詞",
        "CONFIG_BTN_CLEAR_PROMPT": "清除提示詞",
        "CONFIG_BTN_DUMMY_ON": "Dummy：開啟",
        "CONFIG_BTN_DUMMY_OFF": "Dummy：關閉",
        "CONFIG_MODEL_SET_OK": "✅ 預設模型已設定為 `{model}`。",
        "CONFIG_NO_PROMPT": "目前沒有設定提示詞。",
        "CONFIG_PROMPT_EMBED_TITLE": "📝 提示詞",
        "CONFIG_PROMPT_FIELD_PERSONAL": "個人",
        "CONFIG_PROMPT_FIELD_DEFAULT": "預設",
        "CONFIG_PROMPT_MODAL_TITLE": "設定個人提示詞",
        "CONFIG_PROMPT_MODAL_LABEL": "系統提示詞",
        "CONFIG_PROMPT_MODAL_PLACEHOLDER": "描述 PoeHub 應該如何回覆...",
        "CONFIG_PROMPT_APPEND_PLACEHOLDER": "目前提示詞超過 {limit} 字元，新內容會附加在最後。",
        "CONFIG_PROMPT_DEFAULT_TOO_LONG": "預設提示詞過長，請貼上想修改的部分。",
        "CONFIG_PROMPT_UPDATED": "✅ 個人提示詞已更新。",
        "CONFIG_PROMPT_APPENDED": "✅ 個人提示詞已更新（追加）。",
        "CONFIG_PROMPT_MODAL_EMPTY": "❌ 請輸入內容。",
        "CONFIG_PROMPT_CLEARED": "✅ 個人提示詞已清除。",
        "CONFIG_PROMPT_DM_SENT": "📄 完整提示詞已傳送到你的 DM。",
        "CONFIG_PROMPT_DM_BLOCKED": "⚠️ 無法傳送 DM，請使用 !myprompt 取得完整內容。",
        "CONFIG_DUMMY_DISABLED": "❌ 此版本未開放 Dummy API 模式。",
        "CONFIG_DUMMY_STATUS": "🔧 Dummy API 模式目前為 **{status}**。",
        "CONFIG_DUMMY_ENABLED_OK": "✅ Dummy API 模式已開啟（離線回覆）。",
        "CONFIG_DUMMY_DISABLED_OK": "✅ Dummy API 模式已關閉。請用 `[p]poeapikey` 設定真實金鑰。",
        "MY_PROMPT_EMBED_TITLE": "📝 您的系統提示詞",
        "MY_PROMPT_FIELD_PERSONAL": "🔷 個人提示詞",
        "MY_PROMPT_FIELD_DEFAULT": "🔹 預設提示詞",
        "MY_PROMPT_FIELD_STATUS": "ℹ️ 狀態",
        "MY_PROMPT_STATUS_PERSONAL": "使用你的個人提示詞",
        "MY_PROMPT_STATUS_DEFAULT": "使用預設提示詞",
        "MY_PROMPT_ATTACHMENT_PERSONAL": "📄 個人提示詞完整內容已附加於檔案。",
        "MY_PROMPT_ATTACHMENT_DEFAULT": "📄 預設提示詞完整內容已附加於檔案。",
        "MY_PROMPT_ATTACHMENT_GENERIC": "📄 已附加完整提示詞。",
        "MY_PROMPT_DM_BODY": "📄 已附上完整提示詞。",
        "MY_PROMPT_NONE": "尚未設定提示詞",
        # Conversation UI
        "CONV_TITLE": "💬 對話管理",
        "CONV_DESC": "切換、刪除對話，或清除對話紀錄。",
        "CONV_FIELD_ACTIVE": "目前對話",
        "CONV_FIELD_RECENT": "最近內容",
        "CONV_SWITCH_PLACEHOLDER": "切換對話",
        "CONV_DELETE_PLACEHOLDER": "刪除對話",
        "CONV_BTN_CLEAR_HISTORY": "清除紀錄",
        "CONV_BTN_REFRESH": "重新整理",
        "CONV_BTN_NEW": "新對話",
        "CONV_DEFAULT_LABEL": "預設",
        "CONV_OPTION_DESC": "訊息: {count}",
        "CONV_DELETED_OK": "✅ 已刪除對話 **{title}**。",
        "CONV_DELETE_FAILED": "❌ 無法刪除 **{title}**。",
        "CONV_HISTORY_CLEARED_OK": "✅ 已清除 **{title}** 的對話紀錄。",
        "CONV_NO_ACTIVE": "⚠️ 找不到目前對話。",
        "CONV_SYSTEM_NOT_INITIALIZED": "❌ 系統尚未初始化。",
        "CONV_EMPTY": "＊空＊",
        "CONV_NON_TEXT": "［非文字內容］",
        # Help
        "HELP_TITLE": "📖 PoeHub 說明",
        "HELP_DESC": "常用指令與提示。",
        "HELP_SECTION_CHAT": "對話",
        "HELP_SECTION_MODELS": "模型",
        "HELP_SECTION_CONV": "對話管理",
        "HELP_SECTION_SETTINGS": "設定",
        "HELP_LINE": "`{cmd}` — {desc}",
        "HELP_LANG_HINT": "提示：使用 `{cmd}` 切換語言。",
    },
}


def tr(lang: str, key: str, **kwargs: object) -> str:
    """Translate a key into `lang` and format it.

    Args:
        lang: Language code.
        key: Translation key.
        **kwargs: Format values for the template.

    Returns:
        Localized string.
    """
    table = STRINGS.get(lang) or STRINGS[LANG_EN]
    template = table.get(key) or STRINGS[LANG_EN].get(key) or key
    try:
        return template.format(**kwargs)
    except Exception:
        # If formatting fails, return the raw template to avoid user-facing crashes.
        return template
