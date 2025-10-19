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

try:
    # Try relative imports first (when run as module)
    from .loading_indicator import LoadingIndicator
    from .notifications import NotificationManager
except ImportError:
    # Fall back to absolute imports (when run as script)
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
            "command": "\033[94m",    # Blue
            "screenshot": "\033[95m"  # Magenta
        }
        icons = {
            "dictation": ["🎙️", "🎤"],
            "command": ["🤖", "🎯"],
            "screenshot": ["📷", "🖼️"]
        }
        color = colors.get(mode, "\033[93m")  # Yellow default
        mode_icons = icons.get(mode, ["🎙️", "🎤"])
        reset = "\033[0m"
        
        icon_index = 0
        while self.recording:
            current_icon = mode_icons[icon_index % len(mode_icons)]
            print(f"{color}{current_icon} RECORDING ({mode.upper()}) {reset}", end="\r")
            time.sleep(0.5)
            icon_index += 1
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
    process = subprocess.Popen(['python3', server_script], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              text=True)
    return process

def find_server_port(process, timeout=30):
    """Détecte le port du serveur en lisant sa sortie"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Lire la sortie du processus pour détecter le port
            if process.poll() is not None:
                # Le processus s'est terminé
                stderr = process.stderr.read()
                raise RuntimeError(f"Le serveur s'est arrêté: {stderr}")
            
            # Vérifier si on peut lire la sortie
            if process.stdout.readable():
                line = process.stdout.readline()
                if line and "Démarrage du serveur sur le port" in line:
                    # Extraire le numéro de port
                    import re
                    match = re.search(r'port (\d+)', line)
                    if match:
                        return int(match.group(1))
        except Exception as e:
            print(f"Erreur lors de la détection du port: {e}")
        
        time.sleep(0.1)
    
    # Fallback: essayer les ports par défaut
    for port in range(4242, 4252):
        try:
            response = requests.get(f'http://localhost:{port}/health', timeout=1)
            if response.status_code == 200:
                return port
        except requests.exceptions.RequestException:
            pass
    
    raise TimeoutError("Impossible de détecter le port du serveur")

def wait_for_server(port, timeout=30, interval=0.5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f'http://localhost:{port}/health')
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
        import tempfile
        import shlex
        
        # Security: use secure temporary file instead of predictable name
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False, prefix='vibevoice_screenshot_') as temp_file:
            screenshot_path = temp_file.name
        
        print(f"Capturing screenshot to: {screenshot_path}")
        
        # Security: validate screenshot path is in temp directory
        if not screenshot_path.startswith(tempfile.gettempdir()):
            raise ValueError("Screenshot path outside temporary directory")
        
        # Try using macOS native screenshot command first
        try:
            import subprocess
            # Security: use absolute path to screencapture and properly escape filename
            screencapture_path = '/usr/sbin/screencapture'
            if not os.path.exists(screencapture_path):
                raise Exception("screencapture command not found")
                
            result = subprocess.run([
                screencapture_path, '-x', screenshot_path
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0 and os.path.exists(screenshot_path):
                print("Used macOS native screenshot")
            else:
                raise Exception(f"Native screenshot failed: {result.stderr}")
        except Exception as e:
            print(f"Native screenshot failed: {e}, falling back to pyautogui")
            # Fallback to pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(screenshot_path)
        
        # Security: validate file was created and is reasonable size
        if not os.path.exists(screenshot_path):
            raise Exception("Screenshot file was not created")
            
        file_size = os.path.getsize(screenshot_path)
        if file_size == 0:
            raise Exception("Screenshot file is empty")
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            raise Exception("Screenshot file too large")
        
        # Resize if needed with input validation
        from PIL import Image
        with Image.open(screenshot_path) as img:
            # Security: validate environment variable input
            max_width_str = os.getenv('SCREENSHOT_MAX_WIDTH', '1024')
            try:
                max_width = int(max_width_str)
                if not (100 <= max_width <= 4096):  # Reasonable bounds
                    raise ValueError("Max width out of bounds")
            except ValueError:
                print(f"Invalid SCREENSHOT_MAX_WIDTH: {max_width_str}, using default")
                max_width = 1024
                
            width, height = img.size
            
            # Security: validate image dimensions
            if width <= 0 or height <= 0 or width > 10000 or height > 10000:
                raise ValueError("Invalid image dimensions")
            
            if width > max_width:
                ratio = max_width / width
                new_width = max_width
                new_height = int(height * ratio)
                
                # Security: validate new dimensions
                if new_height <= 0 or new_height > 4096:
                    raise ValueError("Invalid resized dimensions")
                    
                img = img.resize((new_width, new_height))
                img.save(screenshot_path)
        
        # Security: validate final file before reading
        final_size = os.path.getsize(screenshot_path)
        if final_size == 0:
            raise Exception("Processed screenshot is empty")
        if final_size > 20 * 1024 * 1024:  # 20MB limit after processing
            raise Exception("Processed screenshot too large")
        
        with open(screenshot_path, "rb") as image_file:
            base64_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        return screenshot_path, base64_data
    except Exception as e:
        print(f"Error capturing screenshot: {e}")
        # Clean up temporary file on error
        try:
            if 'screenshot_path' in locals() and os.path.exists(screenshot_path):
                os.unlink(screenshot_path)
        except:
            pass
        return None, None

def _process_llm_cmd(keyboard_controller, transcript, force_screenshot=False):
    """Process transcript with Ollama and type the response."""

    try:
        # Security: validate and sanitize transcript input
        if not transcript or not isinstance(transcript, str):
            raise ValueError("Invalid transcript input")
        
        transcript = transcript.strip()
        if len(transcript) > 1000:  # Reasonable limit for voice commands
            raise ValueError("Transcript too long")
        
        if not transcript:  # Empty after strip
            print("Empty transcript, skipping processing")
            return None
        
        loading_indicator.show(message=f"Processing: {transcript[:50]}...")  # Limit displayed text
        
        # Security: validate environment variables
        model = os.getenv('OLLAMA_MODEL', 'gemma3:27b')
        if not model or len(model) > 100:  # Reasonable model name length
            print("Invalid OLLAMA_MODEL, using default")
            model = 'gemma3:27b'
        
        # Screenshot logic: force for screenshot mode, or check env var
        if force_screenshot:
            include_screenshot = SCREENSHOT_AVAILABLE
            print("📷 Screenshot mode: capturing screen context...")
        else:
            # Disable screenshots on macOS by default due to workspace limitations
            include_screenshot_str = os.getenv('INCLUDE_SCREENSHOT', 'false').lower()
            include_screenshot = include_screenshot_str in ('true', '1', 'yes', 'on') and SCREENSHOT_AVAILABLE
        
        screenshot_path, screenshot_base64 = (None, None)
        if include_screenshot:
            screenshot_path, screenshot_base64 = capture_screenshot()
        
        user_prompt = transcript
        
        system_prompt = """You are a voice-controlled AI assistant. The user is talking to their computer using voice commands.
Your responses will be directly typed into the user's keyboard at their cursor position, so:
1. Be concise and to the point, but friendly and engaging - prefer shorter answers
2. Focus on answering the specific question or request
3. Don't use introductory phrases like "Here's..." or "Based on the screenshot..."
4. Don't include formatting like bullet points, which might look strange when typed
5. If you see a screenshot, analyze it and use it to inform your response
6. Never apologize for limitations or explain what you're doing"""
        
        # Security: use localhost URL and validate
        base_url = "http://127.0.0.1:11434"  # Use localhost IP instead of hostname
        url = f"{base_url}/api/generate"
        
        # Security: validate payload size and content
        payload = {
            "model": model,
            "prompt": user_prompt,
            "system": system_prompt,
            "stream": True
        }
        
        if screenshot_base64:
            # Security: validate base64 data
            if len(screenshot_base64) > 50 * 1024 * 1024:  # 50MB limit
                print("Screenshot too large, skipping")
            else:
                payload["images"] = [screenshot_base64]
                print(f"Sending request with screenshot to model: {model}")
        else:
            print(f"Sending text-only request to model: {model}")
        
        # Security: add timeout and size limits (longer timeout for screenshots)
        timeout_seconds = 60 if screenshot_base64 else 30  # 60s for screenshots, 30s for text
        try:
            response = requests.post(
                url, 
                json=payload, 
                stream=True,
                timeout=timeout_seconds,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'VibeVoice/1.0'
                }
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            if screenshot_base64:
                raise Exception(f"Request timeout ({timeout_seconds}s) - Screenshots require more processing time. Try a lighter model or check Ollama performance.")
            else:
                raise Exception("Request timeout - Ollama server may be overloaded")
        except requests.exceptions.ConnectionError:
            raise Exception("Cannot connect to Ollama server. Make sure Ollama is running.")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
        
        # Security: limit response processing with size and time limits
        total_response_size = 0
        max_response_size = 10 * 1024  # 10KB limit for AI responses
        
        for line in response.iter_lines():
            if line:
                total_response_size += len(line)
                if total_response_size > max_response_size:
                    print("Response too large, truncating")
                    break
                    
                try:
                    data = line.decode('utf-8')
                    if data.startswith('{'):
                        chunk = json.loads(data)
                        if 'response' in chunk:
                            chunk_text = chunk['response']
                            
                            # Security: validate chunk content
                            if not isinstance(chunk_text, str):
                                continue
                            if len(chunk_text) > 500:  # Limit individual chunks
                                chunk_text = chunk_text[:500]
                            
                            print(f"Debug - received chunk: {repr(chunk_text[:50])}")
                            
                            # Replace smart/curly quotes with standard apostrophes
                            # U+2018 (') and U+2019 (') are both replaced with standard apostrophe (')
                            normalized_text = chunk_text.replace('\u2019', "'").replace('\u2018', "'")
                            
                            # Security: basic content filtering (remove control characters except newline/tab)
                            import re
                            normalized_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', normalized_text)
                            
                            keyboard_controller.type(normalized_text)
                            loading_indicator.hide()
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"Error processing response chunk: {e}")
                    continue
        
        return "Successfully processed with Ollama"
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama: {e}")
    finally:
        loading_indicator.hide()

def check_dependencies():
    """Vérifie que toutes les dépendances sont disponibles"""
    missing_deps = []
    
    try:
        import sounddevice as sd
        # Vérifier que l'audio est disponible
        devices = sd.query_devices()
        if not devices:
            missing_deps.append("Aucun périphérique audio détecté")
    except ImportError:
        missing_deps.append("sounddevice")
    except Exception as e:
        missing_deps.append(f"Erreur audio: {e}")
    
    try:
        import requests
    except ImportError:
        missing_deps.append("requests")
    
    try:
        import numpy as np
    except ImportError:
        missing_deps.append("numpy")
    
    if missing_deps:
        print("❌ Dépendances manquantes:")
        for dep in missing_deps:
            print(f"   - {dep}")
        print("\n💡 Installez les dépendances avec: pip install -r requirements.txt")
        return False
    
    return True

def main():
    print("🚀 Démarrage de VibeVoice...")
    
    # Vérifications préliminaires
    if not check_dependencies():
        sys.exit(1)
    
    load_dotenv()
    key_label = os.environ.get("VOICEKEY", "cmd_r")
    cmd_label = os.environ.get("VOICEKEY_CMD", "f12")
    screenshot_cmd_label = os.environ.get("VOICEKEY_SCREENSHOT", "alt_r")
    RECORD_KEY = Key[key_label]
    CMD_KEY = Key[cmd_label]
    SCREENSHOT_CMD_KEY = Key[screenshot_cmd_label]
#    CMD_KEY = KeyCode(vk=65027)  # This is how you can use non-standard keys, this is AltGr for me

    recording = False
    processing = False  # Prevent double processing
    audio_data = []
    sample_rate = 16000
    keyboard_controller = KeyboardController()
    server_port = None  # Sera défini lors du démarrage du serveur

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
        elif key == SCREENSHOT_CMD_KEY and not recording:
            recording = True
            audio_data = []
            mode = "screenshot"
            visual_indicator.show_recording(mode)
            notification_manager.recording_started(mode)
            print(f"\n📷 Started {mode} recording (with context)...")

    def on_release(key):
        nonlocal recording, processing, audio_data, server_port
        if key == RECORD_KEY or key == CMD_KEY or key == SCREENSHOT_CMD_KEY:
            if not recording or processing:
                return  # Already processed or not recording
            
            recording = False
            processing = True  # Prevent double processing
            visual_indicator.hide_recording()
            notification_manager.recording_stopped()
            
            if key == RECORD_KEY:
                mode = "dictation"
            elif key == CMD_KEY:
                mode = "command"
            else:  # SCREENSHOT_CMD_KEY
                mode = "screenshot"
            
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
                response = requests.post(f'http://localhost:{server_port}/transcribe/', 
                                      json={'file_path': recording_path})
                response.raise_for_status()
                transcript = response.json()['text']
                
                if transcript and key == RECORD_KEY:
                    processed_transcript = transcript + " "
                    print(processed_transcript)
                    keyboard_controller.type(processed_transcript)
                    notification_manager.transcription_complete(transcript)
                elif transcript and key == CMD_KEY:
                    success = _process_llm_cmd(keyboard_controller, transcript, force_screenshot=False)
                    notification_manager.ai_processing_complete(success is not None)
                elif transcript and key == SCREENSHOT_CMD_KEY:
                    success = _process_llm_cmd(keyboard_controller, transcript, force_screenshot=True)
                    notification_manager.ai_processing_complete(success is not None)
            except requests.exceptions.RequestException as e:
                print(f"❌ Erreur lors de l'envoi de la requête à l'API locale: {e}")
                print(f"💡 Vérifiez que le serveur fonctionne sur le port {server_port}")
                notification_manager.transcription_error(str(e))
            except Exception as e:
                print(f"❌ Erreur lors du traitement de la transcription: {e}")
                notification_manager.transcription_error(str(e))
            finally:
                processing = False  # Reset processing flag

    def callback(indata, frames, time, status):
        if status:
            print(status)
        if recording:
            audio_data.append(indata.copy())

    server_process = start_whisper_server()
    
    try:
        print(f"🔍 Détection du port du serveur...")
        server_port = find_server_port(server_process)
        print(f"✅ Serveur détecté sur le port {server_port}")
        
        # Mettre à jour la variable dans la portée de main
        globals()['server_port'] = server_port
        
        print(f"⏳ Attente que le serveur soit prêt...")
        wait_for_server(server_port)
        notification_manager.server_ready()
        print(f"\n🎉 VIBEVOICE IS ACTIVE! 🎉")
        print(f"🎙️  Dictation: Hold down {key_label} (⌘ droite)")
        print(f"🤖 AI Commands: Hold down {cmd_label} (F12)")
        print(f"📷 AI with Screenshot: Hold down {screenshot_cmd_label} (Option droite)")
        print(f"🔔 Sound notifications: {'Enabled' if notification_manager.sound_enabled else 'Disabled'}")
        print(f"👁️  Visual notifications: {'Enabled' if notification_manager.visual_enabled else 'Disabled'}")
        print(f"💡 Legacy audio: {'Enabled' if AUDIO_AVAILABLE else 'Disabled'}")
        print(f"⏹️  Press Ctrl+C to stop\n")
        with Listener(on_press=on_press, on_release=on_release) as listener:
            with sd.InputStream(callback=callback, channels=1, samplerate=sample_rate):
                listener.join()
    except TimeoutError as e:
        print(f"❌ Erreur de timeout: {e}")
        print("💡 Le serveur n'a pas pu démarrer dans les temps. Vérifiez les ports disponibles.")
        notification_manager.server_error()
        server_process.terminate()
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ Erreur du serveur: {e}")
        print("💡 Vérifiez que toutes les dépendances sont installées correctement.")
        notification_manager.server_error()
        server_process.terminate()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt en cours...")
    finally:
        if server_process.poll() is None:
            print("🔄 Arrêt du serveur...")
            server_process.terminate()
            server_process.wait(timeout=5)

if __name__ == "__main__":
    main()
