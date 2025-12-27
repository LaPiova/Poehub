# PoeHub - Red-DiscordBot Cog for LLM APIs

A comprehensive Red-DiscordBot Cog that integrates with **Poe**, **OpenAI**, **Anthropic (Claude)**, **Google (Gemini)**, **DeepSeek**, and **OpenRouter** APIs.

## Features

- 🤖 **Multi-Provider Support**: Switch between Poe, OpenAI, Anthropic, Google Gemini, DeepSeek, and OpenRouter
- 🔄 **Unified Interface**: Use one set of commands regardless of the backend provider
- 💬 **Conversation Context**: AI remembers up to 50 messages per conversation, multiple conversations per user
- 📝 **System Prompts**: Owner can set default prompt, users can set personal prompts (fully isolated per user)
- 🔒 **Encrypted Data Storage**: All local data encrypted using Fernet encryption
- 🖼️ **Image Support**: Send images with your queries using OpenAI Vision format
- 💬 **DM Support**: Chat with the bot directly via Discord DMs
- 🧹 **Data Purging**: Users can delete their data anytime
- 🌊 **Streaming Responses**: Real-time response streaming with 2-second update intervals
- 🌐 **Bilingual Help**: Full Traditional Chinese (繁體中文) support
- 🔄 **Auto-Start**: Optional systemd service for automatic bot start on server reboot

## Before You Start

- ✅ **Discord Bot Token** – create a bot in the [Discord Developer Portal](https://discord.com/developers/applications), invite it to your server, and keep the token ready for `redbot-setup`.
- 🔑 **Poe API Key** – required for live conversations. For local debugging without a key, set `POEHUB_ENABLE_DUMMY_MODE=1` first and then enable dummy mode with `[p]poedummymode on`.
- 🐍 **Python 3.8.1–3.11** – Red-DiscordBot is incompatible with Python 3.12+. The deployment scripts create a compatible virtualenv automatically.
- 💻 **Supported OS** – Ubuntu 22.04/24.04 (primary) or Arch Linux. Use the matching deployment script below.

## Installation

### Option 1: Automated Deployment (Recommended)

Run the deployment script on a fresh system:

```bash
cd ~/Poehub
# Ubuntu / Debian-based
./deploy_poe_bot.sh

# Arch Linux
./deploy_poe_bot_on_arch.sh
```

**Important:** Red-DiscordBot requires Python 3.8.1 to 3.11.x (NOT 3.12+). 

If you see errors about "No matching distribution found for Red-DiscordBot", run:
```bash
./fix_python_version.sh
```

This will:
- Install all system dependencies (including Python 3.11 if needed)
- Create a Python virtual environment with the correct version
- Install Red-DiscordBot and required packages
- Set up the PoeHub cog
- Create startup scripts

### Option 2: Manual Installation

1. **Install Red-DiscordBot**:
```bash
python3 -m venv ~/.redenv
source ~/.redenv/bin/activate
pip install Red-DiscordBot openai anthropic google-generativeai cryptography
```

2. **Set up Red-DiscordBot**:
```bash
redbot-setup
```

3. **Install PoeHub Cog**:
```bash
~/Poehub/sync_to_red.sh
```

4. **Start the bot**:
```bash
./start_bot.sh
```

**Note**: After making changes to the cog, run `sync_to_red.sh` again and use `!reload poehub` in Discord.

## Discord Configuration

Once the bot is running, configure it in Discord:

1. **Add the custom cog path** (use absolute path):
```
[p]addpath /home/<your-user>/red-cogs
```
*Note: Relative paths like ~/red-cogs are not supported*

2. **Load the PoeHub cog**:
```
[p]load poehub
```

3. **Set your Provider and API key** (bot owner only):
```
[p]setprovider <poe|openai|anthropic|google|deepseek|openrouter>
[p]setapikey <provider> <your_key>
```
Example:
```
[p]setprovider openai
[p]setapikey openai sk-...
```

4. **Open the interactive config panel**:
```
[p]poeconfig
```
Use the dropdown + buttons to change your default model, set/clear personal prompts, or (if you're the owner) toggle dummy mode without memorizing every text command.

> Dummy controls only appear after you set `POEHUB_ENABLE_DUMMY_MODE=1`. By default the flag is `0`, so release builds stay clean until you opt in.

## Offline Dummy Mode (No API Key)

Need to debug commands before you have a real API key? After setting `POEHUB_ENABLE_DUMMY_MODE=1`, enable the dummy client:

```
[p]setprovider dummy
```

PoeHub will return local stub replies while the rest of the workflow (conversations, prompts, permissions) stays identical. Switch back to a live API when you're ready:

```
[p]setprovider poe
```

Use this workflow to validate deployments, Discord permissions, and data storage without touching the live Poe service.

### Enabling Dummy Mode (Opt-in)

Dummy mode is hidden by default (`POEHUB_ENABLE_DUMMY_MODE=0`). To expose the offline workflow on a dev box, set the variable before launching Red:

```bash
export POEHUB_ENABLE_DUMMY_MODE=1  # or add Environment=POEHUB_ENABLE_DUMMY_MODE=1 to your systemd unit
./start_bot.sh
```

Once enabled:
- `[p]poedummymode` and the config button appear for the bot owner
- The cog lets you choose between live Poe API and the local stub
- Help embeds/docs mention the dummy commands

Set `POEHUB_ENABLE_DUMMY_MODE=0` (or unset it) again when shipping to another server so users only see the live workflow.

## Usage

### Basic Commands

#### Ask a Question
```
[p]ask How does quantum computing work?
```

You can also attach images to your questions!

#### Set Your Preferred Model
```
[p]setmodel GPT-4o
```

#### Check Current Model
```
[p]mymodel
```

#### List Available Models (Live from Poe API)
```
[p]listmodels
```

Force refresh the model list:
```
[p]listmodels refresh
```

#### Search for Specific Models
```
[p]searchmodels claude
[p]searchmodels gpt
[p]searchmodels llama
```

#### Set System Prompt
```
[p]setprompt You are a helpful coding assistant. Always provide examples.
```
Customize AI behavior with your personal system prompt. Overrides the default prompt set by bot owner.

#### View Current Prompt
```
[p]myprompt
```
See your active system prompt (personal or default).

#### Clear Personal Prompt
```
[p]clearprompt
```
Remove your personal prompt and revert to the default.

#### Create New Conversation
```
[p]newconv Python Learning
```
Start a fresh conversation with a title.

#### Switch Conversations
```
[p]switchconv conv_1734851234
```
Switch to a different conversation by ID.

#### List All Conversations
```
[p]listconv
```
View all your saved conversations.

#### Clear Conversation History
```
[p]clear_history
```
Clear all messages in the current conversation while keeping the conversation itself.

#### Delete Conversation
```
[p]deleteconv conv_1734851234
```
Permanently delete a conversation.

#### Delete All Conversations
```
[p]delete_all_conversations
```
Delete ALL your conversation history. This cannot be undone.

#### Purge Your Data
```
[p]purge_my_data
```
Deletes all your stored preferences and data.

### Owner Commands

#### Set Default System Prompt
```
[p]setdefaultprompt You are a helpful AI assistant. Be concise and accurate.
```
Sets a default prompt that all users will use unless they set their own.

#### Clear Default Prompt
```
[p]cleardefaultprompt
```
Removes the default system prompt.

#### Toggle Dummy Mode (Owner Only, if enabled)
```
[p]poedummymode on
[p]poedummymode off
```
Quickly switch between the offline dummy client and the real Poe API. This command is available only when `POEHUB_ENABLE_DUMMY_MODE=1`.

### DM Support

Simply send a message to the bot via DM (without using a command prefix) and it will respond automatically!

## Available Models

### Claude Models
- Claude-3.5-Sonnet (Default)
- Claude-3-Opus
- Claude-3-Sonnet
- Claude-3-Haiku

### GPT Models
- GPT-4o
- GPT-4-Turbo
- GPT-4
- GPT-3.5-Turbo

### Other Models
- Gemini-Pro
- Gemini-1.5-Pro
- Llama-3.1-405B

*Note: Model availability depends on your Poe subscription level*

## API Key

Get your API keys from the respective provider:
- **Poe**: https://poe.com/api_key
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **Google Gemini**: https://aistudio.google.com/app/apikey
- **DeepSeek**: https://platform.deepseek.com/
- **OpenRouter**: https://openrouter.ai/keys

The bot uses the standard OpenAI client for Poe, DeepSeek, and OpenRouter.

## Security

- **Encryption**: All local data is encrypted using `cryptography.fernet`
- **API Key Protection**: The bot automatically deletes messages containing API keys
- **User Privacy**: Users control their data and can purge it anytime

## File Structure

```
Poehub/
├── src/poehub/             # Cog package (synced to $HOME/red-cogs/poehub/)
│   ├── poehub.py           # Main cog logic
│   ├── api_client.py       # API interaction layer
│   ├── conversation_manager.py  # State and history management
│   ├── encryption.py       # Encryption helper class
│   ├── ui/                 # Discord UI views (dropdowns/buttons)
│   ├── __init__.py         # Package initialization
│   └── info.json           # Cog metadata
├── requirements.txt        # Python dependencies
├── deploy_poe_bot.sh       # Automated deployment script
├── start_bot.sh            # Bot startup script
└── README.md               # This file
```

## Running the Bot

### Interactive Mode
```bash
./start_bot.sh
```

### Background Mode (Screen)
```bash
screen -dmS ${POEHUB_SCREEN_NAME:-poebot} bash -c "source ~/.redenv/bin/activate && redbot ${POEHUB_REDBOT_INSTANCE:-PoeBot}"
screen -r ${POEHUB_SCREEN_NAME:-poebot}  # To attach to the session
```

### As a Systemd Service

1. Copy the service file:
```bash
sudo cp ~/${POEHUB_SERVICE_NAME:-poebot}.service /etc/systemd/system/
```

2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ${POEHUB_SERVICE_NAME:-poebot}.service
sudo systemctl start ${POEHUB_SERVICE_NAME:-poebot}.service
```

3. Check status:
```bash
sudo systemctl status ${POEHUB_SERVICE_NAME:-poebot}.service
```

## Troubleshooting

### Bot not responding
- Check if API key is set: `[p]poeapikey <key>`
- Verify the bot has proper Discord permissions
- Check bot logs for errors

### "API client not initialized" error
- Bot owner needs to set API key first
- Restart the cog: `[p]reload poehub`

### Can't send DMs
- User's privacy settings may block DMs
- Bot must share a server with the user

## Requirements

- Python 3.8+
- Red-DiscordBot 3.5.0+
- discord.py 2.0.0+
- openai 1.0.0+
- anthropic 0.3.0+
- google-generativeai 0.3.0+
- cryptography 41.0.0+

## License

This is a custom cog for Red-DiscordBot. Use at your own discretion.

## Support

For issues or questions:
1. Check Red-DiscordBot documentation: https://docs.discord.red/
2. Review Poe API documentation: https://developer.poe.com/
3. Check bot logs for error details

## Credits

- Built for Red-DiscordBot V3
- Uses OpenAI Python SDK
- Encryption via cryptography library
- Integrates with Poe AI platform

---

**Note**: This cog requires a valid Poe API key and Discord bot token. Model availability depends on your Poe subscription.

