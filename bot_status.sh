#!/bin/bash

###############################################################################
# Check PoeBot Status
# Shows if the bot is running and how
###############################################################################

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}  PoeBot Status${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check screen sessions
echo -e "${BLUE}Screen Sessions:${NC}"
if screen -list | grep -q "poebot"; then
    echo -e "${GREEN}✓${NC} Screen session 'poebot' is running"
    screen -list | grep poebot
else
    echo -e "${YELLOW}⚠${NC}  No screen session 'poebot' found"
fi
echo ""

# Check redbot processes
echo -e "${BLUE}Redbot Processes:${NC}"
if pgrep -f "redbot PoeBot" > /dev/null; then
    echo -e "${GREEN}✓${NC} Redbot process is running"
    ps aux | grep "redbot PoeBot" | grep -v grep
else
    echo -e "${YELLOW}⚠${NC}  No redbot process found"
fi
echo ""

# Check virtual environment
echo -e "${BLUE}Virtual Environment:${NC}"
if [ -d "$HOME/.redenv" ]; then
    echo -e "${GREEN}✓${NC} Virtual environment exists at ~/.redenv"
    source "$HOME/.redenv/bin/activate"
    echo "  Python: $(python --version)"
    echo "  Red-DiscordBot: $(pip show Red-DiscordBot 2>/dev/null | grep Version | cut -d' ' -f2)"
    deactivate
else
    echo -e "${RED}✗${NC} Virtual environment not found"
fi
echo ""

# Check cog files
echo -e "${BLUE}PoeHub Cog Files:${NC}"
if [ -d "/home/ubuntu/red-cogs/poehub" ]; then
    echo -e "${GREEN}✓${NC} Cog directory exists"
    ls -lh /home/ubuntu/red-cogs/poehub/*.py 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
else
    echo -e "${YELLOW}⚠${NC}  Cog directory not found at /home/ubuntu/red-cogs/poehub"
fi
echo ""

# Summary
echo -e "${BLUE}=========================================${NC}"
if screen -list | grep -q "poebot" || pgrep -f "redbot PoeBot" > /dev/null; then
    echo -e "${GREEN}Status: BOT IS RUNNING${NC}"
    echo ""
    echo "To view logs:    screen -r poebot"
    echo "To stop bot:     ./stop_bot.sh"
else
    echo -e "${YELLOW}Status: BOT IS NOT RUNNING${NC}"
    echo ""
    echo "To start bot:    ./start_bot_screen.sh"
fi
echo -e "${BLUE}=========================================${NC}"

