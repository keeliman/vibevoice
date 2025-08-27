#!/bin/bash

# VibeVoice Service Uninstallation Script
# This script removes the VibeVoice LaunchAgent service

set -e

echo "🗑️ VibeVoice Service Uninstaller"
echo "================================"

PLIST_PATH="$HOME/Library/LaunchAgents/com.vibevoice.agent.plist"
SERVICE_NAME="com.vibevoice.agent"
LOGS_DIR="$HOME/Library/Logs/VibeVoice"

# Check if service exists
if [[ ! -f "$PLIST_PATH" ]]; then
    echo "❌ VibeVoice service is not installed"
    exit 0
fi

# Stop and unload the service
echo "⏹️ Stopping and unloading service..."
launchctl stop "$SERVICE_NAME" 2>/dev/null || true
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Remove the plist file
echo "🗂️ Removing service configuration..."
rm "$PLIST_PATH"

# Ask about log files
if [[ -d "$LOGS_DIR" ]]; then
    echo ""
    read -p "🤔 Remove log files at $LOGS_DIR? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$LOGS_DIR"
        echo "📝 Log files removed"
    else
        echo "📝 Log files preserved"
    fi
fi

# Verify removal
if launchctl list | grep -q "$SERVICE_NAME"; then
    echo "⚠️ Service may still be running. Try restarting your session."
else
    echo "✅ VibeVoice service successfully uninstalled!"
fi

echo ""
echo "📖 To reinstall later, run: ./install-service.sh"