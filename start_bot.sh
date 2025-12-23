#!/bin/bash

###############################################################################
# PoeBot Startup Script
# This script activates the virtual environment and starts the bot
###############################################################################

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}  Starting PoeBot...${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Activate virtual environment
if [ -d "$HOME/.redenv" ]; then
    source "$HOME/.redenv/bin/activate"
    echo -e "${GREEN}✓${NC} Virtual environment activated"
else
    echo -e "${RED}✗${NC} Virtual environment not found at ~/.redenv"
    echo "Please run deploy_poe_bot.sh first"
    exit 1
fi

# Start the bot
echo -e "${BLUE}Starting Red-DiscordBot instance 'PoeBot'...${NC}"
echo ""
redbot PoeBot

# Deactivate venv on exit
deactivate

