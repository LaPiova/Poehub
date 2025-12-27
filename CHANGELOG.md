# Changelog

## [Unreleased]

### Added
- Offline dummy mode with `[p]poedummymode` for testing PoeHub without a live Poe API key.
- Interactive `[p]poeconfig` menu for managing models, prompts, and dummy mode via Discord buttons.
- `POEHUB_ENABLE_DUMMY_MODE` environment flag (default OFF) to hide dummy-mode commands and UI in release builds.

## [1.3.0] - 2025-12-23

### Refactored
- **Codebase Modularization**: Split the monolithic `poehub.py` into specialized modules for better maintainability and extensibility.
  - `api_client.py`: Handles all interactions with Poe/OpenAI API (fetching models, streaming).
  - `conversation_manager.py`: Manages conversation state, message limits, and encryption logic.
  - `poehub.py`: Now focuses solely on Discord command handling and acts as a controller.

### Technical Improvements
- **Cleaner Architecture**: Separation of concerns allows for easier testing and feature additions.
- **Robust Imports**: Improved import handling to support both package and script execution.
- **Enhanced Type Hinting**: Added comprehensive type hints across new modules.

## [1.2.1] - 2025-12-22

### Improved
- **Smart Message Splitting**: Enhanced message splitting algorithm that respects natural boundaries
  - Splits at code blocks (```) when possible
  - Splits at paragraph boundaries (double newlines)
  - Splits at sentence endings or word boundaries
  - Adds continuation indicators `*(continued...)*` and `*(continued)*`
  - Prevents breaking code blocks or sentences mid-way

### Technical Details
- Added `_split_message()` helper method with intelligent splitting logic
- Maximum chunk size: 1950 characters (leaves 50 char buffer for Discord's 2000 limit)
- Improved user experience for long AI responses

## [1.2.0] - 2025-12-22

### Added
- **System Prompts**: Owner can set default system prompt for all users
- **Personal Prompts**: Each user can set their own custom system prompt
- **Prompt Commands**: `setdefaultprompt`, `cleardefaultprompt`, `setprompt`, `myprompt`, `clearprompt`
- **Per-User Isolation**: Personal prompts are completely isolated between users
- **Prompt Priority**: Personal prompts override default prompts
- **SYSTEM_PROMPTS_GUIDE.md**: Comprehensive bilingual guide for system prompts

### Changed
- System prompts now automatically applied to all API calls (`ask` command and DM responses)
- Updated bilingual help command to include prompt commands
- Enhanced security: All prompts stored encrypted per-user

### Technical Details
- Added `default_system_prompt` to global config
- Added `system_prompt` to per-user config
- Added `_get_system_prompt()` helper method
- System prompts prepended as `{"role": "system", "content": "..."}` before conversation history

All notable changes to the PoeHub project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-12-21

### Initial Release 🎉

#### Added - Core Features
- **Multi-Model AI Support**: Switch between Claude, GPT-4, Gemini, and other models
- **OpenAI-Compatible Integration**: Uses official OpenAI SDK with Poe API endpoint
- **Streaming Responses**: Real-time response streaming with 2-second update intervals
- **Image Support**: Send images with queries using OpenAI Vision format
- **DM Support**: Automatic responses to direct messages
- **Private Mode**: Toggle to receive responses via DM even in server channels

#### Added - Security & Privacy
- **Fernet Encryption**: All user data encrypted with AES-128
- **Automatic Key Generation**: Unique encryption keys per installation
- **API Key Protection**: Automatically deletes messages containing API keys
- **Data Purging**: Users can delete all their data with confirmation dialog
- **Isolated User Data**: Per-user configuration with no cross-contamination

#### Added - Commands
- `[p]ask <query>` - Ask questions to AI (supports image attachments)
- `[p]setmodel <name>` - Change preferred AI model
- `[p]mymodel` - Check current model setting
- `[p]listmodels` - Display all available models with categories
- `[p]privatemode` - Toggle private DM responses
- `[p]purge_my_data` - Delete all user data (with confirmation)
- `[p]poeapikey <key>` - Set Poe API key (owner only)

#### Added - Deployment & Operations
- **Automated Deployment Script**: `deploy_poe_bot.sh` for one-click setup
- **Virtual Environment Setup**: Automatic venv creation and activation
- **Startup Scripts**: Interactive and screen-based startup options
- **Systemd Service**: Production-ready service file included
- **Verification Script**: Dependency checker for troubleshooting

#### Added - Documentation
- **README.md**: Comprehensive documentation with examples
- **QUICKSTART.md**: Step-by-step quick start guide
- **PROJECT_SUMMARY.md**: Detailed project overview and architecture
- **INSTALLATION_CHECKLIST.md**: Complete installation verification checklist
- **CHANGELOG.md**: This file for tracking changes

#### Technical Specifications
- **Language**: Python 3.8+
- **Framework**: Red-DiscordBot 3.5.0+
- **API Client**: OpenAI SDK 1.0.0+
- **Encryption**: cryptography 41.0.0+
- **Discord Library**: discord.py 2.0.0+
- **API Endpoint**: https://api.poe.com/v1

#### File Structure
```
Poehub/
├── src/poehub/                     # Cog package source
│   ├── poehub.py                   # Main cog implementation
│   ├── api_client.py               # Poe/OpenAI client wrapper
│   ├── conversation_manager.py     # Conversation state + encryption
│   ├── encryption.py               # Encryption helper
│   ├── ui/                         # Discord UI views
│   ├── __init__.py                 # Package initialization
│   └── info.json                   # Cog metadata
├── requirements.txt                # Python dependencies
├── deploy_poe_bot.sh              # Deployment automation
├── start_bot.sh                   # Bot startup script
├── verify_installation.py         # Dependency verification
└── Documentation/
    ├── README.md                  # Main documentation
    ├── QUICKSTART.md             # Quick start guide
    ├── PROJECT_SUMMARY.md        # Project overview
    ├── INSTALLATION_CHECKLIST.md # Setup verification
    └── CHANGELOG.md              # This file
```

#### Supported Models (Initial Release)
##### Claude Models
- Claude-3.5-Sonnet (Default)
- Claude-3-Opus
- Claude-3-Sonnet
- Claude-3-Haiku

##### GPT Models
- GPT-4o
- GPT-4-Turbo
- GPT-4
- GPT-3.5-Turbo

##### Other Models
- Gemini-Pro
- Gemini-1.5-Pro
- Llama-3.1-405B

#### Known Limitations
- Discord 2000 character limit (handled via chunking)
- 2-second update interval to avoid Discord rate limits
- Model availability depends on Poe subscription level
- No conversation history persistence (can be added in future)

#### Requirements Met
- ✅ Phase 1: Blueprint - Complete project structure
- ✅ Phase 2: Implementation - Full cog functionality
- ✅ Phase 3: Encryption Layer - Fernet encryption integrated
- ✅ Phase 4: Deployment - One-click deployment script

## [Unreleased]

### Version 1.1.0 - Conversation Context & Auto-Start (December 22, 2025)

#### 🎯 Major Features Added

**Persistent Conversation Context**
- Multiple conversations per user (create, switch, manage)
- AI remembers context within each conversation (up to 50 messages)
- Per-user isolation - each Discord user has separate conversations
- Encrypted conversation storage
- Conversation management commands

**Auto-Start on Server Reboot**
- Systemd service integration
- Automatic bot start when server reboots
- Service installation and management scripts
- Production-ready deployment

#### Added Commands
- `!newconv [title]` - Create a new conversation
- `!switchconv <id>` - Switch to a different conversation
- `!listconv` - List all your conversations
- `!deleteconv <id>` - Delete a conversation
- `!currentconv` - Show active conversation details

#### Enhanced Commands
- `!ask` - Now automatically uses conversation context
  - AI remembers previous messages in active conversation
  - Messages saved and encrypted per user
  - Works in both channels and DMs

#### New Scripts
- `install_service.sh` - Install bot as systemd service
- `uninstall_service.sh` - Remove systemd service
- `bot_status.sh` - Check bot status (enhanced)
- `stop_bot.sh` - Stop bot cleanly
- `start_bot_screen.sh` - Start in background

#### New Documentation
- `CONVERSATION_GUIDE.md` - Complete conversation management guide
- `SCRIPTS_REFERENCE.md` - All scripts documentation (updated)

#### Technical Changes
- Added conversation storage to Config
- Implemented 6 conversation helper methods
- Modified `_stream_response` to save assistant messages
- Updated DM listener to use conversation context
- Conversation limit: 50 messages per conversation
- Automatic old message cleanup

---

## [Unreleased]

### Recent Updates (v1.0.1)

#### Added
- **Dynamic Model Fetching**: Bot now fetches available models directly from Poe API
- **Model Caching**: 1-hour cache to reduce API calls
- **New Command**: `[p]searchmodels <query>` to search for specific models
- **Enhanced listmodels**: Now shows live data from Poe with model counts
- **Force Refresh**: Use `[p]listmodels refresh` to update the model list
- **Automatic Grouping**: Models automatically grouped by provider (Claude, GPT, Gemini, etc.)
- **Python 3.11 Support**: Fixed compatibility issues with Python 3.12
- **Fix Script**: Added `fix_python_version.sh` for easy Python version management

#### Changed
- `[p]listmodels` now fetches live data instead of using hardcoded list
- Model list updates automatically - no code changes needed for new models
- Improved error handling for model fetching
- Better documentation with Python version requirements

#### Fixed
- Python 3.12 compatibility issue (Red-DiscordBot requires 3.8-3.11)
- Virtual environment creation with correct Python version
- Model availability now reflects actual Poe API state

### Planned Features
- Conversation history with context window
- Multi-turn conversations with memory
- System prompt customization
- Temperature and top_p parameter controls
- Token usage tracking and cost estimation
- Conversation export to various formats
- Voice message transcription support
- File attachment support (PDF, documents)
- Multiple language support for UI
- Redis caching for faster responses

### Planned Improvements
- Docker containerization for easier deployment
- Kubernetes deployment manifests
- Load balancing support for high-traffic bots
- Enhanced analytics and usage statistics
- Automated backup system
- Health check endpoint
- Rate limiting per user/server
- Admin dashboard for monitoring

### Planned Security Enhancements
- End-to-end encryption for conversations
- Audit logging for compliance
- Role-based access control
- API key rotation support
- Encrypted backup system

## Version History

### [1.0.0] - 2025-12-21
- Initial public release
- Complete implementation of all Phase 1-4 requirements
- Full documentation suite
- Production-ready deployment automation

---

## Upgrade Instructions

### From Source
```bash
cd ~/Poehub
git pull  # If using git
./sync_to_red.sh
```

### In Discord
```
[p]reload poehub
```

## Breaking Changes

None (initial release)

## Deprecation Notices

None (initial release)

## Security Updates

Always use the latest version to ensure you have the most recent security patches.

Current version: **1.0.0**

## Contributors

- PoeHub Team - Initial development

## License

Custom Red-DiscordBot Cog - Use at your own discretion

## Links

- **Poe API Documentation**: https://developer.poe.com/
- **Red-DiscordBot**: https://docs.discord.red/
- **OpenAI Python SDK**: https://github.com/openai/openai-python
- **Cryptography Library**: https://cryptography.io/

---

**Note**: This changelog follows semantic versioning. Version numbers follow the format MAJOR.MINOR.PATCH where:
- MAJOR: Incompatible API changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes, backward compatible

