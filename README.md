# PoeHub - Red-DiscordBot Cog for Poe API

A comprehensive Red-DiscordBot Cog that integrates with Poe's AI platform using OpenAI-compatible API endpoints.

## Features

- 🤖 **Multi-Model Support**: Switch between Claude, GPT-4, Gemini, and other AI models (50+ models dynamically fetched)
- 💬 **Conversation Context**: AI remembers up to 50 messages per conversation, multiple conversations per user
- 📝 **System Prompts**: Owner can set default prompt, users can set personal prompts (fully isolated per user)
- 🔒 **Encrypted Data Storage**: All local data encrypted using Fernet encryption
- 🖼️ **Image Support**: Send images with your queries using OpenAI Vision format
- 📬 **Private Mode**: Toggle DM responses for privacy
- 💬 **DM Support**: Chat with the bot directly via Discord DMs
- 🧹 **Data Purging**: Users can delete their data anytime
- 🌊 **Streaming Responses**: Real-time response streaming with 2-second update intervals
- 🌐 **Bilingual Help**: Full Traditional Chinese (繁體中文) support
- 🔄 **Auto-Start**: Optional systemd service for automatic bot start on server reboot

## Installation

### Option 1: Automated Deployment (Recommended)

Run the deployment script on a fresh Ubuntu server:

```bash
cd ~/Poehub
./deploy_poe_bot.sh
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
pip install Red-DiscordBot openai cryptography
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
[p]addpath /home/ubuntu/red-cogs
```
*Note: Relative paths like ~/red-cogs are not supported*

2. **Load the PoeHub cog**:
```
[p]load poehub
```

3. **Set your Poe API key** (bot owner only):
```
[p]poeapikey <your_poe_api_key>
```

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

#### Toggle Private Mode
```
[p]privatemode
```
When enabled, responses will be sent to your DMs even when asking in a server channel.

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

#### Delete Conversation
```
[p]deleteconv conv_1734851234
```
Permanently delete a conversation.

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

Get your Poe API key from: https://poe.com/api_key

The bot uses the OpenAI-compatible endpoint at `https://api.poe.com/v1`

## Security

- **Encryption**: All local data is encrypted using `cryptography.fernet`
- **API Key Protection**: The bot automatically deletes messages containing API keys
- **User Privacy**: Users control their data and can purge it anytime
- **Private Mode**: Option to receive responses via DM for enhanced privacy

## File Structure

```
Poehub/
├── poehub.py               # Main cog logic
├── api_client.py           # API interaction layer
├── conversation_manager.py # State and history management
├── encryption.py           # Encryption helper class
├── __init__.py             # Package initialization
├── info.json               # Cog metadata
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
screen -dmS poebot bash -c "source ~/.redenv/bin/activate && redbot PoeBot"
screen -r poebot  # To attach to the session
```

### As a Systemd Service

1. Copy the service file:
```bash
sudo cp ~/poebot.service /etc/systemd/system/
```

2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable poebot.service
sudo systemctl start poebot.service
```

3. Check status:
```bash
sudo systemctl status poebot.service
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

