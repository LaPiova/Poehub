# PoeHub Troubleshooting Guide

Common issues and their solutions.

## 🔧 Installation Issues

### Python Version Error

**Error:**
```
ERROR: Could not find a version that satisfies the requirement Red-DiscordBot
ERROR: No matching distribution found for Red-DiscordBot
```

**Cause:** Red-DiscordBot requires Python 3.8.1 to 3.11.x and does NOT support Python 3.12+.

**Solution:**
```bash
cd ~/Poehub
./fix_python_version.sh
```

This will:
1. Install Python 3.11 (if not present)
2. Remove the old virtual environment
3. Create a new venv with Python 3.11
4. Install all dependencies correctly

---

### Virtual Environment Already Exists

**Error:**
```
[WARNING] Virtual environment already exists at ~/.redenv
```

**Solution:**

If the virtual environment was created with the wrong Python version:
```bash
rm -rf ~/.redenv
./fix_python_version.sh
```

Or run the updated deployment script:
```bash
./deploy_poe_bot.sh
```

---

### Permission Denied

**Error:**
```
bash: ./deploy_poe_bot.sh: Permission denied
```

**Solution:**
```bash
chmod +x ~/Poehub/*.sh
./deploy_poe_bot.sh
```

---

## 🤖 Bot Issues

### Cog Won't Load

**Error in Discord:**
```
[p]load poehub
Error: No module named 'poehub'
```

**Solutions:**

1. **Check if path is added:**
```
[p]paths
```

If your `red-cogs` path is not listed (use absolute path):
```
[p]addpath /home/<your-user>/red-cogs
```
*Note: Relative paths like ~/red-cogs don't work*

2. **Verify files exist:**
```bash
ls -la /home/<your-user>/red-cogs/poehub/
```

Should see: `poehub.py`, `api_client.py`, `conversation_manager.py`, `encryption.py`, `__init__.py`, `info.json`, and a `ui/` folder

3. **Sync files again:**
```bash
~/Poehub/sync_to_red.sh
```

4. **Reload the cog:**
```
[p]reload poehub
```

---

### API Client Not Initialized

**Error:**
```
❌ API client not initialized. Please set your API key first.
```

**Solution:**

Bot owner must set the API key:
```
[p]poeapikey YOUR_POE_API_KEY
```

Get your API key from: https://poe.com/api_key

Then reload the cog:
```
[p]reload poehub
```

---

### Bot Not Responding

**Checklist:**

1. **Is the bot online?**
```bash
screen -ls
# OR
ps aux | grep redbot
```

2. **Is the cog loaded?**
```
[p]cogs
```

Should show `poehub` in the list.

3. **Check bot permissions:**
- Read Messages
- Send Messages
- Embed Links
- Attach Files
- Read Message History

4. **Check command prefix:**
```
[p]prefix
```

Make sure you're using the correct prefix.

5. **Check logs:**
```bash
screen -r poebot
# View logs, then Ctrl+A, D to detach
```

---

### Can't Send DMs

**Error:**
```
❌ Unable to send DM. Please check your privacy settings.
```

**Causes:**
1. User has DMs disabled for server members
2. Bot doesn't share a server with the user
3. User has blocked the bot

**Solutions:**
1. Enable "Allow direct messages from server members" in Discord privacy settings
2. Make sure the bot is in at least one server you're in
3. Unblock the bot if blocked

---

## 📡 API Issues

### Invalid API Key

**Error:**
```
❌ Error communicating with Poe API: 401 Unauthorized
```

**Solution:**

1. Get a fresh API key from https://poe.com/api_key
2. Set it again:
```
[p]poeapikey NEW_API_KEY
```

---

### Model Not Available

**Error:**
```
❌ Error communicating with Poe API: 404 Not Found
```

**Cause:** Model name is incorrect or not available with your Poe subscription.

**Solutions:**

1. Check available models:
```
[p]listmodels
```

2. Use exact model name:
```
[p]setmodel Claude-3.5-Sonnet
```

3. Upgrade your Poe subscription if you want premium models.

---

### Rate Limit Exceeded

**Error:**
```
❌ Error: 429 Too Many Requests
```

**Solution:**

Wait a few minutes before making more requests. Poe has rate limits based on your subscription tier.

---

## 💾 Data Issues

### Can't Purge Data

**Error:**
```
Confirmation timeout. Data purge cancelled.
```

**Solution:**

React to the confirmation message within 30 seconds with ✅ or ❌.

---

### Encryption Errors

**Error:**
```
Error decrypting data
```

**Cause:** Encryption key was lost or corrupted.

**Solution:**

This will reset your encryption and user data:
```
[p]reload poehub
```

If that doesn't work, clear all config data (owner only):
```
[p]unload poehub
# Remove config directory
rm -rf ~/.local/share/Red-DiscordBot/data/${POEHUB_REDBOT_INSTANCE:-PoeBot}/cogs/PoeHub/
[p]load poehub
[p]poeapikey YOUR_KEY
```

**Warning:** This deletes all user data and preferences.

---

## 🖼️ Image Issues

### Images Not Processing

**Problem:** Bot doesn't respond to images or doesn't describe them.

**Solutions:**

1. **Check model supports vision:**
   
   Use a vision-capable model:
   ```
   [p]setmodel Claude-3.5-Sonnet
   [p]setmodel GPT-4o
   ```

2. **Check file format:**
   
   Supported: JPEG, PNG, GIF, WebP

3. **Check file size:**
   
   Discord limits: 8MB (free), 50MB (Nitro Classic), 100MB (Nitro)

---

## 🚀 Deployment Issues

### redbot-setup Errors

**Error during setup:**
```
error: redbot-setup: command not found
```

**Solution:**

Make sure you've activated the virtual environment:
```bash
source ~/.redenv/bin/activate
which redbot-setup
```

If still not found:
```bash
pip install --upgrade Red-DiscordBot
```

---

### Screen Session Not Found

**Error:**
```
There is no screen to be resumed matching "poebot".
```

**Solution:**

Start a new session:
```bash
~/start_bot_screen.sh
```

Or start interactively:
```bash
~/start_bot.sh
```

---

### Dependencies Not Installing

**Error:**
```
ERROR: Could not find a version that satisfies the requirement...
```

**Solutions:**

1. **Update pip:**
```bash
source ~/.redenv/bin/activate
pip install --upgrade pip setuptools wheel
```

2. **Install manually:**
```bash
pip install Red-DiscordBot openai cryptography
```

3. **Check Python version:**
```bash
python --version
```

Must be 3.8-3.11 (NOT 3.12+).

---

## 🔍 Debugging

### Enable Debug Logging

In Discord:
```
[p]set debuglogging true
```

### View Full Logs

```bash
screen -r poebot
# Scroll through logs
# Press Ctrl+A, D to detach
```

### Test Dependencies

```bash
cd ~/Poehub
source ~/.redenv/bin/activate
python verify_installation.py
```

### Check Config Files

```bash
ls -la ~/.local/share/Red-DiscordBot/data/${POEHUB_REDBOT_INSTANCE:-PoeBot}/cogs/PoeHub/
```

---

## 📞 Still Having Issues?

### Information to Gather

1. **Python version:**
```bash
python3 --version
source ~/.redenv/bin/activate && python --version
```

2. **Red-DiscordBot version:**
```bash
pip show Red-DiscordBot
```

3. **Error messages:**
   - Copy full error from Discord
   - Copy terminal output
   - Check bot logs in screen session

4. **System info:**
```bash
uname -a
cat /etc/os-release
```

### Quick Diagnostic

Run this to check everything:
```bash
cd ~/Poehub
source ~/.redenv/bin/activate
python verify_installation.py
```

---

## 🔄 Clean Reinstall

If all else fails, do a complete reinstall:

```bash
# 1. Stop the bot
screen -X -S poebot quit

# 2. Backup your API key (if you want to keep it)
# (Manual step - save your API key somewhere)

# 3. Remove virtual environment
rm -rf ~/.redenv

# 4. Remove bot data (OPTIONAL - loses all config)
# rm -rf ~/.local/share/Red-DiscordBot/data/${POEHUB_REDBOT_INSTANCE:-PoeBot}

# 5. Run fix script
cd ~/Poehub
./fix_python_version.sh

# 6. Setup bot again
redbot-setup

# 7. Start bot
~/start_bot.sh

# 8. In Discord:
[p]addpath /home/<your-user>/red-cogs
[p]load poehub
[p]poeapikey YOUR_KEY
```
*Note: `addpath` requires an absolute path (not `~/`). Use `~/Poehub/GET_PATH.sh` to print the correct command for your machine.*

---

## ✅ Verification Checklist

After fixing issues, verify everything works:

- [ ] Bot is online in Discord
- [ ] `[p]cogs` shows `poehub` loaded
- [ ] `[p]ask Hello` gets a response
- [ ] `[p]listmodels` shows available models
- [ ] `[p]setmodel GPT-4o` changes model successfully
- [ ] `[p]mymodel` shows correct model
- [ ] DM to bot gets automatic response
- [ ] Image attachment works with `[p]ask`

---

**Last Updated:** December 23, 2025  
**Version:** 1.3.0 (Modularized Architecture)
