# VibeVoice macOS App Bundle

This document explains how to create and use the VibeVoice macOS app bundle with menu bar support.

## Menu Bar Mode

VibeVoice can run with a menu bar icon on macOS for easy control.

### Installation

```bash
# Install menu bar dependency
pip install rumps
```

### Usage

```bash
# Launch with menu bar icon
python launch_menubar.py
```

The menu bar provides:
- **Start/Stop** buttons to control VibeVoice
- **Status indicator** showing if VibeVoice is running
- **Help** and **About** dialogs
- **Quick reference** for keyboard shortcuts

### Keyboard Shortcuts (Default)

| Mode | Key | Description |
|------|-----|-------------|
| Dictation | Right Command (⌘) | Speak to type text |
| AI Command | F12 | Ask AI questions |
| AI with Screenshot | Right Option (⌥) | AI with screen context |

## Creating a Standalone App

### Prerequisites

```bash
# Install build dependencies
pip install pyinstaller pillow

# (Optional) Install menu bar support
pip install rumps
```

### Build the App

```bash
# Build the .app bundle
python build.py
```

This will create `dist/VibeVoice.app` - a standalone macOS application.

### Install the App

```bash
# Move to Applications
mv dist/VibeVoice.app /Applications/

# Run the app
open /Applications/VibeVoice.app
```

## Installing as LaunchAgent (Auto-start)

### Standard Mode (CLI)

```bash
./install-service.sh
```

### Menu Bar Mode

Edit `com.vibevoice.agent.plist` to point to `launch_menubar.py`:

```xml
<key>ProgramArguments</key>
<array>
    <string>/usr/bin/python3</string>
    <string>/path/to/tallahassee/launch_menubar.py</string>
</array>
```

Then run:

```bash
./install-service.sh
```

## Troubleshooting

### Menu bar icon not showing

- Ensure rumps is installed: `pip install rumps`
- Check macOS permissions in System Preferences > Privacy & Security

### App won't open

- Right-click the app and select "Open" (bypasses Gatekeeper)
- Or run: `xattr -cr dist/VibeVoice.app`

### Background audio permissions

VibeVoice needs microphone access:
1. System Settings > Privacy & Security > Microphone
2. Enable VibeVoice
