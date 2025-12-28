#!/bin/bash

###############################################################################
# PoeHub Deployment Script for Arch Linux
# This script sets up a fresh Red-DiscordBot instance with the PoeHub cog
###############################################################################

set -e  # Exit on error

if ! command -v pacman &> /dev/null; then
    echo "This script requires pacman. Please run it on Arch Linux or a derivative."
    exit 1
fi

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
print_status "Step 1: Updating system and installing dependencies via pacman..."

sudo pacman -Syu --noconfirm
sudo pacman -S --needed --noconfirm python python-pip git screen curl

print_success "System dependencies installed!"

###############################################################################
# Step 2: Create Virtual Environment
###############################################################################
print_status "Step 2: Creating virtual environment..."

# Determine compatible Python interpreter (Red-DiscordBot supports 3.8.1 - 3.11.x)
PYTHON_CMD=""

if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
    print_status "Using Python 3.11 (Red-DiscordBot compatible)"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    print_error "No Python installation found. Install Python 3.11 (e.g., via \`yay -S python311\` or pyenv) and re-run this script."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ne 3 ] || [ "$PYTHON_MINOR" -gt 11 ]; then
    print_error "Python $PYTHON_VERSION detected, but Red-DiscordBot requires Python 3.8.1 through 3.11.x."
    print_error "Install Python 3.11 (for Arch, use an AUR package such as python311 or a pyenv install) and re-run this script."
    exit 1
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

cat > "$HOME/start_bot.sh" <<'BOT_SCRIPT'
#!/bin/bash

# Activate virtual environment
source "$HOME/.redenv/bin/activate"

# Start the bot
echo "Starting ${POEHUB_REDBOT_INSTANCE:-PoeBot}..."
redbot "${POEHUB_REDBOT_INSTANCE:-PoeBot}"

# Deactivate venv on exit
deactivate
BOT_SCRIPT

chmod +x "$HOME/start_bot.sh"
print_success "Startup script created at ~/start_bot.sh"



###############################################################################
# Step 7: Create Systemd Service (Optional)
###############################################################################
print_status "Step 7: Creating systemd service file..."

SERVICE_NAME="${POEHUB_SERVICE_NAME:-poebot}"
cat > "$HOME/${SERVICE_NAME}.service" <<'SERVICE_UNIT'
[Unit]
Description=Red-DiscordBot - ${POEHUB_REDBOT_INSTANCE:-PoeBot} Instance
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
ExecStart=$HOME/.redenv/bin/redbot ${POEHUB_REDBOT_INSTANCE:-PoeBot}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_UNIT

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
echo "   OR use screen manually."

echo ""
echo "2. In Discord, add the custom cog repository:"
echo "   ${YELLOW}[p]addpath $COGS_DIR${NC}"

echo "3. Load the PoeHub cog:"
echo "   ${YELLOW}[p]load poehub${NC}"

echo "4. Set your Poe API key (bot owner only):"
echo "   ${YELLOW}[p]poeapikey <your_poe_api_key>${NC}"

echo "5. Start using PoeHub:"
echo "   ${YELLOW}[p]ask How does quantum computing work?${NC}"
echo "   ${YELLOW}[p]setmodel GPT-4o${NC}"
echo "   ${YELLOW}[p]privatemode${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}For more help:${NC}"
echo "  [p]help PoeHub"
echo "  [p]listmodels"

echo -e "${BLUE}Bot Directory:${NC} $HOME/.local/share/Red-DiscordBot/data/${INSTANCE_NAME}"
echo -e "${BLUE}Cog Location:${NC} $COGS_DIR/poehub"
echo -e "${BLUE}Startup Script:${NC} $HOME/start_bot.sh"

echo ""
echo "=========================================="
echo -e "${GREEN}Happy chatting with Poe! 🤖${NC}"
echo "=========================================="

