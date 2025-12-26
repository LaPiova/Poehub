#!/bin/bash

###############################################################################
# Sync PoeHub files to Red-DiscordBot cogs directory
# Run this after making changes to sync them to the bot
###############################################################################

SOURCE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
TARGET_DIR="$HOME/red-cogs/poehub"

set -euo pipefail

echo "🔄 Syncing PoeHub files..."
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo ""

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Copy files
echo "Copying files from $SOURCE_DIR to $TARGET_DIR"
cp "$SOURCE_DIR/poehub.py" "$TARGET_DIR/"
cp "$SOURCE_DIR/api_client.py" "$TARGET_DIR/"
cp "$SOURCE_DIR/conversation_manager.py" "$TARGET_DIR/"
cp "$SOURCE_DIR/encryption.py" "$TARGET_DIR/"
cp "$SOURCE_DIR/__init__.py" "$TARGET_DIR/"
cp "$SOURCE_DIR/info.json" "$TARGET_DIR/"

echo ""
echo "✅ Files synced successfully!"
echo ""
echo "Files in $TARGET_DIR:"
ls -lh "$TARGET_DIR"/*.py "$TARGET_DIR"/*.json 2>/dev/null || true
echo ""
echo "📝 Next steps in Discord:"
echo ""
echo "   If first time loading:"
echo "     !addpath $HOME/red-cogs"
echo "     !load poehub"
echo ""
echo "   If already loaded:"
echo "     !reload poehub"
echo ""
echo "   Note: Use absolute path, not ~/red-cogs"
echo ""

