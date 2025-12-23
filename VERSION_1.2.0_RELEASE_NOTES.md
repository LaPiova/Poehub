# PoeHub v1.2.0 Release Notes
# PoeHub v1.2.0 發布說明

**Release Date:** December 22, 2025  
**發布日期：** 2025年12月22日

---

## 🎯 Major New Feature: System Prompts

### What's New 新功能

PoeHub now supports **System Prompts** - customize how the AI responds to you!

PoeHub 現在支援**系統提示詞** - 自訂 AI 如何回應您！

#### For Bot Owners 機器人擁有者

Set a **default system prompt** that applies to all users:

為所有用戶設定**預設系統提示詞**：

```
!setdefaultprompt You are a helpful AI assistant. Always be polite and concise.
```

This ensures consistent AI behavior across your server while allowing individual users to override it if they want.

這確保了整個伺服器上一致的 AI 行為，同時允許個別用戶在需要時覆蓋它。

#### For All Users 所有用戶

Set your **personal system prompt** to customize AI behavior just for you:

設定您的**個人系統提示詞**以自訂 AI 僅為您服務：

```
!setprompt You are a Python programming expert. Provide code examples with detailed explanations.
```

Your personal prompt:
- Overrides the default prompt
- Is completely separate from other users
- Applies to all your conversations
- Is stored encrypted for security

您的個人提示詞：
- 覆蓋預設提示詞
- 與其他用戶完全分離
- 適用於您的所有對話
- 加密儲存以確保安全

---

## 📋 New Commands

### Owner Commands (2)

| Command | Description |
|---------|-------------|
| `!setdefaultprompt <text>` | Set default system prompt for all users |
| `!cleardefaultprompt` | Remove the default prompt |

### User Commands (4)

| Command | Description |
|---------|-------------|
| `!setprompt <text>` | Set your personal system prompt |
| `!myprompt` | View your current prompt (personal or default) |
| `!clearprompt` | Clear your personal prompt |
| `!poehubhelp` | Updated to include prompt commands |

---

## 🎮 Example Use Cases

### Use Case 1: Coding Assistant

```
!setprompt You are an expert programmer. Always provide:
1. Code examples in Python 3.11+
2. Detailed explanations
3. Best practices and potential issues
4. Alternative approaches when relevant
```

### Use Case 2: Language Learning

```
!setprompt You are a language tutor for English learners. Always:
- Use simple vocabulary
- Explain grammar clearly
- Provide example sentences
- Correct mistakes politely
```

### Use Case 3: Creative Writing

```
!setprompt You are a creative writing coach. Help with:
- Story ideas and plot development
- Character building
- Writing style and tone
- Constructive feedback
```

### Use Case 4: Chinese Responses

```
!setprompt 你是一位專業的 AI 助手。請務必：
- 用繁體中文回答所有問題
- 提供清晰的解釋和實例
- 保持友善和專業的語氣
- 當討論技術話題時提供程式碼範例
```

---

## 🔒 Privacy & Security

### Complete User Isolation

- **Your prompt is yours alone** - Other users cannot see or be affected by your prompt
- **Encrypted storage** - All prompts are encrypted using Fernet (AES-128)
- **No cross-contamination** - Even if you and another user ask the same question, you each get responses based on your own prompts

### 完全用戶隔離

- **您的提示詞只屬於您** - 其他用戶無法看到或受您的提示詞影響
- **加密儲存** - 所有提示詞使用 Fernet (AES-128) 加密
- **無交叉污染** - 即使您和其他用戶問同樣的問題，您各自都會根據自己的提示詞獲得回應

---

## 🔧 Technical Details

### How It Works

1. **Priority System**:
   - Personal prompt (if set) → Used first
   - Default prompt (if set) → Used if no personal prompt
   - No prompt → AI uses default behavior

2. **Integration**:
   - Automatically applied to `!ask` command
   - Automatically applied to DM responses
   - Prepended as `{"role": "system", "content": "your prompt"}`

3. **Storage**:
   - Global config: `default_system_prompt`
   - Per-user config: `system_prompt`
   - Both encrypted at rest

### Configuration Schema

```python
# Global (Owner only)
default_global = {
    "api_key": None,
    "encryption_key": None,
    "base_url": "https://api.poe.com/v1",
    "default_system_prompt": None  # NEW!
}

# Per-User
default_user = {
    "model": "Claude-3.5-Sonnet",
    "private_mode": False,
    "conversations": {},
    "active_conversation": "default",
    "system_prompt": None  # NEW!
}
```

---

## 📊 Statistics

- **New Commands**: 6 commands
- **Code Changes**: ~160 lines added to `poehub.py`
- **New Documentation**: `SYSTEM_PROMPTS_GUIDE.md` (comprehensive bilingual guide)
- **Updated Files**: 4 files (poehub.py, README.md, CHANGELOG.md, 00-START_HERE.md)
- **Total Commands**: 19 commands (up from 13)
- **File Size**: 49 KB (1268 lines)

---

## 🚀 Upgrade Instructions

### For Existing Installations

1. **Pull the latest code** (if using git):
   ```bash
   cd ~/Poehub
   git pull
   ```

2. **Sync to red-cogs**:
   ```bash
   ~/Poehub/sync_to_red.sh
   ```

3. **Reload in Discord**:
   ```
   !reload poehub
   ```

4. **Test the new features**:
   ```
   !myprompt
   !setprompt You are a helpful assistant
   !ask Hello!
   !myprompt
   ```

### For New Installations

Follow the standard installation in `README.md` or `00-START_HERE.md`. All new features are included by default!

---

## 📚 Documentation

### New Documentation

- **SYSTEM_PROMPTS_GUIDE.md**: Comprehensive guide with:
  - Detailed explanations
  - Multiple examples
  - Use cases and scenarios
  - Best practices
  - FAQ
  - Bilingual (English/Traditional Chinese)

### Updated Documentation

- **README.md**: Updated with new commands and features
- **CHANGELOG.md**: Full v1.2.0 changelog
- **00-START_HERE.md**: Updated command reference

---

## 🎓 Getting Started with System Prompts

### Step 1: Check Current Status

```
!myprompt
```

This shows whether you have a personal prompt, the default prompt, or no prompt.

### Step 2: Set Your Prompt

```
!setprompt You are a [role]. Always [behavior instructions].
```

Example:
```
!setprompt You are a helpful coding assistant. Always provide Python code examples with comments.
```

### Step 3: Test It

```
!ask What is a list comprehension?
```

The AI will respond according to your prompt!

### Step 4: Adjust as Needed

```
!setprompt You are a senior Python developer. Be detailed and technical.
```

You can change your prompt anytime without losing conversation history.

### Step 5: View or Clear

```
!myprompt        # View current prompt
!clearprompt     # Clear your personal prompt
```

---

## 💡 Tips & Best Practices

### Writing Effective Prompts

✅ **Be Specific**: "You are a Python expert specializing in data science"  
❌ **Too Vague**: "Be nice"

✅ **Define Behavior**: "Always provide code examples with explanations"  
❌ **Too Generic**: "Help me"

✅ **Set Tone**: "Be friendly and encouraging for beginners"  
❌ **Unclear**: "Talk normal"

✅ **Specify Format**: "Use bullet points for lists, code blocks for code"  
❌ **No Structure**: "Answer questions"

### Prompt Length

- **Optimal**: 100-500 characters
- **Maximum**: No hard limit, but shorter is better
- **Impact**: Very long prompts may increase API token usage

### Testing Prompts

1. Start with a simple prompt
2. Test with a basic question
3. Refine based on results
4. Keep iterating until you get desired behavior

---

## 🔄 Backward Compatibility

### Existing Users

- **No breaking changes** - All existing functionality works exactly as before
- **Opt-in feature** - If you don't set a prompt, behavior is unchanged
- **Data preserved** - All conversations and settings remain intact
- **Automatic migration** - No manual steps required

### Legacy Behavior

If neither owner nor user sets a prompt:
- AI behaves exactly as it did in v1.1.0
- No changes to responses
- No additional token usage

---

## 🐛 Known Issues

None at this time. If you encounter any issues, please report them!

---

## 🙏 Feedback Welcome

We'd love to hear your feedback on this new feature:

- How are you using system prompts?
- What prompt templates work well for you?
- Any suggestions for improvements?

---

## 📅 What's Next?

Potential future enhancements (not confirmed):

- Per-conversation prompts (different prompt for each conversation)
- Prompt templates library
- Prompt sharing between users
- Prompt history/versioning
- Statistics on prompt effectiveness

---

## 🎉 Enjoy!

We hope you find system prompts useful for customizing your AI experience!

Try it out and let the AI know exactly how you want it to help you.

---

**Version**: 1.2.0  
**Previous Version**: 1.1.0  
**Release Type**: Feature Update  
**Status**: ✅ Stable, Production-Ready

**Links**:
- Full Changelog: `CHANGELOG.md`
- System Prompts Guide: `SYSTEM_PROMPTS_GUIDE.md`
- Main Documentation: `README.md`
- Quick Start: `00-START_HERE.md`

