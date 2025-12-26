# PoeHub Bilingual Help System
# PoeHub 雙語說明系統

## Overview 概述

PoeHub now supports **Traditional Chinese (繁體中文)** alongside English!
PoeHub 現在支援**繁體中文**與英文雙語！

All command help text is available in both languages.
所有指令說明文字均提供雙語版本。

---

## How to Use 如何使用

### Method 1: Built-in Help 內建說明

Use Red-DiscordBot's built-in help command:
使用 Red-DiscordBot 的內建說明指令：

```
!help PoeHub
```

This shows the cog description in both languages.
這會顯示雙語的模組說明。

```
!help ask
```

This shows detailed help for a specific command in both languages.
這會顯示特定指令的雙語詳細說明。

---

### Method 2: Custom Bilingual Help 自訂雙語說明

Use the dedicated bilingual help command:
使用專用的雙語說明指令：

```
!poehubhelp
```

**Aliases 別名:**
- `!幫助`
- `!说明`

This displays a beautiful embed with all commands organized by category in both English and Traditional Chinese.
這會顯示一個精美的嵌入訊息，按類別組織所有指令的英文和繁體中文說明。

---

## All Commands with Chinese 所有指令的中文說明

### Basic Commands 基本指令

| Command 指令 | English | 繁體中文 |
|--------------|---------|----------|
| `!ask <question>` | Ask AI with context | 向 AI 提問（包含上下文） |
| `!setmodel <name>` | Change AI model | 更改 AI 模型 |
| `!mymodel` | Check current model | 查看當前模型 |
| `!listmodels` | List all models | 列出所有模型 |
| `!searchmodels <query>` | Search models | 搜尋模型 |

### Conversation Management 對話管理

| Command 指令 | English | 繁體中文 |
|--------------|---------|----------|
| `!newconv [title]` | Create new conversation | 建立新對話 |
| `!switchconv <id>` | Switch conversations | 切換對話 |
| `!listconv` | List all conversations | 列出所有對話 |
| `!currentconv` | Show active conversation | 顯示當前對話 |
| `!clear_history` | Clear active conversation history | 清除當前對話紀錄 |
| `!deleteconv <id>` | Delete conversation | 刪除對話 |
| `!delete_all_conversations` | Delete ALL conversations | 刪除所有對話 |

### Settings & Prompts 設定與提示詞

| Command 指令 | English | 繁體中文 |
|--------------|---------|----------|
| `!poeconfig` | Open interactive config menu | 開啟互動式設定面板 |
| `!setprompt <text>` | Set personal system prompt | 設定個人系統提示詞 |
| `!myprompt` | View current system prompt | 查看當前系統提示詞 |
| `!clearprompt` | Clear personal prompt | 清除個人提示詞 |
| `!purge_my_data` | Delete all your data | 刪除所有資料 |
| `!poedummymode <on/off>` | Toggle dummy API mode (owner only) | 切換 Dummy API 模式（僅擁有者） |

---

## Examples 範例

### English Example 英文範例

```
User: !ask What is Python?
Bot: Python is a high-level programming language...

User: !newconv Python Learning
Bot: ✅ Created and switched to new conversation: Python Learning

User: !listconv
Bot: [Shows all conversations]
```

### Chinese Example 中文範例

```
使用者: !ask Python 是什麼？
機器人: Python 是一種高階程式語言...

使用者: !newconv Python 學習
機器人: ✅ Created and switched to new conversation: Python 學習

使用者: !listconv
機器人: [顯示所有對話]
```

---

## Language Features 語言功能

### What's Bilingual 雙語內容

✅ **All command docstrings** 所有指令文檔字串
- Every command shows help in both languages
  每個指令都顯示雙語說明

✅ **Custom help command** 自訂說明指令
- `!poehubhelp` shows organized bilingual reference
  顯示組織化的雙語參考

✅ **Command aliases** 指令別名
- `!幫助` and `!说明` work as shortcuts
  作為快捷方式使用

### What Uses Bot Language 使用機器人語言

❌ **Bot responses** 機器人回應
- AI responses use the model's language
  AI 回應使用模型的語言
- You can ask in any language
  您可以使用任何語言提問

❌ **Error messages** 錯誤訊息
- Currently English only
  目前僅英文

---

## Tips for Chinese Users 中文使用者提示

### Asking Questions in Chinese 用中文提問

```
!ask 請解釋量子計算
!ask 什麼是機器學習？
!ask 用 Python 寫一個排序函數
```

The AI will respond in Chinese if you ask in Chinese!
如果您用中文提問，AI 會用中文回應！

### Creating Chinese Conversations 建立中文對話

```
!newconv Python 學習
!newconv 機器學習筆記
!newconv 專案規劃討論
```

Use Chinese titles for better organization.
使用中文標題以更好地組織。

### Mixing Languages 混合語言

You can:
您可以：
- Ask in English, get English responses
  用英文問，得到英文回應
- Ask in Chinese, get Chinese responses
  用中文問，得到中文回應
- Switch languages anytime
  隨時切換語言

---

## Help Command Comparison 說明指令比較

### `!help PoeHub`
- Shows Red-DiscordBot's standard help
  顯示 Red-DiscordBot 的標準說明
- Lists all commands with brief descriptions
  列出所有指令及簡要說明
- Bilingual docstrings included
  包含雙語文檔字串

### `!help <command>`
- Shows detailed help for specific command
  顯示特定指令的詳細說明
- Includes usage examples
  包含使用範例
- Full bilingual text
  完整雙語文字

### `!poehubhelp` (or `!幫助`)
- Custom organized view
  自訂組織視圖
- Grouped by category
  按類別分組
- Beautiful embed format
  精美的嵌入格式
- Quick reference
  快速參考

---

## Technical Details 技術細節

### Implementation 實現方式

1. **Bilingual Docstrings** 雙語文檔字串
   - All command docstrings contain both languages
     所有指令文檔字串包含雙語
   - Format: English line, Chinese line
     格式：英文行，中文行

2. **Custom Help Command** 自訂說明指令
   - Implements `!poehubhelp` with Discord embed
     使用 Discord 嵌入實現 `!poehubhelp`
   - Aliases support Chinese characters
     別名支援中文字符

3. **Unicode Support** Unicode 支援
   - Full Traditional Chinese character support
     完整繁體中文字符支援
   - Works in all Discord clients
     在所有 Discord 客戶端中運作

### Why This Approach 為何採用這種方式

✅ **Simple** 簡單
- No complex localization system needed
  無需複雜的本地化系統

✅ **Always Available** 始終可用
- Both languages always shown
  始終顯示雙語

✅ **No Configuration** 無需配置
- Works immediately after reload
  重新載入後立即運作

✅ **Maintainable** 易於維護
- All translations in one place
  所有翻譯集中在一處

---

## FAQ 常見問題

### Q: Can I choose to see only one language? 我可以只看一種語言嗎？
A: Currently, both languages are shown together for maximum accessibility.
目前兩種語言一起顯示以獲得最大可訪問性。

### Q: Will the AI respond in Chinese? AI 會用中文回應嗎？
A: Yes! Ask in Chinese and the AI will respond in Chinese.
會！用中文提問，AI 會用中文回應。

### Q: Are there Simplified Chinese commands? 有簡體中文指令嗎？
A: The `!说明` alias supports Simplified Chinese users too.
`!说明` 別名也支援簡體中文使用者。

### Q: Can I contribute more translations? 我可以貢獻更多翻譯嗎？
A: Yes! Edit the docstrings in `poehub.py` to add more languages.
可以！編輯 `poehub.py` 中的文檔字串以添加更多語言。

---

## Future Enhancements 未來增強功能

Planned features 計劃功能:
- Simplified Chinese support 簡體中文支援
- Japanese support 日文支援
- Korean support 韓文支援
- Language preference setting 語言偏好設定
- Localized error messages 本地化錯誤訊息

---

**Version 版本:** 1.2.0  
**Last Updated 最後更新:** December 23, 2025  
**Languages 語言:** English 英文, Traditional Chinese 繁體中文

