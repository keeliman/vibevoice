"""Command-line interface for vibevoice"""

import os
import subprocess
import time
import json
import sounddevice as sd
import numpy as np
import requests
import sys
import base64

SCREENSHOT_AVAILABLE = False
try:
    import pyautogui
    from PIL import Image
    SCREENSHOT_AVAILABLE = True
except ImportError as e:
    print(f"Screenshot functionality not available: {e}")
    print("Install Pillow with: pip install Pillow")

from pynput.keyboard import Controller as KeyboardController, Key, Listener, KeyCode
from scipy.io import wavfile
from dotenv import load_dotenv

from loading_indicator import LoadingIndicator

loading_indicator = LoadingIndicator()

def start_whisper_server():
    server_script = os.path.join(os.path.dirname(__file__), 'server.py')
    process = subprocess.Popen([sys.executable, server_script])
    return process

def wait_for_server(timeout=1800, interval=0.5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get('http://localhost:4242/health')
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(interval)
    raise TimeoutError("Server failed to start within timeout")

def capture_screenshot():
    """Capture a screenshot, save it, and return the path and base64 data."""
    if not SCREENSHOT_AVAILABLE:
        print("Screenshot functionality not available. Install Pillow with: pip install Pillow")
        return None, None
        
    try:
        screenshot_path = os.path.abspath('screenshot.png')
        print(f"Capturing screenshot to: {screenshot_path}")
        
        screenshot = pyautogui.screenshot()
        
        max_width = int(os.getenv('SCREENSHOT_MAX_WIDTH', '1024'))
        width, height = screenshot.size
        
        if width > max_width:
            ratio = max_width / width
            new_width = max_width
            new_height = int(height * ratio)
            screenshot = screenshot.resize((new_width, new_height))
        
        screenshot.save(screenshot_path)
        
        with open(screenshot_path, "rb") as image_file:
            base64_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        return screenshot_path, base64_data
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        return None, None

def _process_llm_cmd(keyboard_controller, transcript):
    """Process transcript with Ollama and type the response."""

    try:
        loading_indicator.show(message=f"Processing: {transcript}")
        
        model = os.getenv('OLLAMA_MODEL', 'gemma3:27b')
        include_screenshot = os.getenv('INCLUDE_SCREENSHOT', 'true').lower() == 'true'
        
        screenshot_path, screenshot_base64 = (None, None)
        if include_screenshot and SCREENSHOT_AVAILABLE:
            screenshot_path, screenshot_base64 = capture_screenshot()
        
        user_prompt = transcript.strip()
        
        system_prompt = """You are a voice-controlled AI assistant. The user is talking to their computer using voice commands.
Your responses will be directly typed into the user's keyboard at their cursor position, so:
1. Be concise and to the point, but friendly and engaging - prefer shorter answers
2. Focus on answering the specific question or request
3. Don't use introductory phrases like "Here's..." or "Based on the screenshot..."
4. Don't include formatting like bullet points, which might look strange when typed
5. If you see a screenshot, analyze it and use it to inform your response
6. Never apologize for limitations or explain what you're doing"""
        
        if screenshot_base64:
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": model,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": True,
                "images": [screenshot_base64]  # Pass base64 data directly without data URI prefix
            }
            print(f"Sending request with screenshot to model: {model}")
        else:
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": model,
                "prompt": user_prompt,
                "system": system_prompt,
                "stream": True
            }
            print(f"Sending text-only request")
        
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                data = line.decode('utf-8')
                if data.startswith('{'):
                    chunk = json.loads(data)
                    if 'response' in chunk:
                        chunk_text = chunk['response']
                        print(f"Debug - received chunk: {repr(chunk_text)}")
                        
                        # Replace smart/curly quotes with standard apostrophes
                        # U+2018 (') and U+2019 (') are both replaced with standard apostrophe (')
                        normalized_text = chunk_text.replace('\u2019', "'").replace('\u2018', "'")
                        
                        keyboard_controller.type(normalized_text)
                        loading_indicator.hide()
        
        return "Successfully processed with Ollama"
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama: {e}")
    finally:
        loading_indicator.hide()

def generate_modern_sound(frequency, duration, volume=0.3):
    """Generate a modern notification sound using sine wave with fade in/out"""
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Apply fade in and fade out for smooth sound
    fade_duration = 0.05
    fade_samples = int(fade_duration * sample_rate)
    envelope = np.ones_like(t)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    
    # Generate tone with harmonic overtones for richer sound
    tone = (np.sin(2 * np.pi * frequency * t) + 
            0.3 * np.sin(2 * np.pi * frequency * 2 * t) +
            0.1 * np.sin(2 * np.pi * frequency * 3 * t))
    
    audio = tone * envelope * volume
    return (audio * 32767).astype(np.int16)

def play_start_sound():
    """Play a modern ascending sound when starting to record"""
    # Ascending tone: 880Hz (A5) -> 1108Hz (C#6)
    duration = 0.15
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    fade_samples = int(0.02 * sample_rate)
    envelope = np.ones_like(t)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    
    freq_start, freq_end = 880, 1108
    freqs = np.linspace(freq_start, freq_end, len(t))
    tone = np.sin(2 * np.pi * freqs * t)
    tone = tone * envelope * 0.3
    
    audio = (tone * 32767).astype(np.int16)
    sd.play(audio, 44100)

def play_stop_sound():
    """Play a modern descending sound when stopping recording"""
    # Descending tone: 1108Hz (C#6) -> 659Hz (E5)
    duration = 0.2
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    fade_samples = int(0.03 * sample_rate)
    envelope = np.ones_like(t)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    
    freq_start, freq_end = 1108, 659
    freqs = np.linspace(freq_start, freq_end, len(t))
    tone = np.sin(2 * np.pi * freqs * t)
    tone = tone * envelope * 0.25
    
    audio = (tone * 32767).astype(np.int16)
    sd.play(audio, 44100)

def main():
    load_dotenv()
    key_label = os.environ.get("VOICEKEY", "cmd_r")
    cmd_label = os.environ.get("VOICEKEY_CMD", "scroll_lock")
    
    # Handle cmd_r which is now available in pynput Key enum
    if key_label == "cmd_r":
        RECORD_KEY = Key.cmd_r
    else:
        RECORD_KEY = Key[key_label]
    
    # Handle cmd_key - disabled by default, only use cmd_r
    if cmd_label == "scroll_lock":
        CMD_KEY = None  # Disabled - only use cmd_r
    else:
        CMD_KEY = Key[cmd_label]
#    CMD_KEY = KeyCode(vk=65027)  # This is how you can use non-standard keys, this is AltGr for me

    recording = False
    audio_data = []
    sample_rate = 16000
    keyboard_controller = KeyboardController()

    def on_press(key):
        nonlocal recording, audio_data
        if key == RECORD_KEY and not recording:
            recording = True
            audio_data = []
            print("Listening...")
            play_start_sound()

    def on_release(key):
        nonlocal recording, audio_data
        if key == RECORD_KEY:
            recording = False
            print("Transcribing...")
            play_stop_sound()
            
            try:
                audio_data_np = np.concatenate(audio_data, axis=0)
            except ValueError as e:
                print(e)
                return
            
            recording_path = os.path.abspath('recording.wav')
            audio_data_int16 = (audio_data_np * np.iinfo(np.int16).max).astype(np.int16)
            wavfile.write(recording_path, sample_rate, audio_data_int16)
            print(f"DEBUG: Audio data shape: {audio_data_np.shape}, Duration: {len(audio_data_np)/sample_rate:.2f}s")

            try:
                response = requests.post('http://localhost:4242/transcribe/',
                                      json={'file_path': recording_path})
                response.raise_for_status()
                transcript = response.json()['text']
                print(f"DEBUG: Transcript received: '{transcript}'")

                if transcript and key == RECORD_KEY:
                    processed_transcript = transcript + " "
                    print(processed_transcript)
                    keyboard_controller.type(processed_transcript)
                elif transcript and key == CMD_KEY:
                    _process_llm_cmd(keyboard_controller, transcript)
                else:
                    print("DEBUG: Transcript is empty or key doesn't match")
            except requests.exceptions.RequestException as e:
                print(f"Error sending request to local API: {e}")
            except Exception as e:
                print(f"Error processing transcript: {e}")

    def callback(indata, frames, time, status):
        if status:
            print(status)
        if recording:
            audio_data.append(indata.copy())

    server_process = start_whisper_server()
    
    try:
        print(f"Waiting for the server to be ready...")
        wait_for_server()
        
        # List available audio devices
        devices = sd.query_devices()
        print(f"Available audio devices:")
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                print(f"  [{i}] {dev['name']} (inputs: {dev['max_input_channels']})")
        
        # Try to get default input device
        default_device = sd.query_devices(kind='input')
        print(f"Using default input device: {default_device['name']}")
        
        print(f"vibevoice is active. Hold down {key_label} to start dictating.")
        with Listener(on_press=on_press, on_release=on_release) as listener:
            with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
                listener.join()
    except TimeoutError as e:
        print(f"Error: {e}")
        server_process.terminate()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server_process.terminate()

if __name__ == "__main__":
    main()
