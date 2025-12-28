#!/bin/bash

###############################################################################
# PoeHub Test Runner
# This script sets up the environment and runs the unit tests with coverage
###############################################################################

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}  Running PoeHub Tests...${NC}"
echo -e "${BLUE}=========================================${NC}"

# Detect virtual environment
VENV_PATH=""

if [ -d ".venv" ]; then
    VENV_PATH=".venv"
elif [ -d "$HOME/.redenv" ]; then
    VENV_PATH="$HOME/.redenv"
fi

if [ -n "$VENV_PATH" ]; then
    echo -e "Using virtual environment at: ${BLUE}$VENV_PATH${NC}"
    source "$VENV_PATH/bin/activate"
else
    echo -e "${RED}Warning: No virtual environment found (.venv or ~/.redenv).${NC}"
    echo "Attempting to run with system python..."
fi

# Check if development dependencies are installed
if ! python3 -c "import pytest" &> /dev/null; then
    echo -e "${RED}pytest not found!${NC}"
    echo "Installing dev dependencies..."
    pip install -r requirements-dev.txt
fi

# Run Ruff Linting
echo ""
echo -e "${BLUE}Running Ruff Linting...${NC}"
if ! ruff check .; then
    echo -e "${RED}❌ Ruff linting failed! Please fix coding style issues.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Ruff linting passed!${NC}"

# Run tests
echo ""
echo -e "${BLUE}Executing pytest...${NC}"
echo "----------------------------------------"

# Set PYTHONPATH to include src directory and run pytest
export PYTHONPATH=$PYTHONPATH:$(pwd)/src

python3 -m pytest tests/ --cov=src/poehub --cov-report=term-missing

EXIT_CODE=$?

echo "----------------------------------------"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed.${NC}"
fi

exit $EXIT_CODE
