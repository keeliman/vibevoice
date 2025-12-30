"""FastAPI server for Whisper transcription - Power optimized version"""

import os
import socket
import time
import threading
import weakref
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

try:
    from . import config
except ImportError:
    import vibevoice.config as config

app = FastAPI()

# Global model instance (lazy loaded)
_model = None
_model_lock = threading.Lock()
_last_request_time = None
_shutdown_timer = None

def get_model():
    """Lazy load the Whisper model only when needed"""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                print(f"🔧 Loading Whisper model ({config.WHISPER_MODEL_SIZE})...")
                from faster_whisper import WhisperModel
                _model = WhisperModel(
                    config.WHISPER_MODEL_SIZE,
                    device="cpu",
                    compute_type="int8"
                )
                print("✅ Model loaded")
    return _model

def record_request_time():
    """Record the time of the last request for idle detection"""
    global _last_request_time
    _last_request_time = time.time()

def start_idle_timer(timeout_seconds):
    """Start a timer to shutdown the server after idle period"""
    global _shutdown_timer

    def idle_check():
        global _last_request_time, _shutdown_timer
        while True:
            time.sleep(30)  # Check every 30 seconds
            if _last_request_time is None:
                continue

            idle_time = time.time() - _last_request_time
            if timeout_seconds > 0 and idle_time >= timeout_seconds:
                print(f"💤 Server idle for {idle_time:.0f}s, shutting down...")
                os._exit(0)  # Clean exit

    _shutdown_timer = threading.Thread(target=idle_check, daemon=True)
    _shutdown_timer.start()

# Security: Define allowed directory for file access
ALLOWED_DIR = Path.cwd().resolve()
ALLOWED_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg'}

def validate_file_path(file_path: str) -> Path:
    """Validate and sanitize file path to prevent path traversal attacks"""
    try:
        # Convert to Path object and resolve
        path = Path(file_path).resolve()

        # Security check: ensure file is within allowed directory
        if not str(path).startswith(str(ALLOWED_DIR)):
            raise ValueError("File path outside allowed directory")

        # Security check: ensure file exists
        if not path.exists():
            raise FileNotFoundError("File not found")

        # Security check: ensure it's a regular file (not directory or special file)
        if not path.is_file():
            raise ValueError("Path is not a regular file")

        # Security check: validate file extension
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension not allowed. Allowed: {ALLOWED_EXTENSIONS}")

        return path
    except Exception as e:
        raise ValueError(f"Invalid file path: {e}")

class TranscribeRequest(BaseModel):
    file_path: str

    @field_validator('file_path')
    @classmethod
    def validate_file_path_input(cls, v):
        # Basic validation - detailed validation happens in endpoint
        if not v or not isinstance(v, str):
            raise ValueError('file_path must be a non-empty string')
        if len(v) > 1000:  # Prevent extremely long paths
            raise ValueError('file_path too long')
        return v.strip()

@app.get("/health")
def health_check():
    record_request_time()
    return {"status": "ok", "model_loaded": _model is not None}

@app.post("/transcribe/")
async def transcribe(request: TranscribeRequest):
    record_request_time()
    try:
        # Security: validate file path to prevent path traversal
        safe_path = validate_file_path(request.file_path)

        # Get model (lazy loaded) and perform transcription
        model = get_model()
        segments, info = model.transcribe(str(safe_path))
        text = " ".join([segment.text.strip() for segment in segments])

        return {"text": text}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Audio file not found")
    except Exception as e:
        # Log error but don't expose internal details
        print(f"Transcription error: {e}")
        raise HTTPException(status_code=500, detail="Internal transcription error")

@app.post("/shutdown")
async def shutdown():
    """Manual shutdown endpoint"""
    print("👋 Shutdown requested via API")
    os._exit(0)

def find_available_port(start_port=None, max_attempts=None):
    """Trouve un port disponible en commençant par start_port"""
    if start_port is None:
        start_port = config.DEFAULT_SERVER_PORT
    if max_attempts is None:
        max_attempts = config.MAX_PORT_ATTEMPTS
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((config.SERVER_HOST, port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"Aucun port disponible trouvé entre {start_port} et {start_port + max_attempts - 1}")

def run_server():
    """Run the server with power saving features"""
    import sys
    # Security: bind to localhost only to prevent network exposure
    port = find_available_port()
    print(f"🚀 Démarrage du serveur sur le port {port}", flush=True)
    mode_name = "Économie d'énergie" if config.POWER_SAVING_MODE else "Normal"
    print(f"⚡ Mode: {mode_name}", flush=True)
    print(f"🔊 Modèle Whisper: {config.WHISPER_MODEL_SIZE} (lazy load)", flush=True)
    print(f"⏱️  Idle timeout: {config.SERVER_IDLE_TIMEOUT}s", flush=True)

    # Start idle timer if configured
    if config.SERVER_IDLE_TIMEOUT > 0:
        start_idle_timer(config.SERVER_IDLE_TIMEOUT)

    # Configure uvicorn for power saving
    uvicorn.run(
        app,
        host=config.SERVER_HOST,
        port=port,
        log_level="warning",  # Reduce logging overhead
        access_log=False  # Disable access logging for performance
    )

if __name__ == "__main__":
    run_server()
