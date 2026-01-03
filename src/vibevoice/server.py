"""FastAPI server for Whisper transcription"""

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from faster_whisper import WhisperModel

app = FastAPI()

# Use CPU for macOS (CUDA is for NVIDIA GPUs)
#model = WhisperModel("large", device="cuda", compute_type="float16")
model = WhisperModel("small", device="cpu", compute_type="int8")

class TranscribeRequest(BaseModel):
    file_path: str

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/transcribe/")
async def transcribe(request: TranscribeRequest):
    print(f"DEBUG: Transcribing file: {request.file_path}")
    segments, info = model.transcribe(
        request.file_path,
        language="fr",
        beam_size=1,
        best_of=1,
        no_speech_threshold=0.1,  # Lowered from 0.6 to be less aggressive
        vad_filter=False,  # Disable VAD filter to prevent false negatives
        condition_on_previous_text=False
    )
    print(f"DEBUG: Info: {info}")
    segments_list = list(segments)  # Convert generator to list
    print(f"DEBUG: Number of segments: {len(segments_list)}")
    all_text = [segment.text.strip() for segment in segments_list]
    print(f"DEBUG: Segments text: {all_text}")
    text = " ".join(all_text)
    return {"text": text}

def run_server():
    uvicorn.run(app, host="0.0.0.0", port=4242)

if __name__ == "__main__":
    run_server()
