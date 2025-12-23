#!/bin/bash

###############################################################################
# Fix Python Version for Red-DiscordBot
# Red-DiscordBot requires Python 3.8.1 to 3.11.x (NOT 3.12+)
###############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}  Python Version Fix for PoeHub${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Check for Python 3.11
if command -v python3.11 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python 3.11 found"
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python 3.10 found"
    PYTHON_CMD="python3.10"
elif command -v python3.9 &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python 3.9 found"
    PYTHON_CMD="python3.9"
else
    echo -e "${RED}✗${NC} No compatible Python version found (need 3.8-3.11)"
    echo ""
    echo "Installing Python 3.11..."
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3.11-dev
    PYTHON_CMD="python3.11"
fi

echo ""
echo "Python version: $($PYTHON_CMD --version)"
echo ""

# Remove old virtual environment
if [ -d "$HOME/.redenv" ]; then
    echo -e "${YELLOW}Removing old virtual environment...${NC}"
    rm -rf "$HOME/.redenv"
    echo -e "${GREEN}✓${NC} Old venv removed"
fi

# Create new virtual environment with correct Python version
echo -e "${BLUE}Creating new virtual environment with $PYTHON_CMD...${NC}"
$PYTHON_CMD -m venv "$HOME/.redenv"
echo -e "${GREEN}✓${NC} New venv created"

# Activate and install packages
source "$HOME/.redenv/bin/activate"

echo ""
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip setuptools wheel

echo ""
echo -e "${BLUE}Installing Red-DiscordBot and dependencies...${NC}"
pip install Red-DiscordBot openai cryptography

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}✓ Python environment fixed!${NC}"
echo -e "${GREEN}=========================================${NC}"
echo ""
echo "Python version in venv: $(python --version)"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Continue with bot setup: redbot-setup"
echo "2. Or run the full deployment: ./deploy_poe_bot.sh"

