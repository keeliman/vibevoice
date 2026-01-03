"""Streaming transcriber using MLX Whisper for M1 Mac optimization."""

import mlx_whisper
import numpy as np
import os
from typing import Dict, Optional


class StreamingTranscriber:
    """Real-time speech transcription using MLX Whisper."""

    # Available models: tiny, base, small, medium, large
    MODELS = {
        "tiny": "mlx-community/whisper-tiny",
        "base": "mlx-community/whisper-base",
        "small": "mlx-community/whisper-small",
        "medium": "mlx-community/whisper-medium",
        "large": "mlx-community/whisper-large-v3",
    }

    def __init__(self, model_size: str = "small", language: Optional[str] = None):
        """
        Initialize the transcriber.

        Args:
            model_size: Model size (tiny, base, small, medium, large)
            language: Language code (e.g., 'en', 'fr'). None for auto-detect.
        """
        if model_size not in self.MODELS:
            raise ValueError(f"Model size must be one of: {list(self.MODELS.keys())}")

        self.model_path = self.MODELS[model_size]
        self.language = language
        print(f"Loading MLX Whisper model: {model_size}")

    def transcribe(self, audio_data: np.ndarray) -> str:
        """
        Transcribe audio data to text.

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

        # Transcribe using MLX Whisper
        result = mlx_whisper.transcribe(
            audio_data,
            path_or_hf_repo=self.model_path,
            language=self.language,
        )

        return result.get("text", "").strip()

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
