"""Command-line interface for vibevoice - Real-time streaming transcription on M1 Mac.

Optimized with better resource management, error handling, and memory cleanup.
"""

import os
import sys
import threading
import time
import gc
import numpy as np
from pynput.keyboard import Controller as KeyboardController, Key, Listener
from dotenv import load_dotenv

from vibevoice.audio_capture import StreamingAudioCapture
from vibevoice.transcriber import StreamingTranscriber
from vibevoice.loading_indicator import LoadingIndicator


def main():
    """Main entry point for vibevoice with real-time streaming."""
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

    # Initialize streaming audio capture with memory limit (30 seconds max)
    audio_capture = StreamingAudioCapture(
        sample_rate=16000,
        channels=1,
        max_buffer_seconds=30
    )

    recording = False
    transcription_lock = threading.Lock()
    stop_streaming = False
    transcribed_count = 0  # Track number of transcriptions for periodic cleanup

    def transcribe_phrase(audio_phrase: np.ndarray) -> str:
        """
        Transcribe a single audio phrase with error handling.

        Args:
            audio_phrase: Audio data as int16 numpy array

        Returns:
            Transcribed text or empty string on error
        """
        nonlocal transcribed_count

        try:
            audio_float32 = StreamingTranscriber.normalize_audio(audio_phrase)
            result = transcriber.transcribe(audio_float32)

            # Periodic cleanup: every 10 transcriptions, trigger GC
            transcribed_count += 1
            if transcribed_count % 10 == 0:
                gc.collect()

            return result
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""

    def stream_worker():
        """
        Background thread that processes phrases while recording.

        Memory optimizations:
        - Processes phrases from queue
        - Clears audio data immediately after transcription
        - Handles errors gracefully
        """
        nonlocal recording

        while recording:
            try:
                # Check for new phrases
                phrases = audio_capture.get_pending_phrases()

                for phrase in phrases:
                    if len(phrase) > 1000:  # Only transcribe if > ~60ms of audio
                        # Transcribe in background
                        result = transcribe_phrase(phrase)

                        if result:
                            # Type the text immediately
                            print(f"[STREAM] {result}")
                            try:
                                keyboard_controller.type(result + " ")
                            except Exception as e:
                                print(f"Error typing text: {e}")

                    # Explicitly delete phrase to free memory
                    del phrase

                # Sleep briefly to avoid busy-waiting
                time.sleep(0.05)

            except Exception as e:
                print(f"Error in stream worker: {e}")
                time.sleep(0.1)  # Brief pause on error

    streaming_thread = None

    def on_press(key):
        """Handle key press events."""
        nonlocal recording, streaming_thread, stop_streaming

        if key == RECORD_KEY and not recording:
            recording = True
            stop_streaming = False
            transcribed_count = 0  # Reset counter on new recording
            audio_capture.start_recording()
            print("Listening... (text will appear as you speak)")

            # Start streaming worker thread
            streaming_thread = threading.Thread(
                target=stream_worker,
                daemon=True,
                name="StreamingWorker"
            )
            streaming_thread.start()

    def on_release(key):
        """
        Handle key release events with proper cleanup.

        Ensures all resources are freed and final transcription is processed.
        """
        nonlocal recording, stop_streaming, streaming_thread

        if key == RECORD_KEY and recording:
            recording = False
            stop_streaming = True
            print("Finalizing...")

            # Wait for streaming thread to finish (with timeout)
            if streaming_thread and streaming_thread.is_alive():
                streaming_thread.join(timeout=2.0)
                if streaming_thread.is_alive():
                    print("Warning: Streaming thread did not finish in time")

            # Get any remaining audio and transcribe
            try:
                remaining_audio = audio_capture.stop_recording()

                if len(remaining_audio) > 1000:
                    loading_indicator.show(message="Final transcription...")

                    try:
                        result = transcribe_phrase(remaining_audio)

                        if result:
                            # Check if this was already transcribed
                            print(f"[FINAL] {result}")
                            keyboard_controller.type(result + " ")

                    except Exception as e:
                        print(f"Error in final transcription: {e}")

                    finally:
                        loading_indicator.hide()

                # Clear the phrase queue to free memory
                audio_capture.clear_queue()

            except Exception as e:
                print(f"Error stopping recording: {e}")

            # Force garbage collection after recording completes
            gc.collect()

    # Create audio stream with callback
    audio_stream = None
    try:
        audio_stream = audio_capture.create_stream(
            callback=audio_capture.get_callback(),
            sample_rate=16000,
            channels=1
        )

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

    except Exception as e:
        print(f"Unexpected error: {e}")

    finally:
        # Comprehensive cleanup
        print("Cleaning up resources...")

        if audio_stream:
            try:
                audio_stream.close()
            except Exception as e:
                print(f"Error closing audio stream: {e}")

        # Reset transcriber to clear context
        try:
            transcriber.reset()
        except Exception as e:
            print(f"Error resetting transcriber: {e}")

        # Final garbage collection
        gc.collect()

        print("Cleanup complete.")


if __name__ == "__main__":
    main()
