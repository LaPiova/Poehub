#!/bin/bash

###############################################################################
# Stop PoeBot
# Works for both screen sessions and interactive instances
###############################################################################

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${YELLOW}  Stopping PoeBot${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

INSTANCE_NAME="${POEHUB_REDBOT_INSTANCE:-PoeBot}"
SCREEN_NAME="${POEHUB_SCREEN_NAME:-poebot}"

# Check for screen session
if screen -list | grep -q "$SCREEN_NAME"; then
    echo "Found screen session '$SCREEN_NAME'"
    screen -X -S "$SCREEN_NAME" quit
    sleep 1
    
    if screen -list | grep -q "$SCREEN_NAME"; then
        echo -e "${RED}✗${NC} Failed to stop screen session"
        exit 1
    else
        echo -e "${GREEN}✓${NC} Screen session stopped"
    fi
else
    echo -e "${YELLOW}⚠${NC}  No screen session named '$SCREEN_NAME' found"
fi

# Check for running redbot processes
if pgrep -f "redbot ${INSTANCE_NAME}" > /dev/null; then
    echo "Found running redbot process"
    pkill -f "redbot ${INSTANCE_NAME}"
    sleep 1
    
    if pgrep -f "redbot ${INSTANCE_NAME}" > /dev/null; then
        echo -e "${RED}✗${NC} Failed to stop redbot process"
        exit 1
    else
        echo -e "${GREEN}✓${NC} Redbot process stopped"
    fi
else
    echo -e "${YELLOW}⚠${NC}  No redbot process found"
fi

echo ""
echo -e "${GREEN}✓${NC} PoeBot stopped"

