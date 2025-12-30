"""macOS menu bar integration for VibeVoice"""

import os
import sys
import threading
import subprocess
from typing import Optional, Callable

# Platform check - menu bar only available on macOS
if sys.platform == "darwin":
    try:
        import rumps
        RUMPS_AVAILABLE = True
    except ImportError:
        RUMPS_AVAILABLE = False
else:
    RUMPS_AVAILABLE = False


class VibeVoiceMenuBar:
    """macOS menu bar app for VibeVoice"""

    def __init__(self):
        self.app: Optional['rumps.App'] = None
        self.vibevoice_process: Optional[subprocess.Popen] = None
        self.server_process: Optional[subprocess.Popen] = None
        self._on_stop_callback: Optional[Callable] = None
        self._vibevoice_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def is_available(self) -> bool:
        """Check if menu bar is available on this platform"""
        return RUMPS_AVAILABLE

    def start(self, on_stop_callback: Optional[Callable] = None):
        """Start the menu bar app"""
        if not self.is_available():
            print("⚠️  Menu bar not available. Install rumps: pip install rumps")
            print("   Or run VibeVoice directly: python launch.py")
            return False

        self._on_stop_callback = on_stop_callback
        self._create_menu()

        # Auto-start VibeVoice when menubar launches
        print("🚀 Menubar starting, auto-launching VibeVoice...", flush=True)
        import threading
        def auto_start():
            import time
            time.sleep(1)  # Wait for menubar to be ready
            self._on_start(self.start_button)

        start_thread = threading.Thread(target=auto_start, daemon=True)
        start_thread.start()

        self.app.run()
        return True

    def _create_menu(self):
        """Create the menu bar interface"""
        self.app = rumps.App(
            "VibeVoice",
            icon=None,  # Can add icon path here
            template=True,  # Use macOS dark/light mode compatible icon
            quit_button=None  # We'll add our own quit button
        )

        # Status menu items
        self.status_menu = rumps.MenuItem("Status: Stopped", callback=None)
        self.start_button = rumps.MenuItem("▶ Start VibeVoice", callback=self._on_start)
        self.stop_button = rumps.MenuItem("⏹ Stop VibeVoice", callback=self._on_stop)
        self.stop_button.enabled = False
        self.pause_button = rumps.MenuItem("⏸ Pause", callback=self._on_pause)
        self.pause_button.enabled = False

        # Separator
        rumps.separator = rumps.separator

        # Settings menu
        self.dictation_key_item = rumps.MenuItem(
            f"Dictation Key: {os.getenv('VOICEKEY', 'cmd_r')}",
            callback=None
        )
        self.cmd_key_item = rumps.MenuItem(
            f"AI Command Key: {os.getenv('VOICEKEY_CMD', 'f12')}",
            callback=None
        )
        self.screenshot_key_item = rumps.MenuItem(
            f"Screenshot Key: {os.getenv('VOICEKEY_SCREENSHOT', 'alt_r')}",
            callback=None
        )

        # Separator
        rumps.separator = rumps.separator

        # Info menu
        self.help_button = rumps.MenuItem("❓ Help", callback=self._on_help)
        self.about_button = rumps.MenuItem("ℹ️ About", callback=self._on_about)

        # Separator
        rumps.separator = rumps.separator

        # Quit button
        self.quit_button = rumps.MenuItem("Quit VibeVoice", callback=self._on_quit)

        # Add all items to menu
        self.app.menu = [
            self.status_menu,
            self.start_button,
            self.stop_button,
            self.pause_button,
            rumps.separator,
            self.dictation_key_item,
            self.cmd_key_item,
            self.screenshot_key_item,
            rumps.separator,
            self.help_button,
            self.about_button,
            rumps.separator,
            self.quit_button,
        ]

    def _on_start(self, sender):
        """Start VibeVoice process"""
        if self._vibevoice_thread is not None and self._vibevoice_thread.is_alive():
            rumps.alert("VibeVoice is already running!", title="Info")
            return

        try:
            # Reset stop event
            self._stop_event.clear()

            # Import control state to set running
            from .control_state import set_running, set_paused
            set_running(True)
            set_paused(False)

            # Start VibeVoice in a separate thread
            def run_vibevoice():
                try:
                    # Import and run main
                    from . import cli
                    print("🎯 CLI thread starting...", flush=True)
                    cli.main()
                    print("✅ CLI thread finished normally", flush=True)
                except Exception as e:
                    print(f"❌ Error in VibeVoice: {e}", flush=True)
                    import traceback
                    traceback.print_exc()
                finally:
                    # Update status when done
                    from .control_state import set_running
                    set_running(False)
                    self._update_status(stopped=True)
                    print("🔄 Status updated to stopped", flush=True)

            self._vibevoice_thread = threading.Thread(target=run_vibevoice, daemon=True)
            self._vibevoice_thread.start()

            sender.title = "🔄 Starting..."

            # Check if it started successfully
            import time
            time.sleep(2)
            if self._vibevoice_thread.is_alive():
                sender.title = "▶ Start VibeVoice"
                self._update_status(running=True)
            else:
                self._update_status(stopped=True)
                rumps.alert("Failed to start VibeVoice")

        except Exception as e:
            rumps.alert(f"Error: {e}")
            self._update_status(stopped=True)

    def _on_pause(self, sender):
        """Pause/Resume VibeVoice"""
        from .control_state import toggle_pause, is_paused

        if self._vibevoice_thread is None or not self._vibevoice_thread.is_alive():
            return

        try:
            paused = toggle_pause()
            if paused:
                sender.title = "▶ Resume"
                self.status_menu.title = "⏸ Status: Paused"
                rumps.notification_unit(
                    title="VibeVoice",
                    subtitle="Paused - Hold hotkey to resume",
                    sound=False
                )
            else:
                sender.title = "⏸ Pause"
                self.status_menu.title = "● Status: Running"
                rumps.notification_unit(
                    title="VibeVoice",
                    subtitle="Resumed",
                    sound=False
                )
        except Exception as e:
            rumps.alert(f"Error toggling pause: {e}", title="Error")

    def _on_stop(self, sender):
        """Stop VibeVoice process"""
        # Signal thread to stop
        self._stop_event.set()

        # Update control state
        try:
            from .control_state import set_running, set_paused
            set_running(False)
            set_paused(False)
        except:
            pass

        # Reset thread reference
        self._vibevoice_thread = None
        self._update_status(stopped=True)

    def _on_help(self, sender):
        """Show help dialog"""
        help_text = """
VibeVoice - Voice-to-Text with AI Commands

🎙️ Dictation Mode:
   Hold Right Command (⌘) and speak

🤖 AI Command Mode:
   Hold F12 and speak your command

📷 AI with Screenshot:
   Hold Right Option (⌥) and speak

Keys can be customized via environment variables.
        """
        rumps.alert(help_text.strip(), title="VibeVoice Help", ok="Close")

    def _on_about(self, sender):
        """Show about dialog"""
        about_text = """
VibeVoice v0.1.0

A voice-to-text tool using local Whisper
model with AI command support.

Built with ❤️ for macOS
        """
        rumps.alert(about_text.strip(), title="About VibeVoice", ok="Close")

    def _on_quit(self, sender):
        """Quit the application"""
        # Stop VibeVoice if running
        self._stop_event.set()

        # Update control state
        try:
            from .control_state import set_running, set_paused
            set_running(False)
            set_paused(False)
        except:
            pass

        # Call stop callback if provided
        if self._on_stop_callback:
            self._on_stop_callback()

        # Quit the app
        rumps.quit_application()

    def _update_status(self, running: bool = False, stopped: bool = False):
        """Update the menu status"""
        if running:
            self.status_menu.title = "● Status: Running"
            self.status_menu.icon = None  # rumps icon must be file path or None
            self.start_button.enabled = False
            self.stop_button.enabled = True
            self.pause_button.enabled = True
            self.pause_button.title = "⏸ Pause"
        elif stopped:
            self.status_menu.title = "○ Status: Stopped"
            self.status_menu.icon = None
            self.start_button.enabled = True
            self.stop_button.enabled = False
            self.pause_button.enabled = False
            self.pause_button.title = "⏸ Pause"

    def set_running(self, running: bool):
        """Update running status from external code"""
        import rumps
        if self.app:
            rumps.notification_unit(
                title="VibeVoice",
                subtitle="Running" if running else "Stopped",
                sound=False
            )
            self._update_status(running=running, stopped=not running)


# Global menu bar instance
_menu_bar: Optional[VibeVoiceMenuBar] = None


def get_menubar() -> Optional[VibeVoiceMenuBar]:
    """Get or create the menu bar instance"""
    global _menu_bar
    if _menu_bar is None:
        _menu_bar = VibeVoiceMenuBar()
    return _menu_bar


def start_menubar(on_stop_callback: Optional[Callable] = None):
    """Start the menu bar app (blocking call)"""
    menubar = get_menubar()
    if menubar.is_available():
        menubar.start(on_stop_callback)
    else:
        print("Menu bar not available. Running VibeVoice directly...")
        from . import cli
        cli.main()


if __name__ == "__main__":
    start_menubar()
