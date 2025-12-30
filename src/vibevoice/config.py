"""Configuration constants for VibeVoice"""

import os

# === Power Management ===
# Server idle timeout before shutdown (seconds)
# Set to 0 to disable auto-shutdown
SERVER_IDLE_TIMEOUT = int(os.getenv('VIBEVOICE_IDLE_TIMEOUT', '300'))  # 5 minutes default

# Use lazy loading for Whisper model (load on first use)
LAZY_LOAD_MODEL = os.getenv('VIBEVOICE_LAZY_LOAD', 'true').lower() == 'true'

# Power saving mode (reduces CPU usage when idle)
POWER_SAVING_MODE = os.getenv('VIBEVOICE_POWER_SAVE', 'true').lower() == 'true'

# Whisper model size (tiny/base/small/medium/large)
# Smaller models = less battery but less accuracy
WHISPER_MODEL_SIZE = os.getenv('WHISPER_MODEL', 'base')  # 'base' is good balance

# === Server port configuration ===
DEFAULT_SERVER_PORT = 4242
MAX_PORT_ATTEMPTS = 10
FALLBACK_PORTS_START = 4242
FALLBACK_PORTS_END = 4252

# List of all ports used by VibeVoice (for cleanup scripts)
ALL_PORTS = list(range(FALLBACK_PORTS_START, FALLBACK_PORTS_END))

# Server configuration
SERVER_HOST = "127.0.0.1"
HEALTH_CHECK_TIMEOUT = 30
HEALTH_CHECK_INTERVAL = 0.5

# Ollama configuration
OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_DEFAULT_MODEL = "gemma3:27b"

# Request timeouts
REQUEST_TIMEOUT_TEXT = 30
REQUEST_TIMEOUT_SCREENSHOT = 60

# Audio configuration
SAMPLE_RATE = 16000

# File size limits
MAX_SCREENSHOT_SIZE_RAW = 50 * 1024 * 1024  # 50MB
MAX_SCREENSHOT_SIZE_PROCESSED = 20 * 1024 * 1024  # 20MB
MAX_TRANSCRIPT_LENGTH = 1000
MAX_AI_RESPONSE_SIZE = 10 * 1024  # 10KB
MAX_AI_CHUNK_SIZE = 500

# Screenshot configuration
SCREENSHOT_MIN_WIDTH = 100
SCREENSHOT_MAX_WIDTH = 4096
SCREENSHOT_MAX_HEIGHT = 4096
SCREENSHOT_DEFAULT_MAX_WIDTH = 1024
SCREENSHOT_TIMEOUT = 5

# Screenshot base64 size limit
MAX_SCREENSHOT_BASE64_SIZE = 50 * 1024 * 1024  # 50MB
