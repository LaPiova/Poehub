# PoeHub Installation Checklist

Use this checklist to ensure PoeHub is properly installed and configured.

## ✅ Pre-Installation

- [ ] Ubuntu server (20.04+ recommended)
- [ ] Python 3.8-3.11 installed (NOT 3.12+) - check with `python3 --version`
  - If you have Python 3.12, the script will install Python 3.11 automatically
- [ ] Git installed (optional, for updates)
- [ ] Discord bot created at https://discord.com/developers/applications
- [ ] Poe account with API access
- [ ] Poe API key obtained from https://poe.com/api_key

### Python Version Fix (if needed)

If you encounter errors about "No matching distribution found for Red-DiscordBot":

```bash
cd ~/Poehub
./fix_python_version.sh
```

This will install Python 3.11 and recreate the virtual environment.

## ✅ File Verification

Run from the project directory:

```bash
cd ~/Poehub
ls -la
```

You should see these files:
- [ ] `poehub.py` (Main cog)
- [ ] `api_client.py` (API interaction layer)
- [ ] `conversation_manager.py` (State management layer)
- [ ] `encryption.py` (Encryption helper)
- [ ] `__init__.py` (Package init)
- [ ] `info.json` (Cog metadata)
- [ ] `requirements.txt` (Dependencies)
- [ ] `deploy_poe_bot.sh` (Deployment script, executable)
- [ ] `start_bot.sh` (Startup script, executable)
- [ ] `verify_installation.py` (Verification script, executable)
- [ ] `README.md` (Full documentation)
- [ ] `QUICKSTART.md` (Quick start guide)

## ✅ Deployment

Run the automated deployment:

```bash
cd ~/Poehub
./deploy_poe_bot.sh
```

Check for:
- [ ] System packages installed (python3-venv, git, screen)
- [ ] Virtual environment created at `~/.redenv`
- [ ] Red-DiscordBot installed
- [ ] Dependencies installed (openai, cryptography)
- [ ] Red-DiscordBot setup completed (you'll be prompted)
- [ ] Cog files copied to `~/red-cogs/poehub/`
- [ ] Startup scripts created (`~/start_bot.sh`, `~/start_bot_screen.sh`)

## ✅ Dependency Verification

Run the verification script:

```bash
source ~/.redenv/bin/activate
python3 ~/Poehub/verify_installation.py
```

All checks should pass:
- [ ] discord.py is installed
- [ ] Red-DiscordBot is installed
- [ ] openai is installed
- [ ] cryptography is installed
- [ ] Python version is 3.8+

## ✅ Bot Startup

### Option 1: Interactive Mode
```bash
~/start_bot.sh
```

- [ ] Virtual environment activated
- [ ] Bot starts without errors
- [ ] Bot connects to Discord
- [ ] No error messages in console

### Option 2: Screen Session
```bash
~/start_bot_screen.sh
screen -r poebot
```

- [ ] Screen session created
- [ ] Bot running in background
- [ ] Can detach with `Ctrl+A` then `D`

## ✅ Discord Configuration

### 1. Sync Cog Files (Terminal)
```bash
~/Poehub/sync_to_red.sh
```
- [ ] Files copied successfully
- [ ] All 4 files present in ~/red-cogs/poehub/

### 2. In Discord, Add Cog Path
```
!addpath /home/ubuntu/red-cogs
```
*Important: Use absolute path, not ~/red-cogs (relative paths not supported)*

- [ ] Command executed successfully
- [ ] Path added confirmation received

### 3. Load PoeHub
```
!load poehub
```
- [ ] Cog loads without errors
- [ ] No import errors
- [ ] Confirmation message received

### 3. Set API Key (Owner Only)
```
[p]poeapikey YOUR_POE_API_KEY
```
- [ ] Command executed successfully
- [ ] Original message deleted (security feature)
- [ ] Confirmation message received

## ✅ Functionality Tests

### Basic Query Test
```
[p]ask What is 2+2?
```
- [ ] Bot responds with "Thinking..."
- [ ] Response streams in real-time
- [ ] Final answer appears
- [ ] No error messages

### Model Check
```
[p]mymodel
```
- [ ] Shows current model (default: Claude-3.5-Sonnet)

### Model List
```
[p]listmodels
```
- [ ] Displays embed with model categories
- [ ] Shows Claude, GPT, and other models

### Model Switch
```
[p]setmodel GPT-4o
```
- [ ] Confirmation message received
- [ ] `[p]mymodel` shows new model

### Private Mode Toggle
```
[p]privatemode
```
- [ ] Mode enabled/disabled confirmation
- [ ] Icon shows lock status

### Image Support Test
Upload an image with command:
```
[p]ask What's in this image?
```
- [ ] Bot processes image
- [ ] Response describes image content

### DM Test
Send a DM to the bot (no command prefix):
```
Hello, bot!
```
- [ ] Bot responds automatically
- [ ] Uses your preferred model
- [ ] Streaming works in DM

## ✅ Privacy & Security

### Data Purge Test
```
[p]purge_my_data
```
- [ ] Confirmation prompt appears
- [ ] React with ✅ to confirm
- [ ] Data purge confirmation received
- [ ] Settings reset to defaults

### Encryption Verification
Check config directory:
```bash
ls -la ~/.local/share/Red-DiscordBot/data/PoeBot/
```
- [ ] Config files exist
- [ ] Encryption key stored in global config
- [ ] User data encrypted (not human-readable)

## ✅ Production Readiness

### Systemd Service (Optional)
```bash
sudo cp ~/poebot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable poebot.service
sudo systemctl start poebot.service
sudo systemctl status poebot.service
```
- [ ] Service file installed
- [ ] Service enabled
- [ ] Service running
- [ ] Status shows "active (running)"

### Auto-Restart on Reboot
```bash
sudo systemctl is-enabled poebot.service
```
- [ ] Returns "enabled"
- [ ] Bot will auto-start on server reboot

### Log Monitoring
```bash
sudo journalctl -u poebot.service -f
```
- [ ] Logs display correctly
- [ ] No critical errors
- [ ] Bot activity visible

## ✅ Troubleshooting

If any checks fail:

### Bot won't load cog
```bash
# Check cog files
ls -la ~/red-cogs/poehub/

# Verify path
[p]paths

# Reload cog
[p]reload poehub
```

### "API client not initialized" error
```bash
# In Discord (owner only)
[p]poeapikey YOUR_KEY

# Reload cog
[p]reload poehub
```

### Dependencies missing
```bash
source ~/.redenv/bin/activate
pip install --upgrade Red-DiscordBot openai cryptography
```

### Bot offline
```bash
# Check if running
screen -ls

# Or check systemd
sudo systemctl status poebot.service

# Restart
~/start_bot_screen.sh
# OR
sudo systemctl restart poebot.service
```

## ✅ Performance Verification

### Response Time
- [ ] Streaming starts within 2-3 seconds
- [ ] Updates appear every ~2 seconds
- [ ] No significant delays

### Error Handling
Test with invalid model:
```
[p]setmodel InvalidModel123
[p]ask Test question
```
- [ ] Error message is clear
- [ ] Bot doesn't crash
- [ ] Can recover with valid model

### Concurrent Requests
Multiple users ask questions simultaneously:
- [ ] All receive responses
- [ ] No crashes or hangs
- [ ] Responses don't mix between users

## ✅ Final Verification

Run this command to see all configurations:
```
[p]help PoeHub
```

Expected output:
- [ ] Lists all PoeHub commands
- [ ] Shows command descriptions
- [ ] No errors or missing info

## 🎉 Installation Complete!

If all items are checked, your PoeHub installation is complete and fully functional!

### Quick Reference

**Start Bot**:
```bash
~/start_bot.sh  # Interactive
~/start_bot_screen.sh  # Background
```

**Attach to Screen**:
```bash
screen -r poebot
```

**Basic Commands**:
- `[p]ask <question>` - Ask AI
- `[p]setmodel <name>` - Change model
- `[p]listmodels` - See available models
- `[p]privatemode` - Toggle DM responses

### Support

- Documentation: `~/Poehub/README.md`
- Quick Start: `~/Poehub/QUICKSTART.md`
- Project Summary: `~/Poehub/PROJECT_SUMMARY.md`

---

**Checklist Version**: 1.0  
**Last Updated**: December 21, 2025

