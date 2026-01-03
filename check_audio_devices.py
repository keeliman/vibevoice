#!/usr/bin/env python3
"""Comprehensive audio device and permission checker"""
import sounddevice as sd
import numpy as np
from scipy.io import wavfile

print("=" * 60)
print("AUDIO DEVICE AND PERMISSION DIAGNOSTIC")
print("=" * 60)

# List ALL devices
print("\n🎤 ALL AUDIO DEVICES:")
print("-" * 60)
devices = sd.query_devices()
for i, dev in enumerate(devices):
    input_str = f"{dev['max_input_channels']} in" if dev['max_input_channels'] > 0 else "no in"
    output_str = f"{dev['max_output_channels']} out" if dev['max_output_channels'] > 0 else "no out"
    samplerate = f"{dev['default_samplerate']} Hz" if 'default_samplerate' in dev else "N/A"
    print(f"  [{i:2d}] {dev['name']}")
    print(f"       {input_str}, {output_str}, {samplerate}")

# Check default device
default_input = sd.query_devices(kind='input')
print(f"\n🎯 DEFAULT INPUT DEVICE:")
print(f"   {default_input['name']}")
samplerate = f"{default_input['default_samplerate']} Hz" if 'default_samplerate' in default_input else "N/A"
print(f"   Sample rate: {samplerate}")
print(f"   Max channels: {default_input['max_input_channels']}")

# Try to record from default device
print(f"\n🔴 TESTING MICROPHONE (3 seconds)...")
print("   SPEAK NOW!")
print("-" * 60)

try:
    duration = 3
    sample_rate = 16000

    # Try recording with explicit device
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype='float64'
    )
    sd.wait()

    # Analyze
    max_amp = np.max(np.abs(recording))
    rms = np.sqrt(np.mean(recording**2))

    print(f"\n📊 AUDIO ANALYSIS:")
    print(f"   Shape: {recording.shape}")
    print(f"   Max amplitude: {max_amp:.6f}")
    print(f"   RMS (volume): {rms:.6f}")

    if max_amp < 0.001:
        print("\n" + "=" * 60)
        print("❌ MICROPHONE NOT WORKING!")
        print("=" * 60)
        print("\n🔧 FIX STEPS:")
        print("1. Open: System Settings → Privacy & Security → Microphone")
        print("2. Make sure these are ENABLED:")
        print("   - Terminal (or your terminal app)")
        print("   - Python (may appear as 'Python 3.11' or similar)")
        print("3. If you don't see them in the list:")
        print("   a. Click the '+' button")
        print("   b. Navigate to /Applications/Utilities/Terminal.app")
        print("   c. Also add your Python from: /usr/bin/python3")
        print("   d. Or from venv: /Users/mandria/Documents/AITools/VibeVoice/venv/bin/python3")
        print("4. **IMPORTANT**: Completely QUIT and restart Terminal after granting")
        print("5. Try running this script again")
        print("\n💡 Alternative: Check System Settings → Privacy & Security → Screen Recording")
        print("   Sometimes this is also required for audio capture")
        print("=" * 60)
    elif max_amp < 0.01:
        print("\n⚠️  Audio is very quiet but detected")
        print("   Try speaking closer to the mic or check system volume")
    else:
        print(f"\n✅ SUCCESS! Microphone is working (max amp: {max_amp:.3f})")
        print("   If transcription still fails, the issue is with Whisper, not the mic")

    # Save recording
    wavfile.write('diagnostic_recording.wav', sample_rate, (recording * 32767).astype(np.int16))
    print(f"\n💾 Saved diagnostic recording to: diagnostic_recording.wav")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    print("\nThis usually means:")
    print("1. Microphone permission not granted to Terminal/Python")
    print("2. No microphone connected")
    print("3. Wrong device selected")
