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

SERVICE_NAME="${POEHUB_SERVICE_NAME:-poebot}"

# Stop service if running
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${BLUE}Stopping service...${NC}"
    sudo systemctl stop "$SERVICE_NAME"
    echo -e "${GREEN}✓${NC} Service stopped"
fi

# Disable service
if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${BLUE}Disabling service...${NC}"
    sudo systemctl disable "$SERVICE_NAME"
    echo -e "${GREEN}✓${NC} Service disabled"
fi

# Remove service file
if [ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]; then
    echo -e "${BLUE}Removing service file...${NC}"
    sudo rm "/etc/systemd/system/${SERVICE_NAME}.service"
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

