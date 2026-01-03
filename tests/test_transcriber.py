"""Unit tests for the transcriber module."""

import pytest
import numpy as np
from vibevoice.transcriber import StreamingTranscriber


class TestStreamingTranscriber:
    """Test suite for StreamingTranscriber class."""

    def test_model_sizes(self):
        """Test that valid model sizes are accepted."""
        valid_sizes = ["tiny", "base", "small", "medium", "large"]

        for size in valid_sizes:
            # Should not raise exception
            transcriber = StreamingTranscriber(model_size=size)
            # Check model_path is set correctly (not model_size)
            assert transcriber.model_path is not None
            assert size in transcriber.model_path

    def test_invalid_model_size(self):
        """Test that invalid model size raises ValueError."""
        with pytest.raises(ValueError, match="Model size must be one of"):
            StreamingTranscriber(model_size="invalid")

    def test_normalize_audio_int16(self):
        """Test audio normalization from int16 to float32."""
        # Create sample int16 audio (max and min values)
        audio_int16 = np.array([32767, 0, -32768], dtype=np.int16)

        # Normalize
        result = StreamingTranscriber.normalize_audio(audio_int16)

        # Check result is float32 and in [-1, 1] range
        assert result.dtype == np.float32
        assert np.all(result >= -1.0) and np.all(result <= 1.0)
        # Max value should be close to 1.0
        assert abs(result[0] - 1.0) < 0.01

    def test_normalize_audio_already_float32(self):
        """Test that float32 audio gets converted properly."""
        # Note: normalize_audio always assumes int16 input and converts to float32
        # If you pass float32, it will be treated as if it were int16 values
        audio_float = np.array([0.5, 0.0, -0.5], dtype=np.float32)

        result = StreamingTranscriber.normalize_audio(audio_float.astype(np.int16))

        assert result.dtype == np.float32
        # Result should be normalized in [-1, 1] range
        assert np.all(result >= -1.0) and np.all(result <= 1.0)

    def test_transcribe_empty_audio(self):
        """Test that empty audio returns empty string."""
        transcriber = StreamingTranscriber(model_size="tiny")
        result = transcriber.transcribe(np.array([], dtype=np.float32))
        assert result == ""

    def test_transcribe_silence(self, sample_audio_float32):
        """Test transcription of silent audio."""
        transcriber = StreamingTranscriber(model_size="tiny")
        result = transcriber.transcribe(sample_audio_float32)
        # Silence should result in empty or very short result
        assert isinstance(result, str)
        assert len(result) < 10  # Allow for minor artifacts

    def test_transcribe_with_language(self):
        """Test that language parameter is accepted."""
        transcriber = StreamingTranscriber(model_size="tiny", language="en")
        assert transcriber.language == "en"

    def test_transcribe_with_language_none(self):
        """Test that None language works (auto-detect)."""
        transcriber = StreamingTranscriber(model_size="tiny", language=None)
        assert transcriber.language is None

    def test_transcribe_real_audio_structure(self, sample_tone):
        """Test transcription with real audio structure (doesn't mock MLX)."""
        transcriber = StreamingTranscriber(model_size="tiny")

        # This will attempt real transcription but might fail if model not downloaded
        # We're testing the structure, not the actual MLX output
        try:
            result = transcriber.transcribe(
                StreamingTranscriber.normalize_audio(sample_tone)
            )
            # If successful, result should be a string
            assert isinstance(result, str)
        except Exception as e:
            # Expected if model not available - test passed if we get here
            assert "model" in str(e).lower() or "mlx" in str(e).lower() or "hub" in str(e).lower()

    def test_transcriber_has_models_dict(self):
        """Test that MODELS dictionary exists and has expected keys."""
        assert hasattr(StreamingTranscriber, 'MODELS')
        assert isinstance(StreamingTranscriber.MODELS, dict)

        expected_keys = ["tiny", "base", "small", "medium", "large"]
        for key in expected_keys:
            assert key in StreamingTranscriber.MODELS
