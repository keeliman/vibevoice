"""Streaming transcriber using MLX Whisper for M1 Mac optimization.

Optimized for memory efficiency and low-latency real-time transcription.
"""

import mlx_whisper
import numpy as np
import os
import gc
from typing import Dict, Optional, Tuple


class StreamingTranscriber:
    """Real-time speech transcription using MLX Whisper with memory optimization."""

    # Available models: tiny, base, small, medium, large
    MODELS = {
        "tiny": "mlx-community/whisper-tiny",
        "base": "mlx-community/whisper-base",
        "small": "mlx-community/whisper-small",
        "medium": "mlx-community/whisper-medium",
        "large": "mlx-community/whisper-large-v3",
    }

    # Model memory requirements (approximate, in MB)
    MODEL_MEMORY = {
        "tiny": 40,
        "base": 80,
        "small": 250,
        "medium": 800,
        "large": 1600,
    }

    def __init__(
        self,
        model_size: str = "small",
        language: Optional[str] = None,
        max_context_chunks: int = 3,
    ):
        """
        Initialize the transcriber with memory optimization.

        Args:
            model_size: Model size (tiny, base, small, medium, large)
            language: Language code (e.g., 'en', 'fr'). None for auto-detect.
            max_context_chunks: Maximum number of previous audio chunks to keep as context
                               (helps with continuity but uses more memory)
        """
        if model_size not in self.MODELS:
            raise ValueError(f"Model size must be one of: {list(self.MODELS.keys())}")

        self.model_size = model_size
        self.model_path = self.MODELS[model_size]
        self.language = language
        self.max_context_chunks = max_context_chunks

        # Context buffer for better transcription continuity
        self._context_buffer: list[np.ndarray] = []
        self._context_samples = 0

        print(f"Loading MLX Whisper model: {model_size}")
        print(f"Estimated memory usage: ~{self.MODEL_MEMORY[model_size]}MB")

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio data to text with memory optimization.

        Args:
            audio_data: Audio data as numpy array (float32, normalized to [-1, 1])

        Returns:
            Transcribed text
        """
        if len(audio_data) == 0:
            return ""

        # Ensure audio data is float32 and normalized
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        # Add context from previous chunks for better continuity
        audio_to_transcribe = self._prepare_audio_with_context(audio_data)

        try:
            # Transcribe using MLX Whisper
            result = mlx_whisper.transcribe(
                audio_to_transcribe,
                path_or_hf_repo=self.model_path,
                language=self.language,
            )

            text = result.get("text", "").strip()

            # Update context buffer with new audio
            self._update_context(audio_data)

            return text

        except Exception as e:
            print(f"Transcription error: {e}")
            # Clear context on error to prevent memory buildup
            self._clear_context()
            return ""

        finally:
            # Explicitly clean up large arrays
            if 'audio_to_transcribe' in locals():
                del audio_to_transcribe
            gc.collect()

    def _prepare_audio_with_context(self, new_audio: np.ndarray) -> np.ndarray:
        """
        Prepare audio with context from previous chunks for better continuity.

        Args:
            new_audio: New audio segment to transcribe

        Returns:
            Audio with context prepended (if available)
        """
        if not self._context_buffer:
            return new_audio

        # Concatenate context with new audio
        context_audio = np.concatenate(self._context_buffer + [new_audio])
        return context_audio

    def _update_context(self, new_audio: np.ndarray):
        """
        Update rolling context buffer with new audio.

        Keeps only the most recent chunks to limit memory usage.

        Args:
            new_audio: New audio segment to add to context
        """
        # Add new audio to context
        self._context_buffer.append(new_audio)
        self._context_samples += len(new_audio)

        # Limit context size to prevent memory bloat
        # Keep approximately last 3 seconds of context (at 16kHz)
        max_context_samples = 3 * 16000

        while self._context_samples > max_context_samples and self._context_buffer:
            removed = self._context_buffer.pop(0)
            self._context_samples -= len(removed)

    def _clear_context(self):
        """Clear the context buffer to free memory."""
        self._context_buffer.clear()
        self._context_samples = 0
        gc.collect()

    def reset(self):
        """Reset transcriber state (clears context)."""
        self._clear_context()

    @staticmethod
    def normalize_audio(audio_int16: np.ndarray) -> np.ndarray:
        """
        Convert int16 audio to normalized float32.

        Args:
            audio_int16: Audio data as int16

        Returns:
            Normalized float32 audio in range [-1, 1]
        """
        return audio_int16.astype(np.float32) / 32768.0

    @staticmethod
    def denormalize_audio(audio_float32: np.ndarray) -> np.ndarray:
        """
        Convert normalized float32 audio to int16.

        Args:
            audio_float32: Normalized audio data in range [-1, 1]

        Returns:
            Audio data as int16
        """
        clipped = np.clip(audio_float32, -1.0, 1.0)
        return (clipped * 32767).astype(np.int16)
