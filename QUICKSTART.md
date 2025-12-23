# PoeHub Quick Start Guide

## 🚀 Phase 1: Deploy the Bot

Run on your Ubuntu server:

```bash
cd ~/Poehub
./deploy_poe_bot.sh
```

**Python Version Note:** Red-DiscordBot requires Python 3.8-3.11 (NOT 3.12+). The script will automatically try to use Python 3.11. If you encounter errors, run `./fix_python_version.sh` first.

Follow the prompts to set up your Discord bot token.

## 🤖 Phase 2: Start the Bot

```bash
~/start_bot.sh
```

Or run in background:

```bash
~/start_bot_screen.sh
```

To attach to the screen session:
```bash
screen -r poebot
```

## 💬 Phase 3: Configure in Discord

### 1. Sync the cog files (in terminal)
```bash
~/Poehub/sync_to_red.sh
```

### 2. In Discord, add the cog directory
```
!addpath /home/ubuntu/red-cogs
```
*Note: Must use absolute path, not ~/red-cogs*

### 3. Load PoeHub
```
!load poehub
```

### 3. Set API Key (Bot Owner Only)
```
[p]poeapikey YOUR_POE_API_KEY
```

Get your key from: https://poe.com/api_key

## ✨ Phase 4: Start Using!

### Basic Usage
```
[p]ask What is the meaning of life?
```

### With Images
Upload an image and ask:
```
[p]ask What's in this image?
```

### Change Model
```
[p]setmodel GPT-4o
```

### See Available Models (Fetched Live from Poe)
```
[p]listmodels
```

Search for specific models:
```
[p]searchmodels claude
```

### Enable Private Mode
```
[p]privatemode
```
Responses will be sent to your DMs!

### Chat via DM
Just send a message to the bot via DM (no command needed)!

## 🔧 Common Commands

| Command | Description |
|---------|-------------|
| `[p]ask <query>` | Ask a question to the AI |
| `[p]setmodel <name>` | Change your AI model |
| `[p]mymodel` | Check current model |
| `[p]listmodels` | Show available models |
| `[p]privatemode` | Toggle DM responses |
| `[p]purge_my_data` | Delete your data |
| `[p]help PoeHub` | Show help |

## 🎯 Popular Models

- **Claude-3.5-Sonnet** (Default) - Best for reasoning
- **GPT-4o** - Fast and capable
- **Claude-3-Opus** - Most powerful Claude
- **GPT-4-Turbo** - Advanced GPT-4

## 🛟 Troubleshooting

### Bot not responding?
1. Check if loaded: `[p]cogs`
2. Reload: `[p]reload poehub`
3. Check API key is set

### Can't load cog?
1. Verify path: `[p]paths`
2. Check files exist: `ls ~/red-cogs/poehub/`
3. Reinstall dependencies: `pip install openai cryptography`

### API errors?
- Verify your API key at https://poe.com/api_key
- Check your Poe subscription status
- Some models require paid plans

## 📊 Bot Status

Check if bot is running:
```bash
screen -ls
```

View bot logs (if using screen):
```bash
screen -r poebot
```

Press `Ctrl+A` then `D` to detach without stopping the bot.

## 🔄 Update PoeHub

```bash
cd ~/Poehub
# Pull new changes if from git
# git pull

# Copy updated files
cp poehub.py api_client.py conversation_manager.py encryption.py __init__.py info.json ~/red-cogs/poehub/

# Reload in Discord
[p]reload poehub
```

## 🎉 That's it!

You're ready to chat with Poe's AI models through Discord!

---

**Need Help?** Use `[p]help PoeHub` in Discord for command details.

