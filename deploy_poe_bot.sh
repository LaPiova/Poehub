#!/bin/bash

###############################################################################
# PoeHub Deployment Script for Ubuntu
# This script sets up a fresh Red-DiscordBot instance with the PoeHub cog
###############################################################################

set -e  # Exit on error

echo "=========================================="
echo "  PoeHub Deployment Script"
echo "=========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

###############################################################################
# Step 1: System Preparation
###############################################################################
print_status "Step 1: Updating system and installing dependencies..."

sudo apt update
sudo apt install -y python3 python3-venv python3-pip git screen curl

# Try to install Python 3.11 if not present (for Red-DiscordBot compatibility)
if ! command -v python3.11 &> /dev/null; then
    print_status "Installing Python 3.11 for Red-DiscordBot compatibility..."
    sudo apt install -y python3.11 python3.11-venv python3.11-dev || true
fi

print_success "System dependencies installed!"

###############################################################################
# Step 2: Create Virtual Environment
###############################################################################
print_status "Step 2: Creating virtual environment..."

# Check Python version and use compatible version
PYTHON_CMD="python3"

# Red-DiscordBot requires Python 3.8.1 to 3.11.x (not 3.12+)
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    print_status "Using Python 3.11 (Red-DiscordBot compatible)"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
    print_status "Using Python 3.10 (Red-DiscordBot compatible)"
elif command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
    print_status "Using Python 3.9 (Red-DiscordBot compatible)"
else
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 12 ]; then
        print_error "Python 3.12+ detected, but Red-DiscordBot requires Python 3.8.1 to 3.11.x"
        print_error "Please install Python 3.11: sudo apt install python3.11 python3.11-venv"
        exit 1
    fi
fi

# Create venv if it doesn't exist
if [ ! -d "$HOME/.redenv" ]; then
    $PYTHON_CMD -m venv "$HOME/.redenv"
    print_success "Virtual environment created at ~/.redenv with $PYTHON_CMD"
else
    print_warning "Virtual environment already exists at ~/.redenv"
fi

# Activate virtual environment
source "$HOME/.redenv/bin/activate"
print_success "Virtual environment activated!"

###############################################################################
# Step 3: Install Red-DiscordBot and Dependencies
###############################################################################
print_status "Step 3: Installing Red-DiscordBot and dependencies..."

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install Red-DiscordBot
pip install Red-DiscordBot

# Install PoeHub dependencies
pip install openai cryptography

print_success "All packages installed!"

###############################################################################
# Step 4: Run Red-DiscordBot Setup
###############################################################################
INSTANCE_NAME="${POEHUB_REDBOT_INSTANCE:-PoeBot}"
COGS_DIR="${POEHUB_COGS_DIR:-$HOME/red-cogs}"

print_status "Step 4: Setting up Red-DiscordBot instance '${INSTANCE_NAME}'..."

# Check if instance already exists
if [ -d "$HOME/.local/share/Red-DiscordBot/data/${INSTANCE_NAME}" ]; then
    print_warning "Instance '${INSTANCE_NAME}' already exists. Skipping setup..."
else
    print_status "Running redbot-setup..."
    print_warning "You will need to provide your Discord bot token and make some choices."
    echo ""
    
    # Run setup interactively
    redbot-setup
    
    print_success "Red-DiscordBot setup complete!"
fi

###############################################################################
# Step 5: Create Custom Cog Directory
###############################################################################
print_status "Step 5: Creating custom cog directory..."

# Create cogs directory
mkdir -p "$COGS_DIR"

# Copy PoeHub files
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if we're in the Poehub directory
if [ -d "$SCRIPT_DIR/src/poehub" ]; then
    rm -rf "$COGS_DIR/poehub"
    cp -R "$SCRIPT_DIR/src/poehub" "$COGS_DIR/poehub"
    print_success "PoeHub cog package copied to $COGS_DIR/poehub/"
else
    print_error "PoeHub files not found! Expected: $SCRIPT_DIR/src/poehub"
    exit 1
fi

###############################################################################
# Step 6: Create Startup Script
###############################################################################
print_status "Step 6: Creating startup script..."

cat > "$HOME/start_bot.sh" << 'EOF'
#!/bin/bash

# Activate virtual environment
source "$HOME/.redenv/bin/activate"

# Start the bot
echo "Starting ${POEHUB_REDBOT_INSTANCE:-PoeBot}..."
redbot "${POEHUB_REDBOT_INSTANCE:-PoeBot}"

# Deactivate venv on exit
deactivate
EOF

chmod +x "$HOME/start_bot.sh"
print_success "Startup script created at ~/start_bot.sh"

###############################################################################
# Step 7: Create Screen Session Helper
###############################################################################
print_status "Step 7: Creating screen session helper..."

cat > "$HOME/start_bot_screen.sh" << 'EOF'
#!/bin/bash

# Start bot in a detached screen session
screen -dmS "${POEHUB_SCREEN_NAME:-poebot}" bash -c "source $HOME/.redenv/bin/activate && redbot ${POEHUB_REDBOT_INSTANCE:-PoeBot}"

echo "Bot started in screen session 'poebot'"
echo "To attach: screen -r poebot"
echo "To detach: Press Ctrl+A then D"
EOF

chmod +x "$HOME/start_bot_screen.sh"
print_success "Screen helper created at ~/start_bot_screen.sh"

###############################################################################
# Step 8: Create Systemd Service (Optional)
###############################################################################
print_status "Step 8: Creating systemd service file..."

SERVICE_NAME="${POEHUB_SERVICE_NAME:-poebot}"
cat > "$HOME/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Red-DiscordBot - ${INSTANCE_NAME} Instance
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=$HOME/.redenv/bin/redbot ${INSTANCE_NAME}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

print_success "Systemd service file created at ~/${SERVICE_NAME}.service"
print_warning "To install the service, run:"
print_warning "  sudo cp ~/${SERVICE_NAME}.service /etc/systemd/system/"
print_warning "  sudo systemctl daemon-reload"
print_warning "  sudo systemctl enable ${SERVICE_NAME}.service"
print_warning "  sudo systemctl start ${SERVICE_NAME}.service"

###############################################################################
# Deployment Complete!
###############################################################################
echo ""
echo "=========================================="
print_success "DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo ""
echo "1. Start the bot:"
echo "   ${GREEN}~/start_bot.sh${NC}"
echo "   OR use screen:"
echo "   ${GREEN}~/start_bot_screen.sh${NC}"
echo ""
echo "2. In Discord, add the custom cog repository:"
echo "   ${YELLOW}[p]addpath $COGS_DIR${NC}"
echo ""
echo "3. Load the PoeHub cog:"
echo "   ${YELLOW}[p]load poehub${NC}"
echo ""
echo "4. Set your Poe API key (bot owner only):"
echo "   ${YELLOW}[p]poeapikey <your_poe_api_key>${NC}"
echo ""
echo "5. Start using PoeHub:"
echo "   ${YELLOW}[p]ask How does quantum computing work?${NC}"
echo "   ${YELLOW}[p]setmodel GPT-4o${NC}"
echo "   ${YELLOW}[p]privatemode${NC}"
echo ""
echo "=========================================="
echo -e "${GREEN}For more help:${NC}"
echo "  [p]help PoeHub"
echo "  [p]listmodels"
echo ""
echo -e "${BLUE}Bot Directory:${NC} $HOME/.local/share/Red-DiscordBot/data/${INSTANCE_NAME}"
echo -e "${BLUE}Cog Location:${NC} $COGS_DIR/poehub"
echo -e "${BLUE}Startup Script:${NC} $HOME/start_bot.sh"
echo ""
echo "=========================================="
echo -e "${GREEN}Happy chatting with Poe! 🤖${NC}"
echo "=========================================="

