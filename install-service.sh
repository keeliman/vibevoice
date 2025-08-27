#!/bin/bash

# VibeVoice Service Installation Script
# This script installs VibeVoice as a macOS LaunchAgent service

set -e

echo "🎙️ VibeVoice Service Installer"
echo "=============================="

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This script is only for macOS"
    exit 1
fi

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_SOURCE="$SCRIPT_DIR/com.vibevoice.agent.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/com.vibevoice.agent.plist"
LOGS_DIR="$HOME/Library/Logs/VibeVoice"

# Security: Get current user's Python path dynamically
PYTHON_BIN_DIR="$(python3 -c "import sys; import os; print(os.path.dirname(sys.executable))")"
USER_PYTHON_BIN="$HOME/Library/Python/$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")/bin"

# Create LaunchAgents directory if it doesn't exist
if [[ ! -d "$LAUNCH_AGENTS_DIR" ]]; then
    echo "📁 Creating LaunchAgents directory..."
    mkdir -p "$LAUNCH_AGENTS_DIR"
fi

# Create logs directory if it doesn't exist
if [[ ! -d "$LOGS_DIR" ]]; then
    echo "📝 Creating logs directory..."
    mkdir -p "$LOGS_DIR"
fi

# Check if service is already loaded
if launchctl list | grep -q "com.vibevoice.agent"; then
    echo "🔄 Unloading existing service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Security: Create customized plist with dynamic paths
echo "📋 Installing service configuration..."
sed \
    -e "s|VIBEVOICE_APP_PATH|$SCRIPT_DIR|g" \
    -e "s|VIBEVOICE_LOG_PATH|$LOGS_DIR|g" \
    -e "s|PYTHON_BIN_PATH|$USER_PYTHON_BIN|g" \
    "$PLIST_SOURCE" > "$PLIST_DEST"

# Set proper permissions
chmod 644 "$PLIST_DEST"

# Load the service
echo "🚀 Loading VibeVoice service..."
launchctl load "$PLIST_DEST"

# Check if service is running
sleep 2
if launchctl list | grep -q "com.vibevoice.agent"; then
    echo "✅ VibeVoice service installed and running!"
    echo ""
    echo "📖 Service Management Commands:"
    echo "   Stop service:    launchctl stop com.vibevoice.agent"
    echo "   Start service:   launchctl start com.vibevoice.agent" 
    echo "   Restart service: launchctl kickstart -k gui/$(id -u)/com.vibevoice.agent"
    echo "   Uninstall:       ./uninstall-service.sh"
    echo ""
    echo "📝 Logs available at:"
    echo "   Stdout: $LOGS_DIR/stdout.log"
    echo "   Stderr: $LOGS_DIR/stderr.log"
    echo ""
    echo "🎉 VibeVoice is now running as a background service!"
else
    echo "❌ Service installation failed. Check logs at $LOGS_DIR"
    exit 1
fi