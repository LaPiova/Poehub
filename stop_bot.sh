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

# Check for screen session
if screen -list | grep -q "poebot"; then
    echo "Found screen session 'poebot'"
    screen -X -S poebot quit
    sleep 1
    
    if screen -list | grep -q "poebot"; then
        echo -e "${RED}✗${NC} Failed to stop screen session"
        exit 1
    else
        echo -e "${GREEN}✓${NC} Screen session stopped"
    fi
else
    echo -e "${YELLOW}⚠${NC}  No screen session named 'poebot' found"
fi

# Check for running redbot processes
if pgrep -f "redbot PoeBot" > /dev/null; then
    echo "Found running redbot process"
    pkill -f "redbot PoeBot"
    sleep 1
    
    if pgrep -f "redbot PoeBot" > /dev/null; then
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

