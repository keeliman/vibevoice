"""Enhanced notification system for VibeVoice using modern libraries"""

import os
import asyncio
import platform
from typing import Optional, Literal

# Sound notifications
try:
    import chime
    CHIME_AVAILABLE = True
except ImportError:
    CHIME_AVAILABLE = False
    print("Chime not available. Install with: pip install chime")

# Visual notifications
# Disabled on macOS due to permission issues blocking startup
import sys
if sys.platform == "darwin":
    DESKTOP_NOTIFIER_AVAILABLE = False
    DesktopNotifier = None
else:
    try:
        from desktop_notifier import DesktopNotifier
        DESKTOP_NOTIFIER_AVAILABLE = True
    except ImportError:
        DESKTOP_NOTIFIER_AVAILABLE = False
        print("Desktop notifier not available. Install with: pip install desktop-notifier")

class NotificationManager:
    """Elegant notification manager combining sound and visual notifications"""

    def __init__(self):
        self.sound_enabled = CHIME_AVAILABLE
        self.visual_enabled = DESKTOP_NOTIFIER_AVAILABLE
        self._event_loop = None  # Cached event loop for sync notifications
        self.desktop_notifier = None

        if self.sound_enabled:
            # Set chime theme to elegant sounds (use default theme)
            pass  # chime uses default theme which is suitable

        if self.visual_enabled:
            try:
                self.desktop_notifier = DesktopNotifier(
                    app_name="VibeVoice",
                    app_icon=None  # Can be set to an icon path if needed
                )
            except Exception as e:
                # DesktopNotifier may fail due to permissions on macOS
                print(f"Desktop notifier initialization failed: {e}")
                print("Visual notifications disabled")
                self.visual_enabled = False
    
    def play_sound(self, sound_type: Literal["success", "error", "warning", "info"]):
        """Play elegant notification sound"""
        if not self.sound_enabled:
            return

        try:
            if sound_type == "success":
                chime.success()
            elif sound_type == "error":
                chime.error()
            elif sound_type == "warning":
                chime.warning()
            elif sound_type == "info":
                chime.info()
        except Exception as e:
            print(f"Sound notification error: {e}")
    
    async def show_notification(
        self,
        title: str,
        message: str,
        notification_type: Literal["success", "error", "warning", "info"] = "info",
        timeout: int = 5
    ):
        """Show visual desktop notification"""
        if not self.visual_enabled:
            print(f"[{notification_type.upper()}] {title}: {message}")
            return
            
        try:
            # Use desktop notifier send API directly
            await self.desktop_notifier.send(
                title=title,
                message=message,
                timeout=timeout
            )
        except Exception as e:
            print(f"Visual notification error: {e}")
            print(f"[{notification_type.upper()}] {title}: {message}")
    
    def show_notification_sync(
        self,
        title: str,
        message: str,
        notification_type: Literal["success", "error", "warning", "info"] = "info",
        timeout: int = 5
    ):
        """Synchronous wrapper for visual notifications (optimized with cached loop)"""
        if not self.visual_enabled:
            print(f"[{notification_type.upper()}] {title}: {message}")
            return

        try:
            # Try to use existing running loop
            try:
                loop = asyncio.get_running_loop()
                # If we're here, there's a running loop - schedule as task
                import threading
                result = [None]
                exception = [None]

                def run_in_thread():
                    try:
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            result[0] = new_loop.run_until_complete(
                                self.show_notification(title, message, notification_type, timeout)
                            )
                        finally:
                            new_loop.close()
                    except Exception as e:
                        exception[0] = e

                thread = threading.Thread(target=run_in_thread, daemon=True)
                thread.start()
                thread.join(timeout=timeout + 1)
                if exception[0]:
                    raise exception[0]
            except RuntimeError:
                # No running loop, try to get or create cached loop
                if self._event_loop is None or self._event_loop.is_closed():
                    self._event_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._event_loop)

                self._event_loop.run_until_complete(
                    self.show_notification(title, message, notification_type, timeout)
                )
        except Exception as e:
            print(f"Visual notification error: {e}")
            print(f"[{notification_type.upper()}] {title}: {message}")
    
    def notify(
        self,
        title: str,
        message: str,
        notification_type: Literal["success", "error", "warning", "info"] = "info",
        sound: bool = True,
        visual: bool = True,
        timeout: int = 5
    ):
        """Complete notification with both sound and visual components"""
        if sound:
            self.play_sound(notification_type)
        
        if visual:
            self.show_notification_sync(title, message, notification_type, timeout)
    
    # Convenience methods for common notifications
    def recording_started(self, mode: str = "dictation"):
        """Notification for recording start"""
        self.notify(
            title="VibeVoice",
            message=f"Recording started ({mode})",
            notification_type="info",
            sound=True,
            visual=False  # Visual indicator already handled by existing code
        )
    
    def recording_stopped(self):
        """Notification for recording stop"""
        self.notify(
            title="VibeVoice", 
            message="Recording stopped",
            notification_type="info",
            sound=True,
            visual=False
        )
    
    def transcription_complete(self, transcript: str):
        """Notification for successful transcription"""
        preview = transcript[:50] + "..." if len(transcript) > 50 else transcript
        self.notify(
            title="Transcription Complete",
            message=f'"{preview}"',
            notification_type="success",
            sound=True,
            visual=True,
            timeout=3
        )
    
    def ai_processing_complete(self, success: bool = True):
        """Notification for AI processing completion"""
        if success:
            self.notify(
                title="AI Command Complete",
                message="Response generated successfully",
                notification_type="success",
                sound=True,
                visual=True,
                timeout=3
            )
        else:
            self.notify(
                title="AI Command Failed",
                message="Error processing AI command",
                notification_type="error",
                sound=True,
                visual=True,
                timeout=5
            )
    
    def transcription_error(self, error_msg: str = ""):
        """Notification for transcription errors"""
        self.notify(
            title="Transcription Error",
            message=error_msg or "Failed to transcribe audio",
            notification_type="error",
            sound=True,
            visual=True,
            timeout=5
        )
    
    def server_ready(self):
        """Notification when server is ready"""
        self.notify(
            title="VibeVoice Ready",
            message="Voice recognition is active",
            notification_type="success",
            sound=True,
            visual=True,
            timeout=3
        )
    
    def server_error(self):
        """Notification for server errors"""
        self.notify(
            title="VibeVoice Error",
            message="Server connection failed",
            notification_type="error",
            sound=True,
            visual=True,
            timeout=5
        )