"""FastAPI server for Whisper transcription"""

import gc
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from faster_whisper import WhisperModel

try:
    import orjson as json_lib
except ImportError:
    import json as json_lib

app = FastAPI()

model = WhisperModel("large", device="cuda", compute_type="float16")
# Enable in case you want to run on CPU, but it's much slower
#model = WhisperModel("medium", device="cpu", compute_type="int8")

class TranscribeRequest(BaseModel):
    file_path: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

def _transcribe_stream(file_path: str):
    """Stream transcription segments as they are generated."""
    segments, info = model.transcribe(
        file_path,
        vad_filter=True,
        language=None,  # Auto-detect for faster startup
        condition_on_previous_text=False,  # Faster streaming
    )
    for segment in segments:
        text = segment.text.strip()
        if text:
            yield f"data: {json_lib.dumps({'text': text}).decode()}\n\n"
    yield f"data: {json_lib.dumps({'done': True}).decode()}\n\n"

@app.post("/transcribe/")
async def transcribe(request: TranscribeRequest):
    try:
        return StreamingResponse(
            _transcribe_stream(request.file_path),
            media_type="text/event-stream",
        )
    finally:
        # Suggest garbage collection after each transcription to free memory
        gc.collect()

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=4242)

if __name__ == "__main__":
    run_server()
