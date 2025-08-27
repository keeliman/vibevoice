"""FastAPI server for Whisper transcription"""

import os
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from faster_whisper import WhisperModel

app = FastAPI()

# Use CPU on macOS since CUDA is not supported
model = WhisperModel("medium", device="cpu", compute_type="int8")
# Enable in case you want to run on GPU (Linux/Windows with CUDA)
#model = WhisperModel("large", device="cuda", compute_type="float16")

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
    
    @validator('file_path')
    def validate_file_path_input(cls, v):
        # Basic validation - detailed validation happens in endpoint
        if not v or not isinstance(v, str):
            raise ValueError('file_path must be a non-empty string')
        if len(v) > 1000:  # Prevent extremely long paths
            raise ValueError('file_path too long')
        return v.strip()

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/transcribe/")
async def transcribe(request: TranscribeRequest):
    try:
        # Security: validate file path to prevent path traversal
        safe_path = validate_file_path(request.file_path)
        
        # Perform transcription on validated file
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

def run_server():
    # Security: bind to localhost only to prevent network exposure
    uvicorn.run(app, host="127.0.0.1", port=4242)

if __name__ == "__main__":
    run_server()
