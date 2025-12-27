#!/bin/bash

###############################################################################
# Sync PoeHub files to Red-DiscordBot cogs directory
# Run this after making changes to sync them to the bot
###############################################################################

SOURCE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
COG_SOURCE_DIR="$SOURCE_DIR/src/poehub"
TARGET_DIR="$HOME/red-cogs/poehub"

set -euo pipefail

echo "🔄 Syncing PoeHub files..."
echo "Source: $SOURCE_DIR"
echo "Target: $TARGET_DIR"
echo ""

if [ ! -d "$COG_SOURCE_DIR" ]; then
  echo "❌ Could not find cog source directory: $COG_SOURCE_DIR"
  echo "Expected layout: $SOURCE_DIR/src/poehub/"
  exit 1
fi

mkdir -p "$HOME/red-cogs"
rm -rf "$TARGET_DIR"

echo "Copying cog package from $COG_SOURCE_DIR to $TARGET_DIR"
cp -R "$COG_SOURCE_DIR" "$TARGET_DIR"

echo ""
echo "✅ Files synced successfully!"
echo ""
echo "Files in $TARGET_DIR:"
find "$TARGET_DIR" -maxdepth 2 -type f \( -name "*.py" -o -name "*.json" \) -print 2>/dev/null || true
echo ""
echo "🔍 Verifying deployment:"
grep "encryption_key" "$TARGET_DIR/poehub.py" || echo "❌ KEY NOT FOUND IN DEPLOYED FILE"
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

