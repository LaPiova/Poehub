# 🚀 PoeHub - START HERE

Welcome to **PoeHub**, a complete Red-DiscordBot Cog for integrating Poe AI into Discord!

## 📦 What You've Got

This project includes everything you need to run an AI-powered Discord bot:

```
✅ Core Bot Code (Python)
✅ Security & Encryption Layer
✅ Automated Deployment Scripts
✅ Comprehensive Documentation
✅ Installation Verification Tools
```

## ⚡ Quick Start (5 Minutes)

### Step 1: Deploy the Bot
```bash
cd ~/Poehub
./deploy_poe_bot.sh
```
*This installs everything automatically*

**Note:** Red-DiscordBot requires Python 3.8-3.11 (NOT 3.12+). If you encounter installation errors, run:
```bash
./fix_python_version.sh
```

### Step 2: Start the Bot

**Interactive mode** (see logs in real-time):
```bash
~/Poehub/start_bot.sh
```

**Background mode** (recommended for production):
```bash
~/Poehub/start_bot_screen.sh
```

To view logs later: `screen -r poebot`  
To detach: Press `Ctrl+A` then `D`

### Step 3: Copy Cog Files to Red-DiscordBot
```bash
~/Poehub/sync_to_red.sh
```

### Step 4: Configure in Discord
```
!addpath /home/ubuntu/red-cogs
!load poehub
!poeapikey YOUR_POE_API_KEY
```
*Note: Use absolute path (not ~/). Get your API key from https://poe.com/api_key*

### Step 4: Start Using!
```
[p]ask Hello, how are you?
```

**That's it! You're ready to go! 🎉**

---

## 📚 Documentation Guide

We've created comprehensive documentation for every need:

### 🎯 For Getting Started
- **[QUICKSTART.md](QUICKSTART.md)** - Fast setup guide (Read this first!)
- **[INSTALLATION_CHECKLIST.md](INSTALLATION_CHECKLIST.md)** - Verify your setup

### 📖 For Learning More
- **[README.md](README.md)** - Complete documentation with all features
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Technical architecture & design

### 🔄 For Updates & Changes
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and updates

---

## 🎮 What Can This Bot Do?

### 🤖 Dynamic Multi-Model AI
The bot **automatically fetches** the latest models from Poe's API:
- **Claude Models** (3.5-Sonnet, Opus, Haiku, etc.)
- **GPT Models** (GPT-4o, GPT-4-Turbo, etc.)
- **Gemini Models** (Gemini-Pro, Gemini-1.5-Pro)
- **Llama, Mistral, and more!**
- **New models added automatically** - no updates needed!

### 🖼️ Image Analysis
Send images with your questions:
```
[p]ask What's in this image? (+ attach image)
```

### 🔒 Privacy Features
- **Private Mode**: Get responses via DM
- **Data Purging**: Delete your data anytime
- **Encryption**: All data encrypted locally

### 💬 Natural Conversations
- Chat in Discord channels
- Direct message the bot
- Real-time streaming responses

---

## 📁 Project Structure

```
Poehub/
│
├── 🎯 Core Files (The Bot Itself)
│   ├── poehub.py              # Main bot logic
│   ├── api_client.py          # API interaction layer
│   ├── conversation_manager.py # State management layer
│   ├── encryption.py          # Security layer
│   ├── __init__.py            # Package setup
│   └── info.json              # Bot metadata
│
├── ⚙️ Configuration
│   ├── requirements.txt       # Python packages needed
│   └── .env.example           # Environment variable template
│
├── 🚀 Deployment Tools
│   ├── deploy_poe_bot.sh     # One-click deployment (run this first!)
│   ├── start_bot.sh          # Start bot interactively
│   └── verify_installation.py # Check if everything works
│
└── 📚 Documentation (You are here!)
    ├── 00-START_HERE.md      # This file
    ├── QUICKSTART.md         # Fast setup
    ├── README.md             # Full documentation
    ├── INSTALLATION_CHECKLIST.md  # Setup verification
    ├── PROJECT_SUMMARY.md    # Technical details
    └── CHANGELOG.md          # Version history
```

---

## 🛠️ Common Tasks

### Check if Bot is Running
```bash
screen -ls
# OR
ps aux | grep redbot
```

### Stop the Bot
```bash
screen -r poebot
# Then press Ctrl+C
```

### Restart the Bot
```bash
~/start_bot_screen.sh
```

### Update the Cog
```bash
cd ~/Poehub
# If using git: git pull
cp poehub.py encryption.py __init__.py info.json ~/red-cogs/poehub/
# Then in Discord:
[p]reload poehub
```

### View Bot Logs
```bash
screen -r poebot
# View logs, then Ctrl+A, D to detach
```

---

## 🎨 Feature Highlights

### 1️⃣ Easy Model Switching
```
[p]setmodel GPT-4o
[p]ask Explain quantum computing
```

### 2️⃣ Image Understanding
```
[p]ask Describe this image
(Attach an image to your message)
```

### 3️⃣ Private Conversations
```
[p]privatemode
[p]ask My secret question
(Response sent to your DMs!)
```

### 4️⃣ Direct Messaging
Just DM the bot directly - no command needed!

### 5️⃣ See All Available Models (Live from Poe API)
```
[p]listmodels
```

Search for specific models:
```
[p]searchmodels claude
```

---

## 🔐 Security Features

- ✅ **Fernet Encryption** - All user data encrypted
- ✅ **API Key Protection** - Bot deletes API key messages
- ✅ **User Privacy** - Private mode for DM responses
- ✅ **Data Control** - Users can purge their data anytime
- ✅ **Isolated Storage** - Each user's data kept separate

---

## 📊 Stats

```
Total Lines of Code:    ~1,800 lines
Core Python Files:      5 files (poehub.py, api_client.py, conversation_manager.py, encryption.py, __init__.py)
Deployment Scripts:     3 scripts
Documentation Files:    6 comprehensive guides
Supported AI Models:    50+ models
Time to Deploy:         ~5 minutes
```

---

## 🆘 Need Help?

### Quick Troubleshooting

**Bot won't start?**
```bash
source ~/.redenv/bin/activate
python3 verify_installation.py
```

**Cog won't load?**
```
[p]addpath ~/red-cogs
[p]load poehub
```

**API not working?**
1. Check your API key at https://poe.com/api_key
2. Set it again: `[p]poeapikey YOUR_KEY`
3. Reload: `[p]reload poehub`

### Documentation to Check

- **Setup issues?** → Read [INSTALLATION_CHECKLIST.md](INSTALLATION_CHECKLIST.md)
- **Command help?** → Read [README.md](README.md)
- **Quick tips?** → Read [QUICKSTART.md](QUICKSTART.md)
- **Technical info?** → Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

---

## 🎓 Learning Path

### Beginner
1. Read this file (00-START_HERE.md) ← You are here!
2. Read [QUICKSTART.md](QUICKSTART.md)
3. Run `./deploy_poe_bot.sh`
4. Start using basic commands

### Intermediate
1. Read [README.md](README.md) for all features
2. Try different models with `[p]setmodel`
3. Use image analysis
4. Enable private mode

### Advanced
1. Read [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) for architecture
2. Set up systemd service for production
3. Customize the code if needed
4. Monitor with logs and analytics

---

## 🌟 Best Practices

### For Users
- Start with Claude-3.5-Sonnet (default)
- Try different models for different tasks
- Use private mode for sensitive queries
- Attach images for visual analysis
- Check `[p]listmodels` to see what's available

### For Bot Owners
- Keep API key secure
- Monitor usage and costs
- Run bot in screen or systemd for stability
- Regular backups of bot data
- Update dependencies periodically

### For Developers
- Check logs regularly: `screen -r poebot`
- Use verification script: `verify_installation.py`
- Follow the code in `poehub.py` to understand flow
- Encryption logic in `encryption.py`

---

## 🎯 Next Steps

After reading this, you should:

1. ✅ Run the deployment script
2. ✅ Start the bot
3. ✅ Configure in Discord
4. ✅ Try a few commands
5. ✅ Read QUICKSTART.md for more details

---

## 🚀 Ready to Begin?

### Your 3-Step Checklist:

1. **Deploy**: Run `./deploy_poe_bot.sh`
2. **Start**: Run `~/start_bot.sh`
3. **Configure**: Use commands in Discord

### First Commands to Try:

```
[p]addpath ~/red-cogs
[p]load poehub
[p]poeapikey YOUR_KEY
[p]listmodels
[p]ask Hello! Can you introduce yourself?
```

---

## 💬 Example Conversation

```
You: [p]ask What is the capital of France?

Bot: 🤔 Thinking...
     The capital of France is Paris. It's the largest city
     in France and has been the country's capital since...

You: [p]setmodel GPT-4o

Bot: ✅ Your model has been set to: GPT-4o

You: [p]ask Tell me a joke

Bot: 🤔 Thinking...
     Why don't scientists trust atoms?
     Because they make up everything! 😄
```

---

## 🎉 You're All Set!

Everything you need is here. Just follow the steps and you'll have a powerful AI Discord bot running in minutes!

**Happy chatting! 🤖💬**

---

### Quick Links Summary

- 🚀 [QUICKSTART.md](QUICKSTART.md) - Get started fast
- 📖 [README.md](README.md) - Full documentation
- ✅ [INSTALLATION_CHECKLIST.md](INSTALLATION_CHECKLIST.md) - Verify setup
- 🏗️ [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Architecture
- 📝 [CHANGELOG.md](CHANGELOG.md) - Version history

---

**Version**: 1.0.0  
**Last Updated**: December 21, 2025  
**Status**: ✅ Ready for Production

**Get your API key**: https://poe.com/api_key  
**Discord Developer Portal**: https://discord.com/developers/applications

