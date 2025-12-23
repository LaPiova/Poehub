#!/bin/bash

###############################################################################
# Uninstall PoeBot System Service
# Removes auto-start on server boot
###############################################################################

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${YELLOW}  Uninstalling PoeBot System Service${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Stop service if running
if systemctl is-active --quiet poebot; then
    echo -e "${BLUE}Stopping service...${NC}"
    sudo systemctl stop poebot
    echo -e "${GREEN}✓${NC} Service stopped"
fi

# Disable service
if systemctl is-enabled --quiet poebot 2>/dev/null; then
    echo -e "${BLUE}Disabling service...${NC}"
    sudo systemctl disable poebot
    echo -e "${GREEN}✓${NC} Service disabled"
fi

# Remove service file
if [ -f "/etc/systemd/system/poebot.service" ]; then
    echo -e "${BLUE}Removing service file...${NC}"
    sudo rm /etc/systemd/system/poebot.service
    echo -e "${GREEN}✓${NC} Service file removed"
fi

# Reload systemd
echo -e "${BLUE}Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload

echo ""
echo -e "${GREEN}✓ Service uninstalled successfully${NC}"
echo ""
echo "The bot will no longer start automatically on boot."
echo "You can still start it manually with: ./start_bot.sh"

