#!/bin/bash

# VibeVoice Service Management Script
# Provides easy commands to control the VibeVoice service

PLIST_PATH="$HOME/Library/LaunchAgents/com.vibevoice.agent.plist"
SERVICE_NAME="com.vibevoice.agent"
LOGS_DIR="$HOME/Library/Logs/VibeVoice"

show_usage() {
    echo "🎙️ VibeVoice Service Manager"
    echo "==========================="
    echo ""
    echo "Usage: ./manage-service.sh <command>"
    echo ""
    echo "Commands:"
    echo "  status     - Show service status"
    echo "  start      - Start the service"
    echo "  stop       - Stop the service"
    echo "  restart    - Restart the service"
    echo "  logs       - Show recent logs"
    echo "  follow     - Follow logs in real-time"
    echo "  install    - Install the service"
    echo "  uninstall  - Remove the service"
    echo ""
}

check_service_exists() {
    if [[ ! -f "$PLIST_PATH" ]]; then
        echo "❌ VibeVoice service not installed. Run: ./install-service.sh"
        exit 1
    fi
}

show_status() {
    if [[ ! -f "$PLIST_PATH" ]]; then
        echo "🔴 Service not installed"
        return
    fi

    if launchctl list | grep -q "$SERVICE_NAME"; then
        echo "🟢 VibeVoice service is running"
        launchctl list | grep "$SERVICE_NAME"
    else
        echo "🔴 VibeVoice service is not running"
    fi
}

start_service() {
    check_service_exists
    echo "🚀 Starting VibeVoice service..."
    launchctl start "$SERVICE_NAME"
    sleep 1
    show_status
}

stop_service() {
    check_service_exists
    echo "⏹️ Stopping VibeVoice service..."
    launchctl stop "$SERVICE_NAME"
    sleep 1
    show_status
}

restart_service() {
    check_service_exists
    echo "🔄 Restarting VibeVoice service..."
    launchctl kickstart -k "gui/$(id -u)/$SERVICE_NAME"
    sleep 2
    show_status
}

show_logs() {
    if [[ -f "$LOGS_DIR/stdout.log" ]]; then
        echo "📝 Recent stdout logs:"
        echo "===================="
        tail -20 "$LOGS_DIR/stdout.log"
    fi
    
    if [[ -f "$LOGS_DIR/stderr.log" ]]; then
        echo ""
        echo "⚠️ Recent stderr logs:"
        echo "===================="
        tail -20 "$LOGS_DIR/stderr.log"
    fi
    
    if [[ ! -f "$LOGS_DIR/stdout.log" && ! -f "$LOGS_DIR/stderr.log" ]]; then
        echo "📝 No logs found at $LOGS_DIR"
    fi
}

follow_logs() {
    if [[ -f "$LOGS_DIR/stdout.log" ]]; then
        echo "📝 Following VibeVoice logs... (Ctrl+C to exit)"
        tail -f "$LOGS_DIR/stdout.log"
    else
        echo "📝 No logs found at $LOGS_DIR/stdout.log"
    fi
}

install_service() {
    if [[ -f "./install-service.sh" ]]; then
        ./install-service.sh
    else
        echo "❌ install-service.sh not found in current directory"
        exit 1
    fi
}

uninstall_service() {
    if [[ -f "./uninstall-service.sh" ]]; then
        ./uninstall-service.sh
    else
        echo "🗑️ Uninstalling VibeVoice service..."
        if [[ -f "$PLIST_PATH" ]]; then
            launchctl unload "$PLIST_PATH" 2>/dev/null || true
            rm "$PLIST_PATH"
            echo "✅ Service uninstalled successfully"
        else
            echo "❌ Service not found"
        fi
    fi
}

# Main script logic
case "$1" in
    "status")
        show_status
        ;;
    "start")
        start_service
        ;;
    "stop")
        stop_service
        ;;
    "restart")
        restart_service
        ;;
    "logs")
        show_logs
        ;;
    "follow")
        follow_logs
        ;;
    "install")
        install_service
        ;;
    "uninstall")
        uninstall_service
        ;;
    *)
        show_usage
        ;;
esac