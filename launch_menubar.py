#!/usr/bin/env python3
"""
Launch VibeVoice with macOS menu bar icon
This provides a menu bar icon to control VibeVoice
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("🎙️  Launching VibeVoice with menu bar...")

    # Check if running on macOS
    if sys.platform != "darwin":
        print("⚠️  Menu bar is only available on macOS")
        print("   Falling back to standard launch...")
        from vibevoice.cli import main as cli_main
        cli_main()
        return

    try:
        import rumps
        print("✅ Menu bar support available")

        # Launch with menu bar
        from vibevoice.menubar import start_menubar
        start_menubar()

    except ImportError:
        print("⚠️  rumps not installed. Install with: pip install rumps")
        print("   Falling back to standard launch...")
        from vibevoice.cli import main as cli_main
        cli_main()

if __name__ == "__main__":
    main()
