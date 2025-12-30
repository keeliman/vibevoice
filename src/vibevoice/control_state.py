"""Shared control state for VibeVoice - allows menubar to control CLI"""

import threading
from typing import Callable, Optional

class ControlState:
    """Shared state for controlling VibeVoice from menubar"""

    def __init__(self):
        self._paused = False
        self._running = False
        self._lock = threading.Lock()
        self._pause_callbacks: list[Callable] = []
        self._resume_callbacks: list[Callable] = []

    @property
    def paused(self) -> bool:
        """Check if VibeVoice is paused"""
        with self._lock:
            return self._paused

    @paused.setter
    def paused(self, value: bool):
        """Set pause state and trigger callbacks"""
        with self._lock:
            old_value = self._paused
            self._paused = value
            if value and not old_value:
                # Just paused
                for callback in self._pause_callbacks:
                    try:
                        callback()
                    except Exception:
                        pass
            elif not value and old_value:
                # Just resumed
                for callback in self._resume_callbacks:
                    try:
                        callback()
                    except Exception:
                        pass

    @property
    def running(self) -> bool:
        """Check if VibeVoice is running"""
        with self._lock:
            return self._running

    @running.setter
    def running(self, value: bool):
        """Set running state"""
        with self._lock:
            self._running = value

    def toggle_pause(self) -> bool:
        """Toggle pause state, returns new state (True=paused)"""
        with self._lock:
            self.paused = not self._paused
            return self._paused

    def register_pause_callback(self, callback: Callable):
        """Register callback to be called when paused"""
        with self._lock:
            self._pause_callbacks.append(callback)

    def register_resume_callback(self, callback: Callable):
        """Register callback to be called when resumed"""
        with self._lock:
            self._resume_callbacks.append(callback)


# Global instance
_control_state: Optional[ControlState] = None
_state_lock = threading.Lock()


def get_control_state() -> ControlState:
    """Get or create the global control state instance"""
    global _control_state
    with _state_lock:
        if _control_state is None:
            _control_state = ControlState()
        return _control_state


def is_paused() -> bool:
    """Convenience function to check if paused"""
    return get_control_state().paused


def is_running() -> bool:
    """Convenience function to check if running"""
    return get_control_state().running


def set_paused(value: bool):
    """Convenience function to set paused state"""
    get_control_state().paused = value


def set_running(value: bool):
    """Convenience function to set running state"""
    get_control_state().running = value


def toggle_pause() -> bool:
    """Convenience function to toggle pause, returns new state"""
    return get_control_state().toggle_pause()
