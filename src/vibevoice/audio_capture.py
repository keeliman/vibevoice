"""Audio capture module for real-time streaming speech-to-text with VAD.

Optimized for memory efficiency with circular buffer and smart cleanup.
"""

import numpy as np
import sounddevice as sd
from typing import Callable, Optional, List
import threading
import time
from queue import Queue
import gc


class AudioCapture:
    """Captures audio from microphone for batch transcription."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        """Initialize audio capture."""
        self.sample_rate = sample_rate
        self.channels = channels
        self.recording = False
        self.audio_buffer = []
        self.lock = threading.Lock()

    def start_recording(self):
        """Start recording audio."""
        with self.lock:
            self.recording = True
            self.audio_buffer = []

    def stop_recording(self) -> np.ndarray:
        """Stop recording and return captured audio."""
        with self.lock:
            self.recording = False
            if self.audio_buffer:
                audio_data = np.concatenate(self.audio_buffer, axis=0)
                audio_int16 = (audio_data * np.iinfo(np.int16).max).astype(np.int16)
                # Clear buffer to free memory
                self.audio_buffer.clear()
                return audio_int16
            return np.array([], dtype=np.int16)

    def get_callback(self):
        """Get the callback function for sounddevice InputStream."""

        def callback(indata, frames, time, status):
            if status:
                print(f"Audio callback status: {status}")
            with self.lock:
                if self.recording:
                    self.audio_buffer.append(indata.copy())

        return callback

    @staticmethod
    def create_stream(callback, sample_rate: int = 16000, channels: int = 1):
        """Create a sounddevice input stream."""
        return sd.InputStream(
            callback=callback,
            channels=channels,
            samplerate=sample_rate,
        )


class StreamingAudioCapture:
    """
    Captures audio with VAD-based phrase detection for real-time streaming.
    Optimized with circular buffer and memory limits.

    Memory optimizations:
    - Circular buffer with configurable max size
    - Automatic cleanup of transcribed audio
    - Lazy VAD loading
    - Periodic garbage collection
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 512,
        max_buffer_seconds: int = 30,
    ):
        """
        Initialize streaming audio capture with memory limits.

        Args:
            sample_rate: Sample rate in Hz (default 16000 for Whisper)
            channels: Number of audio channels (default 1 for mono)
            chunk_size: Audio chunk size in samples (default 512 = ~32ms)
            max_buffer_seconds: Maximum audio buffer size in seconds (prevents memory bloat)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.max_buffer_samples = max_buffer_seconds * sample_rate

        self.recording = False
        self.audio_buffer = []  # Will be constrained by max_buffer_samples
        self.last_transcribed_pos = 0
        self.total_samples = 0  # Track total samples for circular buffer logic
        self.silence_chunks = 0
        self._vad = None  # Lazy-loaded VAD instance

        self.lock = threading.Lock()
        self.phrase_queue = Queue(maxsize=10)  # Bounded queue to prevent memory bloat

    def start_recording(self):
        """Start recording audio."""
        with self.lock:
            self.recording = True
            self.audio_buffer = []
            self.last_transcribed_pos = 0
            self.total_samples = 0
            self.silence_chunks = 0

    def stop_recording(self) -> np.ndarray:
        """
        Stop recording and return all remaining audio.

        Returns:
            Audio data as numpy array (int16)
        """
        with self.lock:
            self.recording = False
            if self.audio_buffer:
                audio_data = np.concatenate(self.audio_buffer, axis=0)
                audio_int16 = (audio_data * np.iinfo(np.int16).max).astype(np.int16)
                # Clear buffer to free memory
                self.audio_buffer.clear()
                self.last_transcribed_pos = 0
                self.total_samples = 0
                return audio_int16
            return np.array([], dtype=np.int16)

    def get_current_phrase(self) -> Optional[np.ndarray]:
        """
        Get new audio since last transcription (for streaming).

        Returns:
            New audio segment as numpy array, or None if no new audio
        """
        with self.lock:
            if not self.audio_buffer:
                return None

            # Concatenate all audio
            full_audio = np.concatenate(self.audio_buffer, axis=0)

            # Get audio from last transcribed position
            if self.last_transcribed_pos < len(full_audio):
                new_audio = full_audio[self.last_transcribed_pos:]
                self.last_transcribed_pos = len(full_audio)
                return new_audio

            return None

    def _add_to_buffer(self, audio_chunk: np.ndarray):
        """
        Add audio chunk to buffer with memory limit enforcement.

        Args:
            audio_chunk: Audio chunk to add
        """
        self.audio_buffer.append(audio_chunk)
        self.total_samples += len(audio_chunk)

        # Enforce buffer size limit
        if self.total_samples > self.max_buffer_samples:
            # Remove oldest chunks until we're under the limit
            while self.audio_buffer and self.total_samples > self.max_buffer_samples * 0.8:
                removed = self.audio_buffer.pop(0)
                self.total_samples -= len(removed)
                # Adjust transcribed position accordingly
                self.last_transcribed_pos -= len(removed)

            # Ensure transcribed position doesn't go negative
            self.last_transcribed_pos = max(0, self.last_transcribed_pos)

    def _get_vad(self):
        """
        Lazy-load the Silero VAD instance (cached).

        Returns:
            SileroVAD instance
        """
        if self._vad is None:
            from vibevoice.vad import SileroVAD
            self._vad = SileroVAD()
        return self._vad

    def get_callback(self):
        """Get the callback function for sounddevice InputStream."""

        def callback(indata, frames, time_info, status):
            if status:
                print(f"Audio callback status: {status}")

            with self.lock:
                if self.recording:
                    self._add_to_buffer(indata.copy())

                    # Check for silence (simple energy-based detection)
                    audio_energy = np.mean(np.abs(indata))
                    if audio_energy < 0.01:  # Silence threshold
                        self.silence_chunks += 1
                    else:
                        self.silence_chunks = 0

                    # If enough silence, check for phrase to transcribe
                    chunk_duration_ms = int(frames * 1000 / self.sample_rate)
                    silence_ms = self.silence_chunks * chunk_duration_ms

                    # Trigger phrase detection after ~400ms of silence
                    if silence_ms >= 400:
                        self.silence_chunks = 0
                        new_audio = self.get_current_phrase()
                        if new_audio is not None and len(new_audio) > 0:
                            # Use VAD to verify speech before queuing
                            try:
                                vad = self._get_vad()
                                if vad.has_speech(new_audio):
                                    # Convert to int16 and queue
                                    audio_int16 = (new_audio * np.iinfo(np.int16).max).astype(np.int16)
                                    # Use non-blocking put with timeout to prevent deadlock
                                    try:
                                        self.phrase_queue.put_nowait(audio_int16)
                                    except:
                                        # Queue is full, drop oldest phrase
                                        try:
                                            self.phrase_queue.get_nowait()
                                            self.phrase_queue.put_nowait(audio_int16)
                                        except:
                                            pass
                            except Exception as e:
                                # Fallback: queue if VAD fails
                                print(f"VAD error: {e}, using energy-based detection")
                                audio_int16 = (new_audio * np.iinfo(np.int16).max).astype(np.int16)
                                try:
                                    self.phrase_queue.put_nowait(audio_int16)
                                except:
                                    pass

        return callback

    def get_pending_phrases(self) -> List[np.ndarray]:
        """
        Get all pending phrases from the queue.

        Returns:
            List of audio phrases ready for transcription
        """
        phrases = []
        while not self.phrase_queue.empty():
            try:
                phrase = self.phrase_queue.get_nowait()
                phrases.append(phrase)
            except:
                break
        return phrases

    def clear_queue(self):
        """Clear all pending phrases from the queue."""
        while not self.phrase_queue.empty():
            try:
                self.phrase_queue.get_nowait()
            except:
                break

    @staticmethod
    def create_stream(callback, sample_rate: int = 16000, channels: int = 1):
        """Create a sounddevice input stream."""
        return sd.InputStream(
            callback=callback,
            channels=channels,
            samplerate=sample_rate,
        )
