"""Command-line interface for vibevoice - Real-time streaming transcription with sound feedback."""

import os
import sys

# Add parent directory to path to allow imports when run from root
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import threading
import time
import numpy as np
import sounddevice as sd
from pynput.keyboard import Controller as KeyboardController, Key, Listener
from dotenv import load_dotenv

from vibevoice.audio_capture import StreamingAudioCapture
from vibevoice.transcriber import StreamingTranscriber
from vibevoice.loading_indicator import LoadingIndicator


def play_start_sound():
    """Play a modern ascending sound when starting recording"""
    # Ascending tone: 880Hz (A5) -> 1108Hz (C#6)
    duration = 0.15
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    fade_samples = int(0.03 * sample_rate)
    envelope = np.ones_like(t)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)

    freq_start, freq_end = 880, 1108
    freqs = np.linspace(freq_start, freq_end, len(t))
    tone = np.sin(2 * np.pi * freqs * t)
    tone = tone * envelope * 0.3

    audio = (tone * 32767).astype(np.int16)
    sd.play(audio, 44100)


def play_stop_sound():
    """Play a modern descending sound when stopping recording"""
    # Descending tone: 1108Hz (C#6) -> 659Hz (E5)
    duration = 0.2
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    fade_samples = int(0.03 * sample_rate)
    envelope = np.ones_like(t)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)

    freq_start, freq_end = 1108, 659
    freqs = np.linspace(freq_start, freq_end, len(t))
    tone = np.sin(2 * np.pi * freqs * t)
    tone = tone * envelope * 0.25

    audio = (tone * 32767).astype(np.int16)
    sd.play(audio, 44100)


def main():
    """Main entry point for vibevoice with real-time streaming and sound feedback."""
    load_dotenv()

    # Configuration from environment variables
    key_label = os.environ.get("VOICEKEY", "cmd_r")
    model_size = os.environ.get("WHISPER_MODEL", "small")
    language = os.environ.get("WHISPER_LANGUAGE", None)

    RECORD_KEY = Key[key_label]
    keyboard_controller = KeyboardController()
    loading_indicator = LoadingIndicator()

    # Initialize MLX Whisper transcriber (M1 optimized)
    print(f"Initializing MLX Whisper (model: {model_size})...")
    transcriber = StreamingTranscriber(model_size=model_size, language=language)
    print("Model loaded successfully!")

    # Initialize streaming audio capture
    audio_capture = StreamingAudioCapture(sample_rate=16000, channels=1)

    recording = False
    transcription_lock = threading.Lock()
    stop_streaming = False

    def transcribe_phrase(audio_phrase: np.ndarray) -> str:
        """Transcribe a single audio phrase."""
        try:
            audio_float32 = StreamingTranscriber.normalize_audio(audio_phrase)
            return transcriber.transcribe(audio_float32)
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""

    def stream_worker():
        """Background thread that processes phrases while recording."""
        nonlocal recording

        while recording:
            # Check for new phrases
            phrases = audio_capture.get_pending_phrases()

            for phrase in phrases:
                if len(phrase) > 1000:  # Only transcribe if > ~60ms of audio
                    # Transcribe in background
                    result = transcribe_phrase(phrase)

                    if result:
                        # Type the text immediately
                        print(f"[STREAM] {result}")
                        keyboard_controller.type(result + " ")

            # Sleep briefly to avoid busy-waiting
            time.sleep(0.05)

    streaming_thread = None

    def on_press(key):
        """Handle key press events."""
        nonlocal recording, streaming_thread, stop_streaming

        if key == RECORD_KEY and not recording:
            recording = True
            stop_streaming = False
            audio_capture.start_recording()
            print("Listening... (text will appear as you speak)")

            # Play start sound
            play_start_sound()

            # Start streaming worker thread
            streaming_thread = threading.Thread(target=stream_worker, daemon=True)
            streaming_thread.start()

    def on_release(key):
        """Handle key release events."""
        nonlocal recording, stop_streaming, streaming_thread

        if key == RECORD_KEY and recording:
            recording = False
            stop_streaming = True
            print("Finalizing...")

            # Play stop sound
            play_stop_sound()

            # Wait for streaming thread to finish
            if streaming_thread:
                streaming_thread.join(timeout=1.0)

            # Get any remaining audio and transcribe
            remaining_audio = audio_capture.stop_recording()

            if len(remaining_audio) > 1000:
                loading_indicator.show(message="Final transcription...")

                result = transcribe_phrase(remaining_audio)

                loading_indicator.hide()

                if result:
                    # Check if this was already transcribed
                    print(f"[FINAL] {result}")
                    keyboard_controller.type(result + " ")

    # Create audio stream with callback
    audio_stream = audio_capture.create_stream(
        callback=audio_capture.get_callback(),
        sample_rate=16000,
        channels=1
    )

    try:
        print(f"vibevoice is ready for real-time streaming!")
        print(f"Model: {model_size} | Hold {key_label} to speak")
        print("Press Ctrl+C to quit.")
        print("-" * 50)

        # Start keyboard listener and audio stream
        with Listener(on_press=on_press, on_release=on_release) as listener:
            with audio_stream:
                listener.join()

    except KeyboardInterrupt:
        print("\nStopping vibevoice...")
    finally:
        if audio_stream:
            audio_stream.close()


if __name__ == "__main__":
    main()
