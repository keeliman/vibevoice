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
from notifications import NotificationManager
import threading
import pygame

loading_indicator = LoadingIndicator()
notification_manager = NotificationManager()

# Initialize pygame for audio feedback (legacy support)
try:
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except:
    AUDIO_AVAILABLE = False
    print("Legacy audio feedback not available")

class VisualIndicator:
    def __init__(self):
        self.recording = False
        self.thread = None
        
    def show_recording(self, mode="dictation"):
        """Show visual recording indicator"""
        if self.thread and self.thread.is_alive():
            return
            
        self.recording = True
        self.thread = threading.Thread(target=self._recording_animation, args=(mode,))
        self.thread.daemon = True
        self.thread.start()
        
    def hide_recording(self):
        """Hide visual recording indicator"""
        self.recording = False
        if self.thread:
            self.thread.join(timeout=0.1)
            
    def _recording_animation(self, mode):
        """Animated recording indicator"""
        import time
        colors = {
            "dictation": "\033[92m",  # Green
            "command": "\033[94m"     # Blue
        }
        color = colors.get(mode, "\033[93m")  # Yellow default
        reset = "\033[0m"
        
        while self.recording:
            print(f"{color}🎙️  RECORDING ({mode.upper()}) {reset}", end="\r")
            time.sleep(0.5)
            print(f"{color}🎤 RECORDING ({mode.upper()}) {reset}", end="\r")
            time.sleep(0.5)
        print(" " * 50, end="\r")  # Clear the line

def play_sound(sound_type):
    """Play audio feedback with modern, pleasant sounds"""
    if not AUDIO_AVAILABLE:
        return
        
    try:
        sample_rate = 44100
        duration = 0.15
        
        if sound_type == "start":
            # Modern "ding" sound - ascending chord
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            # Create a pleasant ascending chord (C major triad)
            wave1 = np.sin(2 * np.pi * 523.25 * t)  # C5
            wave2 = np.sin(2 * np.pi * 659.25 * t)  # E5  
            wave3 = np.sin(2 * np.pi * 783.99 * t)  # G5
            
            # Blend the waves with fade in/out
            fade_samples = int(0.05 * sample_rate)
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)
            
            wave = (wave1 + wave2 + wave3) / 3
            wave[:fade_samples] *= fade_in
            wave[-fade_samples:] *= fade_out
            
            # Normalize and convert
            wave = (wave * 0.3 * 32767).astype(np.int16)
            
        elif sound_type == "stop":
            # Modern "dong" sound - descending chord
            t = np.linspace(0, duration, int(sample_rate * duration))
            
            # Create a pleasant descending chord (F major triad)
            wave1 = np.sin(2 * np.pi * 349.23 * t)  # F4
            wave2 = np.sin(2 * np.pi * 440.00 * t)  # A4
            wave3 = np.sin(2 * np.pi * 523.25 * t)  # C5
            
            # Blend the waves with fade in/out
            fade_samples = int(0.05 * sample_rate)
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)
            
            wave = (wave1 + wave2 + wave3) / 3
            wave[:fade_samples] *= fade_in
            wave[-fade_samples:] *= fade_out
            
            # Normalize and convert
            wave = (wave * 0.3 * 32767).astype(np.int16)
        
        pygame.mixer.Sound(wave).play()
        
    except Exception as e:
        print(f"Audio error: {e}")

visual_indicator = VisualIndicator()

def start_whisper_server():
    server_script = os.path.join(os.path.dirname(__file__), 'server.py')
    process = subprocess.Popen(['python3', server_script])
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
        
        # Try using macOS native screenshot command first
        try:
            import subprocess
            result = subprocess.run(['screencapture', '-x', screenshot_path], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and os.path.exists(screenshot_path):
                print("Used macOS native screenshot")
            else:
                raise Exception("Native screenshot failed")
        except Exception as e:
            print(f"Native screenshot failed: {e}, falling back to pyautogui")
            # Fallback to pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
        
        # Resize if needed
        from PIL import Image
        with Image.open(screenshot_path) as img:
            max_width = int(os.getenv('SCREENSHOT_MAX_WIDTH', '1024'))
            width, height = img.size
            
            if width > max_width:
                ratio = max_width / width
                new_width = max_width
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height))
                img.save(screenshot_path)
        
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
        # Disable screenshots on macOS by default due to workspace limitations
        include_screenshot = os.getenv('INCLUDE_SCREENSHOT', 'false').lower() == 'true'
        
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

def main():
    load_dotenv()
    key_label = os.environ.get("VOICEKEY", "cmd_r")
    cmd_label = os.environ.get("VOICEKEY_CMD", "f12")
    RECORD_KEY = Key[key_label]
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
            mode = "dictation"
            visual_indicator.show_recording(mode)
            notification_manager.recording_started(mode)
            print(f"\n🎙️  Started {mode} recording...")
        elif key == CMD_KEY and not recording:
            recording = True
            audio_data = []
            mode = "command"
            visual_indicator.show_recording(mode)
            notification_manager.recording_started(mode)
            print(f"\n🤖 Started {mode} recording...")

    def on_release(key):
        nonlocal recording, audio_data
        if key == RECORD_KEY or key == CMD_KEY:
            recording = False
            visual_indicator.hide_recording()
            notification_manager.recording_stopped()
            mode = "dictation" if key == RECORD_KEY else "command"
            print(f"\n⏹️  Stopped {mode} recording. Transcribing...")
            
            try:
                audio_data_np = np.concatenate(audio_data, axis=0)
            except ValueError as e:
                print(e)
                return
            
            recording_path = os.path.abspath('recording.wav')
            audio_data_int16 = (audio_data_np * np.iinfo(np.int16).max).astype(np.int16)
            wavfile.write(recording_path, sample_rate, audio_data_int16)

            try:
                response = requests.post('http://localhost:4242/transcribe/', 
                                      json={'file_path': recording_path})
                response.raise_for_status()
                transcript = response.json()['text']
                
                if transcript and key == RECORD_KEY:
                    processed_transcript = transcript + " "
                    print(processed_transcript)
                    keyboard_controller.type(processed_transcript)
                    notification_manager.transcription_complete(transcript)
                elif transcript and key == CMD_KEY:
                    success = _process_llm_cmd(keyboard_controller, transcript)
                    notification_manager.ai_processing_complete(success is not None)
            except requests.exceptions.RequestException as e:
                print(f"Error sending request to local API: {e}")
                notification_manager.transcription_error(str(e))
            except Exception as e:
                print(f"Error processing transcript: {e}")
                notification_manager.transcription_error(str(e))

    def callback(indata, frames, time, status):
        if status:
            print(status)
        if recording:
            audio_data.append(indata.copy())

    server_process = start_whisper_server()
    
    try:
        print(f"Waiting for the server to be ready...")
        wait_for_server()
        notification_manager.server_ready()
        print(f"\n🎉 VIBEVOICE IS ACTIVE! 🎉")
        print(f"🎙️  Dictation: Hold down {key_label} (⌘ droite)")
        print(f"🤖 AI Commands: Hold down {cmd_label} (F12)")
        print(f"🔔 Sound notifications: {'Enabled' if notification_manager.sound_enabled else 'Disabled'}")
        print(f"👁️  Visual notifications: {'Enabled' if notification_manager.visual_enabled else 'Disabled'}")
        print(f"💡 Legacy audio: {'Enabled' if AUDIO_AVAILABLE else 'Disabled'}")
        print(f"⏹️  Press Ctrl+C to stop\n")
        with Listener(on_press=on_press, on_release=on_release) as listener:
            with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
                listener.join()
    except TimeoutError as e:
        print(f"Error: {e}")
        notification_manager.server_error()
        server_process.terminate()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        server_process.terminate()

if __name__ == "__main__":
    main()
