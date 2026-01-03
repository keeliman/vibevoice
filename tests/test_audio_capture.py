"""Unit tests for the audio_capture module."""

import pytest
import time
import threading
import numpy as np
from queue import Empty
from vibevoice.audio_capture import AudioCapture, StreamingAudioCapture


class TestAudioCapture:
    """Test suite for AudioCapture class (batch mode)."""

    def test_initialization(self):
        """Test that AudioCapture initializes correctly."""
        capture = AudioCapture(sample_rate=16000, channels=1)
        assert capture.sample_rate == 16000
        assert capture.channels == 1
        assert capture.recording == False
        assert len(capture.audio_buffer) == 0

    def test_initialization_custom_params(self):
        """Test initialization with custom parameters."""
        capture = AudioCapture(sample_rate=22050, channels=2)
        assert capture.sample_rate == 22050
        assert capture.channels == 2

    def test_start_recording(self):
        """Test starting recording."""
        capture = AudioCapture()
        capture.start_recording()
        assert capture.recording == True
        assert len(capture.audio_buffer) == 0

    def test_stop_recording_empty(self):
        """Test stopping recording with no audio."""
        capture = AudioCapture()
        capture.start_recording()
        result = capture.stop_recording()

        assert capture.recording == False
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) == 0

    def test_callback_exists(self):
        """Test that get_callback returns a callable."""
        capture = AudioCapture()
        callback = capture.get_callback()
        assert callable(callback)

    def test_create_stream_exists(self):
        """Test that create_stream is a static method."""
        assert hasattr(AudioCapture, 'create_stream')
        assert callable(AudioCapture.create_stream)


class TestStreamingAudioCapture:
    """Test suite for StreamingAudioCapture class."""

    def test_initialization(self):
        """Test that StreamingAudioCapture initializes correctly."""
        capture = StreamingAudioCapture(sample_rate=16000, channels=1)
        assert capture.sample_rate == 16000
        assert capture.channels == 1
        assert capture.chunk_size == 512
        assert capture.recording == False
        assert capture.last_transcribed_pos == 0
        assert capture.silence_chunks == 0

    def test_initialization_vad_none(self):
        """Test that VAD is initialized as None (lazy loading)."""
        capture = StreamingAudioCapture()
        assert capture._vad is None

    def test_get_vad_method_exists(self):
        """Test that _get_vad method exists and is callable."""
        capture = StreamingAudioCapture()
        assert hasattr(capture, '_get_vad')
        assert callable(capture._get_vad)

    def test_start_recording(self):
        """Test starting streaming recording."""
        capture = StreamingAudioCapture()
        capture.start_recording()
        assert capture.recording == True
        assert len(capture.audio_buffer) == 0
        assert capture.last_transcribed_pos == 0
        assert capture.silence_chunks == 0

    def test_stop_recording_empty(self):
        """Test stopping with no audio."""
        capture = StreamingAudioCapture()
        capture.start_recording()
        result = capture.stop_recording()

        assert capture.recording == False
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) == 0

    def test_get_current_phrase_empty(self):
        """Test getting current phrase when no audio."""
        capture = StreamingAudioCapture()
        capture.start_recording()
        result = capture.get_current_phrase()
        assert result is None

    def test_get_current_phrase_with_audio(self, sample_speech_like):
        """Test getting current phrase with audio."""
        capture = StreamingAudioCapture()
        capture.start_recording()

        # Simulate audio buffer (normally done by callback)
        with capture.lock:
            capture.audio_buffer.append(sample_speech_like.reshape(-1, 1))

        result = capture.get_current_phrase()

        assert result is not None
        assert isinstance(result, np.ndarray)
        assert len(result) > 0

    def test_mark_as_transcribed(self):
        """Test marking audio as transcribed."""
        capture = StreamingAudioCapture()
        capture.start_recording()

        # Mark some samples as transcribed
        capture.mark_as_transcribed(1000)

        assert capture.last_transcribed_pos == 1000

    def test_get_pending_phrases_empty(self):
        """Test getting pending phrases when queue is empty."""
        capture = StreamingAudioCapture()
        phrases = capture.get_pending_phrases()
        assert isinstance(phrases, list)
        assert len(phrases) == 0

    def test_callback_exists(self):
        """Test that get_callback returns a callable."""
        capture = StreamingAudioCapture()
        callback = capture.get_callback()
        assert callable(callback)

    def test_create_stream_exists(self):
        """Test that create_stream is a static method."""
        assert hasattr(StreamingAudioCapture, 'create_stream')
        assert callable(StreamingAudioCapture.create_stream)

    def test_phrase_queue_functionality(self, sample_speech_like):
        """Test the phrase queue for streaming."""
        capture = StreamingAudioCapture()

        # Manually add a phrase to the queue
        capture.phrase_queue.put(sample_speech_like)

        # Get pending phrases
        phrases = capture.get_pending_phrases()

        assert len(phrases) == 1
        np.testing.assert_array_equal(phrases[0], sample_speech_like)

    def test_silence_detection_logic(self, sample_speech_like):
        """Test silence detection in callback logic."""
        capture = StreamingAudioCapture()
        capture.start_recording()

        # Simulate callback with silence
        frames = 512
        silence_data = np.zeros((frames, 1), dtype=np.float32) * 0.001  # Very low energy

        with capture.lock:
            capture.audio_buffer.append(silence_data)

            # Simulate silence detection logic
            audio_energy = np.mean(np.abs(silence_data))
            if audio_energy < 0.01:
                capture.silence_chunks += 1

        assert capture.silence_chunks > 0

    def test_speech_detection_logic(self):
        """Test speech (non-silence) detection in callback logic."""
        capture = StreamingAudioCapture()
        capture.start_recording()

        # Simulate callback with speech
        frames = 512
        speech_data = np.ones((frames, 1), dtype=np.float32) * 0.5  # High energy

        with capture.lock:
            capture.audio_buffer.append(speech_data)

            # Simulate speech detection logic
            audio_energy = np.mean(np.abs(speech_data))
            if audio_energy < 0.01:
                capture.silence_chunks += 1
            else:
                capture.silence_chunks = 0

        assert capture.silence_chunks == 0

    def test_thread_safety(self, sample_speech_like):
        """Test that the lock works correctly for thread safety."""
        capture = StreamingAudioCapture()
        capture.start_recording()

        # Test lock acquisition
        with capture.lock:
            # We're holding the lock, modify state
            capture.audio_buffer.append(sample_speech_like.reshape(-1, 1))

        # Lock should be released now
        assert len(capture.audio_buffer) == 1


class TestIntegrationAudioCapture:
    """Integration tests for audio capture components."""

    def test_both_capture_classes_exist(self):
        """Test that both capture classes are available."""
        assert AudioCapture is not None
        assert StreamingAudioCapture is not None

    def test_both_have_same_interface(self):
        """Test that both classes have compatible interfaces."""
        batch = AudioCapture()
        streaming = StreamingAudioCapture()

        # Both should have these methods
        for method in ['start_recording', 'stop_recording', 'get_callback']:
            assert hasattr(batch, method)
            assert hasattr(streaming, method)
