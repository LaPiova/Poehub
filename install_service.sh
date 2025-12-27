#!/bin/bash

###############################################################################
# Install PoeBot as a System Service
# Enables automatic start on server boot
###############################################################################

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}  Installing PoeBot System Service${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

INSTANCE_NAME="${POEHUB_REDBOT_INSTANCE:-PoeBot}"
SERVICE_NAME="${POEHUB_SERVICE_NAME:-poebot}"

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}✗${NC} Do NOT run this script as root/sudo"
    echo "Run as: ./install_service.sh"
    echo "The script will request sudo when needed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$HOME/.redenv" ]; then
    echo -e "${RED}✗${NC} Virtual environment not found at ~/.redenv"
    echo "Please run: ./fix_python_version.sh"
    exit 1
fi

# Create systemd service file
SERVICE_FILE="/tmp/${SERVICE_NAME}.service"

echo -e "${BLUE}Creating service file...${NC}"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=${INSTANCE_NAME} - Red-DiscordBot with Poe API Integration
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
Environment="PATH=$HOME/.redenv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$HOME/.redenv/bin/redbot ${INSTANCE_NAME} --no-prompt
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓${NC} Service file created"

# Install service file
echo -e "${BLUE}Installing service (requires sudo)...${NC}"
sudo cp "$SERVICE_FILE" "/etc/systemd/system/${SERVICE_NAME}.service"
sudo chmod 644 "/etc/systemd/system/${SERVICE_NAME}.service"

echo -e "${GREEN}✓${NC} Service file installed"

# Reload systemd
echo -e "${BLUE}Reloading systemd daemon...${NC}"
sudo systemctl daemon-reload

echo -e "${GREEN}✓${NC} Systemd reloaded"

# Enable service
echo -e "${BLUE}Enabling service to start on boot...${NC}"
sudo systemctl enable "${SERVICE_NAME}.service"

echo -e "${GREEN}✓${NC} Service enabled"

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}✓ Installation Complete!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""
echo "Service Commands:"
echo "  ${GREEN}Start bot:${NC}      sudo systemctl start ${SERVICE_NAME}"
echo "  ${GREEN}Stop bot:${NC}       sudo systemctl stop ${SERVICE_NAME}"
echo "  ${GREEN}Restart bot:${NC}    sudo systemctl restart ${SERVICE_NAME}"
echo "  ${GREEN}Check status:${NC}   sudo systemctl status ${SERVICE_NAME}"
echo "  ${GREEN}View logs:${NC}      sudo journalctl -u ${SERVICE_NAME} -f"
echo "  ${GREEN}Disable autostart:${NC} sudo systemctl disable ${SERVICE_NAME}"
echo ""
echo -e "${YELLOW}Note:${NC} Bot will now start automatically when server boots"
echo ""
echo "Start the bot now? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    sudo systemctl start "${SERVICE_NAME}"
    sleep 2
    sudo systemctl status "${SERVICE_NAME}" --no-pager
fi

