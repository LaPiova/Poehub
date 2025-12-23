# System Prompts Guide
# 系統提示詞指南

## Overview 概述

PoeHub supports **System Prompts** that allow you to customize AI behavior. System prompts are instructions that tell the AI how to respond.

PoeHub 支援**系統提示詞**，讓您可以自訂 AI 的行為。系統提示詞是告訴 AI 如何回應的指令。

### Key Features 主要功能

✅ **Owner can set a default prompt** for all users  
✅ **擁有者可以為所有用戶設定預設提示詞**

✅ **Each user can set their own personal prompt**  
✅ **每個用戶可以設定自己的個人提示詞**

✅ **Personal prompts override the default**  
✅ **個人提示詞會覆蓋預設提示詞**

✅ **Complete isolation between users**  
✅ **用戶之間完全隔離**

✅ **Prompts apply to all conversations**  
✅ **提示詞適用於所有對話**

---

## How It Works 運作方式

### Prompt Priority 提示詞優先順序

1. **Personal Prompt** (if set) → Used first
2. **Default Prompt** (if set) → Used if no personal prompt
3. **No Prompt** → AI uses default behavior

1. **個人提示詞**（如果已設定）→ 優先使用
2. **預設提示詞**（如果已設定）→ 沒有個人提示詞時使用
3. **無提示詞** → AI 使用預設行為

### User Isolation 用戶隔離

- Each user's personal prompt is stored separately
- User A's prompt does NOT affect User B
- Even if User A and User B are in the same conversation, each sees responses based on their own prompt

- 每個用戶的個人提示詞分別儲存
- 用戶 A 的提示詞不會影響用戶 B
- 即使用戶 A 和用戶 B 在同一對話中，每個人都會看到基於自己提示詞的回應

---

## Commands 指令

### For Bot Owner 機器人擁有者指令

#### Set Default Prompt 設定預設提示詞
```
!setdefaultprompt <prompt>
```

**Example 範例:**
```
!setdefaultprompt You are a helpful AI assistant. Always be polite and concise.
```

This sets a prompt that ALL users will use by default.  
這會設定一個所有用戶預設使用的提示詞。

---

#### Clear Default Prompt 清除預設提示詞
```
!cleardefaultprompt
```

Removes the default prompt. Users without personal prompts will get AI's default behavior.  
移除預設提示詞。沒有個人提示詞的用戶將獲得 AI 的預設行為。

---

### For All Users 所有用戶指令

#### Set Personal Prompt 設定個人提示詞
```
!setprompt <your custom prompt>
```

**Examples 範例:**

**For coding help 程式設計協助:**
```
!setprompt You are an expert programmer. Provide code examples with explanations. Use Python 3.11 syntax.
```

**For creative writing 創意寫作:**
```
!setprompt You are a creative writing assistant. Help with storytelling, character development, and plot ideas.
```

**For language learning 語言學習:**
```
!setprompt You are a language tutor. Explain grammar clearly and provide example sentences. Correct my mistakes politely.
```

**In Traditional Chinese 繁體中文:**
```
!setprompt 你是一位專業的程式設計助手。請用繁體中文回答，並提供程式碼範例和詳細說明。
```

---

#### View Current Prompt 查看當前提示詞
```
!myprompt
```

Shows:
- Your personal prompt (if set)
- OR the default prompt (if no personal prompt)
- OR "No prompt configured"

顯示：
- 您的個人提示詞（如果已設定）
- 或預設提示詞（如果沒有個人提示詞）
- 或「未設定提示詞」

---

#### Clear Personal Prompt 清除個人提示詞
```
!clearprompt
```

Removes your personal prompt. You'll then use:
- The default prompt (if owner set one)
- OR AI's default behavior (if no default prompt)

移除您的個人提示詞。之後您將使用：
- 預設提示詞（如果擁有者設定了）
- 或 AI 的預設行為（如果沒有預設提示詞）

---

## Use Cases 使用場景

### Scenario 1: Different Users, Different Needs
### 場景 1：不同用戶，不同需求

**Setup:**
- Owner sets no default prompt
- Alice sets: `!setprompt You are a Python expert`
- Bob sets: `!setprompt You are a creative writer`

**Result:**
- Alice's questions → Python expert responses
- Bob's questions → Creative writing responses
- Completely isolated!

**設定:**
- 擁有者不設定預設提示詞
- Alice 設定: `!setprompt You are a Python expert`
- Bob 設定: `!setprompt You are a creative writer`

**結果:**
- Alice 的問題 → Python 專家回應
- Bob 的問題 → 創意寫作回應
- 完全隔離！

---

### Scenario 2: Default with Overrides
### 場景 2：預設加覆蓋

**Setup:**
- Owner sets: `!setdefaultprompt Be helpful and concise`
- Alice keeps default (doesn't set personal prompt)
- Bob overrides: `!setprompt Be detailed and technical`

**Result:**
- Alice → Gets "helpful and concise" responses
- Bob → Gets "detailed and technical" responses

**設定:**
- 擁有者設定: `!setdefaultprompt Be helpful and concise`
- Alice 保持預設（不設定個人提示詞）
- Bob 覆蓋: `!setprompt Be detailed and technical`

**結果:**
- Alice → 獲得「有幫助且簡潔」的回應
- Bob → 獲得「詳細且技術性」的回應

---

### Scenario 3: Language-Specific Prompts
### 場景 3：語言特定提示詞

**Setup:**
- Owner sets (English default): `!setdefaultprompt Respond in English`
- Chinese user: `!setprompt 請用繁體中文回答所有問題`
- Spanish user: `!setprompt Responde en español`

**Result:**
- Each user gets responses in their preferred language
- No interference between users

**設定:**
- 擁有者設定（英文預設）: `!setdefaultprompt Respond in English`
- 中文用戶: `!setprompt 請用繁體中文回答所有問題`
- 西班牙語用戶: `!setprompt Responde en español`

**結果:**
- 每個用戶都獲得其偏好語言的回應
- 用戶之間沒有干擾

---

## Best Practices 最佳實踐

### Writing Good Prompts 撰寫良好的提示詞

✅ **Be specific** → "You are a Python expert specializing in data science"  
✅ **具體明確** → "你是專精於數據科學的 Python 專家"

✅ **Set the tone** → "Be friendly and encouraging"  
✅ **設定語氣** → "友善且鼓勵"

✅ **Define format** → "Always provide code examples"  
✅ **定義格式** → "總是提供程式碼範例"

✅ **Specify language** → "Respond in Traditional Chinese"  
✅ **指定語言** → "用繁體中文回應"

❌ **Avoid being too vague** → "Be nice"  
❌ **避免過於模糊** → "要好"

❌ **Don't make it too long** → Keep under 500 characters for best results  
❌ **不要太長** → 保持在 500 字以內效果最佳

---

### Example Prompts 範例提示詞

**For Customer Support:**
```
You are a helpful customer support agent. Be polite, empathetic, and solution-focused. Always ask clarifying questions if needed.
```

**For Technical Documentation:**
```
You are a technical writer. Provide clear, structured explanations with examples. Use headings and bullet points for clarity.
```

**For Math Tutoring:**
```
You are a patient math tutor. Break down complex problems into steps. Check understanding before moving forward.
```

**For Chinese Speakers:**
```
你是一位專業的 AI 助手。請用繁體中文回答所有問題。解釋要清楚明瞭，並提供實際範例。
```

**For Code Review:**
```
You are a senior software engineer. Review code for bugs, performance, and best practices. Suggest improvements with explanations.
```

---

## Technical Details 技術細節

### How Prompts Are Applied 提示詞如何應用

When you use `!ask` or send a DM:

1. Bot loads your conversation history
2. Bot checks for your personal system prompt
3. If no personal prompt, bot checks for default prompt
4. If prompt exists, it's prepended to messages as:
   ```json
   {"role": "system", "content": "Your prompt here"}
   ```
5. API receives: `[system_prompt, conversation_history, new_message]`

當您使用 `!ask` 或發送私訊時：

1. 機器人載入您的對話歷史記錄
2. 機器人檢查您的個人系統提示詞
3. 如果沒有個人提示詞，機器人檢查預設提示詞
4. 如果存在提示詞，它會作為以下格式添加到訊息前面：
   ```json
   {"role": "system", "content": "您的提示詞"}
   ```
5. API 接收: `[系統提示詞, 對話歷史記錄, 新訊息]`

### Storage 儲存

- **Default prompt**: Stored globally (one for all)
- **Personal prompts**: Stored per-user (encrypted)
- **Security**: All user data encrypted with Fernet

- **預設提示詞**：全域儲存（所有用戶共用一個）
- **個人提示詞**：每個用戶分別儲存（加密）
- **安全性**：所有用戶資料使用 Fernet 加密

---

## FAQ 常見問題

**Q: Does my prompt affect other users?**  
**問：我的提示詞會影響其他用戶嗎？**

A: No! Each user's prompt is completely isolated.  
答：不會！每個用戶的提示詞完全隔離。

---

**Q: Can I have different prompts for different conversations?**  
**問：我可以為不同的對話設定不同的提示詞嗎？**

A: Currently, no. Your prompt applies to all your conversations. This is a future feature.  
答：目前不行。您的提示詞適用於所有對話。這是未來的功能。

---

**Q: What happens if I switch models?**  
**問：如果我切換模型會發生什麼？**

A: Your prompt stays the same and works with any model.  
答：您的提示詞保持不變，適用於任何模型。

---

**Q: Can the bot owner see my personal prompt?**  
**問：機器人擁有者可以看到我的個人提示詞嗎？**

A: Technically yes (they have database access), but prompts are encrypted at rest.  
答：技術上可以（他們有資料庫存取權限），但提示詞在儲存時是加密的。

---

**Q: How long can my prompt be?**  
**問：我的提示詞可以多長？**

A: No hard limit, but keep it under 500 characters for best results. Very long prompts may affect API token usage.  
答：沒有硬性限制，但建議保持在 500 字以內以獲得最佳效果。非常長的提示詞可能會影響 API token 使用。

---

**Q: Can I test different prompts easily?**  
**問：我可以輕鬆測試不同的提示詞嗎？**

A: Yes! Just use `!setprompt` with a new prompt anytime. Previous conversations are not affected.  
答：可以！隨時使用 `!setprompt` 設定新提示詞。之前的對話不會受影響。

---

## Quick Reference 快速參考

| Command | Who Can Use | What It Does |
|---------|-------------|--------------|
| `!setdefaultprompt <prompt>` | Owner only | Set default for all users |
| `!cleardefaultprompt` | Owner only | Clear default prompt |
| `!setprompt <prompt>` | All users | Set personal prompt |
| `!myprompt` | All users | View current prompt |
| `!clearprompt` | All users | Clear personal prompt |

| 指令 | 誰可以使用 | 功能 |
|------|-----------|------|
| `!setdefaultprompt <提示詞>` | 僅擁有者 | 為所有用戶設定預設值 |
| `!cleardefaultprompt` | 僅擁有者 | 清除預設提示詞 |
| `!setprompt <提示詞>` | 所有用戶 | 設定個人提示詞 |
| `!myprompt` | 所有用戶 | 查看當前提示詞 |
| `!clearprompt` | 所有用戶 | 清除個人提示詞 |

---

## Tips 提示

💡 **Tip 1**: Test your prompt with a simple question to see if it behaves as expected.  
💡 **提示 1**：用簡單問題測試您的提示詞，看看是否符合預期。

💡 **Tip 2**: You can change your prompt anytime without losing conversation history.  
💡 **提示 2**：您可以隨時更改提示詞，而不會丟失對話歷史記錄。

💡 **Tip 3**: Use `!myprompt` to remind yourself what prompt you're currently using.  
💡 **提示 3**：使用 `!myprompt` 提醒自己當前使用的提示詞。

💡 **Tip 4**: If AI isn't responding as expected, check your prompt with `!myprompt` first.  
💡 **提示 4**：如果 AI 回應不如預期，先用 `!myprompt` 檢查您的提示詞。

---

🎉 **Enjoy customizing your AI experience!**  
🎉 **享受自訂您的 AI 體驗！**

