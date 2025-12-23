# PoeHub Scripts Reference

Quick guide to all available helper scripts.

## 🚀 Bot Control Scripts

### Start Bot (Interactive)
```bash
~/Poehub/start_bot.sh
```
**Use when:** You want to see logs in real-time, debugging, first-time setup

**Pros:** 
- See all output immediately
- Easy to debug
- Can stop with Ctrl+C

**Cons:**
- Terminal must stay open
- Bot stops when you close terminal

---

### Start Bot (Background - Screen)
```bash
~/Poehub/start_bot_screen.sh
```
**Use when:** Running in production, want bot to persist after logout

**Features:**
- Runs in detached screen session
- Survives terminal close
- Can reconnect anytime

**Management:**
```bash
screen -r poebot        # Attach to view logs
# Press Ctrl+A then D   # Detach (keeps running)
screen -ls              # List all sessions
```

---

### Stop Bot
```bash
~/Poehub/stop_bot.sh
```
**What it does:**
- Stops screen session if running
- Kills redbot process if found
- Clean shutdown

---

### Check Bot Status
```bash
~/Poehub/bot_status.sh
```
**Shows:**
- Screen session status
- Process status
- Virtual environment info
- Cog files status
- Quick action commands

---

## 🔧 Setup & Maintenance Scripts

### Sync Cog Files
```bash
~/Poehub/sync_to_red.sh
```
**Use when:** 
- After editing cog files
- Installing updates
- First time setup

**What it does:**
- Copies files from ~/Poehub to ~/red-cogs/poehub
- Shows file list
- Displays next steps

---

### Get Absolute Path
```bash
~/Poehub/GET_PATH.sh
```
**Use when:** 
- Need the exact path for !addpath command
- Unsure of absolute path

**Output:**
```
!addpath /home/ubuntu/red-cogs
```

---

### Fix Python Version
```bash
~/Poehub/fix_python_version.sh
```
**Use when:**
- Installation errors about Python version
- Red-DiscordBot won't install
- Need to switch to Python 3.11

**What it does:**
- Installs Python 3.11 if needed
- Recreates virtual environment
- Installs all dependencies

---

### Verify Installation
```bash
source ~/.redenv/bin/activate
python ~/Poehub/verify_installation.py
```
**Use when:**
- Troubleshooting dependency issues
- Verifying setup is correct
- After fresh install

---

### Full Deployment
```bash
~/Poehub/deploy_poe_bot.sh
```
**Use when:**
- Fresh server setup
- First time installation
- Complete reinstall needed

**What it does:**
- Installs system packages
- Creates virtual environment
- Installs Red-DiscordBot
- Sets up directories
- Creates all helper scripts

---

## 📊 Common Workflows

### First Time Setup
```bash
# 1. Deploy everything
~/Poehub/deploy_poe_bot.sh

# 2. Start bot (interactive to see if it works)
~/Poehub/start_bot.sh
# Follow prompts for Discord token and prefix

# 3. In Discord:
!addpath /home/ubuntu/red-cogs
!load poehub
!poeapikey YOUR_KEY

# 4. Stop and restart in background
Ctrl+C
~/Poehub/start_bot_screen.sh
```

---

### Updating PoeHub Code
```bash
# 1. Edit files in ~/Poehub/
vim ~/Poehub/poehub.py

# 2. Sync to red-cogs
~/Poehub/sync_to_red.sh

# 3. Reload in Discord
!reload poehub
```

---

### Troubleshooting
```bash
# Check status
~/Poehub/bot_status.sh

# View logs
screen -r poebot

# Stop and restart
~/Poehub/stop_bot.sh
~/Poehub/start_bot.sh  # Interactive to see errors

# Verify dependencies
source ~/.redenv/bin/activate
python ~/Poehub/verify_installation.py
```

---

### Production Restart
```bash
# Stop current instance
~/Poehub/stop_bot.sh

# Start in background
~/Poehub/start_bot_screen.sh

# Check it's running
~/Poehub/bot_status.sh

# View logs
screen -r poebot
```

---

## 🎯 Quick Command Reference

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `start_bot.sh` | Start interactively | Debugging, first setup |
| `start_bot_screen.sh` | Start in background | Production use |
| `stop_bot.sh` | Stop the bot | Shutdown, restart |
| `bot_status.sh` | Check status | Verify bot is running |
| `sync_to_red.sh` | Copy cog files | After code changes |
| `GET_PATH.sh` | Show path command | Need absolute path |
| `fix_python_version.sh` | Fix Python issues | Installation errors |
| `verify_installation.py` | Check dependencies | Troubleshooting |
| `deploy_poe_bot.sh` | Full deployment | Fresh install |

---

## 💡 Tips

### Screen Session Commands
```bash
screen -r poebot          # Attach to session
Ctrl+A, then D            # Detach (keeps running)
screen -ls                # List all sessions
screen -X -S poebot quit  # Kill session
```

### Make Scripts Executable (if needed)
```bash
chmod +x ~/Poehub/*.sh
```

### View Logs Without Screen
```bash
# If bot is running
ps aux | grep redbot

# Check system logs (if using systemd)
sudo journalctl -u poebot -f
```

---

## 🔒 Security Note

- Keep your Poe API key secure
- Don't commit it to git
- Set via Discord: `!poeapikey <key>`
- Bot automatically deletes the message

---

**Last Updated:** December 23, 2025  
**Version:** 1.3.0

