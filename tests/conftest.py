"""Pytest configuration and fixtures for vibevoice tests."""

import sys
import os
import pytest
import numpy as np

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture
def sample_audio_int16():
    """Generate sample audio data in int16 format."""
    # Generate 1 second of silence at 16kHz
    samples = 16000
    audio = np.zeros(samples, dtype=np.int16)
    return audio


@pytest.fixture
def sample_audio_float32():
    """Generate sample audio data in float32 format."""
    # Generate 1 second of silence at 16kHz
    samples = 16000
    audio = np.zeros(samples, dtype=np.float32)
    return audio


@pytest.fixture
def sample_tone():
    """Generate a 440Hz tone (A4) for testing."""
    sample_rate = 16000
    duration = 0.5  # 500ms
    frequency = 440  # A4 note

    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    tone = np.sin(2 * np.pi * frequency * t)

    # Convert to int16
    tone_int16 = (tone * 32767 * 0.5).astype(np.int16)
    return tone_int16


@pytest.fixture
def sample_speech_like():
    """Generate speech-like audio (noise bursts)."""
    sample_rate = 16000
    duration = 1.0  # 1 second

    # Create noise bursts to simulate speech
    audio = np.random.randn(int(sample_rate * duration)) * 0.1

    # Add some "speech" bursts
    burst_indices = [
        (1000, 3000),
        (5000, 7000),
        (9000, 12000)
    ]

    for start, end in burst_indices:
        audio[start:end] += np.random.randn(end - start) * 0.3

    # Normalize and convert to int16
    audio = np.clip(audio, -1, 1)
    audio_int16 = (audio * 32767).astype(np.int16)

    return audio_int16
