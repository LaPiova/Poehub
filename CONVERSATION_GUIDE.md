# PoeHub Conversation Management Guide

## 🎯 Overview

PoeHub now supports **persistent conversation context**! Each user has their own separate conversations, and the AI maintains context across multiple messages within each conversation.

## ✨ Key Features

- **Multiple Conversations**: Create as many separate conversations as you need
- **Persistent Context**: The AI remembers previous messages in each conversation
- **Per-User Storage**: Each Discord user has their own isolated conversations
- **Encrypted Storage**: All conversation data is encrypted using Fernet
- **Easy Management**: Simple commands to create, switch, list, and delete conversations

---

## 📋 Commands

### View Current Conversation
```
!currentconv
```
Shows details about your active conversation including:
- Conversation title and ID
- Number of messages
- Recent message preview

### Create New Conversation
```
!newconv [title]
```
Creates a new conversation and automatically switches to it.

**Examples:**
```
!newconv                    # Creates "Conversation conv_1234567"
!newconv Python Help        # Creates "Python Help"
!newconv Project Planning   # Creates "Project Planning"
```

### List All Conversations
```
!listconv
```
Shows all your saved conversations with:
- Title and ID
- Number of messages
- Creation date
- Active conversation indicator (🟢)

### Switch Conversations
```
!switchconv <conversation_id>
```
Switch to a different conversation to continue where you left off.

**Example:**
```
!listconv                          # See your conversations
!switchconv conv_1703251234       # Switch to that conversation
```

### Delete Conversation
```
!deleteconv <conversation_id>
```
Permanently delete a conversation (requires confirmation).

**Note:** You cannot delete your active conversation. Switch to another one first.

---

## 💬 How It Works

### Asking Questions

When you use `!ask`, your question is automatically added to your active conversation:

```
!ask What is Python?
```

The AI's response is also saved, maintaining context for future questions:

```
!ask Can you show me an example?
# AI remembers you were asking about Python
```

### Conversation Flow Example

```
# Create a conversation for Python help
!newconv Python Learning

# Ask questions - each builds on the previous
!ask What is a list in Python?
!ask How do I add items to it?
!ask Show me an example with a loop

# Create a new conversation for a different topic
!newconv JavaScript Help

# This conversation has no memory of Python discussion
!ask What is an array in JavaScript?

# Switch back to Python conversation
!listconv
!switchconv conv_1703251234

# Continue Python discussion - AI remembers the context
!ask Can I use list comprehensions?
```

---

## 🔄 Use Cases

### 1. **Separate Projects**
Create different conversations for each project you're working on:
```
!newconv Backend API Development
!newconv Frontend React App
!newconv Database Design
```

### 2. **Topic-Based Learning**
Keep learning materials organized by subject:
```
!newconv Machine Learning Basics
!newconv Python Advanced Topics
!newconv Linux System Administration
```

### 3. **Long-Running Discussions**
Continue complex discussions over multiple sessions:
```
# Day 1
!newconv Website Design Ideas
!ask I want to redesign my website...

# Day 2  
!switchconv conv_1703251234
!ask Following up on yesterday's design ideas...
```

### 4. **Code Development**
Track progress on coding problems:
```
!newconv Sorting Algorithm Help
!ask How do I implement quicksort?
!ask Can you explain the partition step?
!ask Show me how to handle edge cases
```

---

## 📊 Context Window Management

### Message Limits
- Each conversation stores up to **50 messages** (25 exchanges)
- Older messages are automatically removed when limit is reached
- This prevents context window overflow

### Why 50 Messages?
- Most AI models have context limits (e.g., 4000-8000 tokens)
- 50 messages typically stays within these limits
- Provides enough context for meaningful conversations
- Prevents excessive storage use

### Manual Management
If you want to start fresh within a topic:
```
!newconv Python Help - Part 2
# Fresh context but you can reference old conv ID
```

---

## 🔒 Privacy & Security

### Encryption
- All conversation data is encrypted using Fernet (AES-128)
- Messages are encrypted before being saved
- Only decrypted when you access them

### Per-User Isolation
- Each Discord user has completely separate conversations
- Users cannot see each other's conversations
- User ID is used as the isolation key

### Data Deletion
Delete a specific conversation:
```
!deleteconv conv_1703251234
```

Delete ALL your data (including all conversations):
```
!purge_my_data
```

---

## 🎓 Best Practices

### 1. **Use Descriptive Titles**
```
✅ !newconv React Hooks Tutorial
❌ !newconv Conversation 1
```

### 2. **Create Topic-Specific Conversations**
Don't mix unrelated topics in one conversation
```
✅ Separate: "Python Help" and "JavaScript Help"
❌ Mixed: "Programming Help" with both Python and JS
```

### 3. **Switch Conversations When Changing Topics**
```
# Discussing React
!ask How do I use useState?

# Need to switch to Python  
!newconv Python Async Programming
!ask How does asyncio work?
```

### 4. **Review Before Deleting**
Use `!currentconv` to review conversation contents before deleting

### 5. **Keep Active Conversations Manageable**
Delete old conversations you no longer need:
```
!listconv                    # Review all conversations
!deleteconv old_conv_id      # Clean up finished ones
```

---

## 💡 Tips & Tricks

### Quick Status Check
```
!currentconv
# Shows your active conversation and recent messages
```

### Find Old Conversations
```
!listconv
# Shows all conversations with creation dates
# Copy the ID of the conversation you want
!switchconv conv_1703251234
```

### Starting Fresh While Keeping History
```
# Don't delete - just create new
!newconv Topic Name - Part 2
# Old conversation still accessible if needed
```

### Context Reset Within Conversation
If you want to change direction but keep the conversation:
```
!ask Let's start a new subtopic: [your question]
```

The AI can adapt to topic shifts within a conversation.

---

## ⚙️ Technical Details

### Storage Structure
```json
{
  "conversation_id": {
    "id": "conv_1703251234",
    "title": "Python Learning",
    "created_at": 1703251234.567,
    "messages": [
      {
        "role": "user",
        "content": "What is Python?",
        "timestamp": 1703251234.567
      },
      {
        "role": "assistant",
        "content": "Python is...",
        "timestamp": 1703251235.789
      }
    ]
  }
}
```

### Message Roles
- `user`: Your messages
- `assistant`: AI responses
- Both are sent to the API for context

### Conversation IDs
- Format: `conv_` + Unix timestamp
- Example: `conv_1703251234`
- Guaranteed unique per creation time

---

## 🐛 Troubleshooting

### "Conversation not found"
```
!listconv
# Make sure you're using the correct ID
# IDs are case-sensitive
```

### "Cannot delete active conversation"
```
!newconv Temporary
!deleteconv old_conv_id
# Or switch to a different conversation first
```

### Lost Track of Conversations
```
!listconv
# Shows all your conversations with details
```

### Want to Start Fresh
```
!newconv
# Creates a brand new conversation
# Old ones remain accessible
```

---

## 📈 Upgrade from Previous Version

If you were using PoeHub before this update:

### Automatic Migration
- Old data is preserved
- A "default" conversation is created automatically
- Your first `!ask` will use this default conversation

### Manual Organization
After upgrade, organize your conversations:
```
!currentconv               # See your default conversation
!newconv Main Conversation  # Create a better-named one
!listconv                  # See all conversations
```

---

## 🎯 Summary

| Command | Purpose | Example |
|---------|---------|---------|
| `!ask` | Ask with context | `!ask Explain recursion` |
| `!newconv` | Create conversation | `!newconv Python Help` |
| `!listconv` | List all conversations | `!listconv` |
| `!switchconv` | Switch conversation | `!switchconv conv_123` |
| `!deleteconv` | Delete conversation | `!deleteconv conv_123` |
| `!currentconv` | Show active conversation | `!currentconv` |

---

**Version:** 1.1.0  
**Last Updated:** December 22, 2025  
**Feature:** Persistent Conversation Context

