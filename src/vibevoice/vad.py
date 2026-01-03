"""Voice Activity Detection using Silero VAD."""

import torch
import numpy as np
import os
from typing import List, Dict, Optional
import threading


class SileroVAD:
    """
    Voice Activity Detection using Silero VAD.
    Enterprise-grade, ultra-fast (<1ms per 32ms chunk).
    """

    _model = None
    _utils = None
    _lock = threading.Lock()

    @classmethod
    def load_model(cls):
        """Load Silero VAD model (lazy loading, cached)."""
        with cls._lock:
            if cls._model is None:
                print("Loading Silero VAD model...")
                try:
                    cls._model, cls._utils = torch.hub.load(
                        repo_or_dir='snakers4/silero-vad',
                        model='silero_vad',
                        force_reload=False,
                        verbose=False
                    )
                    print("Silero VAD loaded!")
                except Exception as e:
                    print(f"Failed to load Silero VAD: {e}")
                    raise
        return cls._model, cls._utils

    def __init__(self, threshold: float = 0.5, min_silence_ms: int = 400):
        """
        Initialize VAD.

        Args:
            threshold: Speech probability threshold (0-1), default 0.5
            min_silence_ms: Minimum silence duration for phrase split (ms)
        """
        self.threshold = threshold
        self.min_silence_ms = min_silence_ms
        self.model, self.utils = self.load_model()
        self.get_speech_timestamps = self.utils[0]

    def detect_speech(self, audio: np.ndarray) -> List[Dict]:
        """
        Detect speech segments in audio.

        Args:
            audio: Audio data as numpy array (int16 or float32)

        Returns:
            List of dicts with 'start' and 'end' sample indices
        """
        if len(audio) == 0:
            return []

        # Convert to int16 for Silero VAD (expects 16kHz, int16)
        if audio.dtype != np.int16:
            audio_int16 = (audio * 32768).astype(np.int16)
        else:
            audio_int16 = audio

        # Silero VAD expects int16 tensor at 16kHz
        audio_tensor = torch.from_numpy(audio_int16)

        # Get speech timestamps
        try:
            timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.model,
                threshold=self.threshold,
                sampling_rate=16000
            )
            return timestamps
        except Exception as e:
            print(f"VAD error: {e}")
            return []

    def get_phrases(self, audio: np.ndarray) -> List[np.ndarray]:
        """
        Split audio into phrases based on VAD-detected speech segments.

        Args:
            audio: Audio data as numpy array

        Returns:
            List of audio segments (each phrase as numpy array)
        """
        timestamps = self.detect_speech(audio)

        if not timestamps:
            # No speech detected, return empty list
            return []

        phrases = []
        for ts in timestamps:
            start = ts['start']
            end = ts['end']
            phrase = audio[start:end]
            phrases.append(phrase)

        return phrases

    def has_speech(self, audio: np.ndarray) -> bool:
        """
        Quick check if audio contains speech.

        Args:
            audio: Audio data as numpy array

        Returns:
            True if speech detected, False otherwise
        """
        return len(self.detect_speech(audio)) > 0

    @staticmethod
    def ms_to_samples(ms: int, sample_rate: int = 16000) -> int:
        """Convert milliseconds to sample count."""
        return int(ms * sample_rate / 1000)

    @staticmethod
    def samples_to_ms(samples: int, sample_rate: int = 16000) -> int:
        """Convert sample count to milliseconds."""
        return int(samples * 1000 / sample_rate)
