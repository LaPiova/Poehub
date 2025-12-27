#!/bin/bash

###############################################################################
# Start PoeBot in a Screen Session
# This allows the bot to run in the background
###############################################################################

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}  Starting PoeBot in Screen Session${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

INSTANCE_NAME="${POEHUB_REDBOT_INSTANCE:-PoeBot}"
SCREEN_NAME="${POEHUB_SCREEN_NAME:-poebot}"

# Check if screen session already exists
if screen -list | grep -q "$SCREEN_NAME"; then
    echo -e "${YELLOW}⚠${NC}  Screen session '${SCREEN_NAME}' already exists!"
    echo ""
    echo "Options:"
    echo "  1. Attach to existing session: screen -r ${SCREEN_NAME}"
    echo "  2. Kill and restart: screen -X -S ${SCREEN_NAME} quit && $0"
    echo ""
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$HOME/.redenv" ]; then
    echo -e "${RED}✗${NC} Virtual environment not found at ~/.redenv"
    echo "Please run: ./fix_python_version.sh"
    exit 1
fi

# Start bot in detached screen session
echo -e "${BLUE}Starting bot in screen session 'poebot'...${NC}"
echo -e "${BLUE}Starting bot in screen session '${SCREEN_NAME}'...${NC}"
screen -dmS "$SCREEN_NAME" bash -c "source $HOME/.redenv/bin/activate && redbot ${INSTANCE_NAME}"

# Give it a moment to start
sleep 2

# Check if session is running
if screen -list | grep -q "$SCREEN_NAME"; then
    echo ""
    echo -e "${GREEN}✓${NC} Bot started successfully in screen session!"
    echo ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo "  • Attach to session:  ${GREEN}screen -r ${SCREEN_NAME}${NC}"
    echo "  • Detach from session: Press ${GREEN}Ctrl+A${NC} then ${GREEN}D${NC}"
    echo "  • Stop the bot:       ${GREEN}screen -X -S ${SCREEN_NAME} quit${NC}"
    echo "  • View all sessions:  ${GREEN}screen -ls${NC}"
    echo ""
    echo -e "${BLUE}Bot Status:${NC}"
    screen -ls | grep "$SCREEN_NAME"
else
    echo ""
    echo -e "${RED}✗${NC} Failed to start bot in screen session"
    echo "Try running interactively to see errors: ./start_bot.sh"
fi

