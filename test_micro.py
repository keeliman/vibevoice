#!/usr/bin/env python3
"""Test script to verify microphone is working"""
import sounddevice as sd
import numpy as np
import sys

print("Testing microphone...")
print("\nAll input devices:")
devices = sd.query_devices()
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"  [{i}] {dev['name']}")

print(f"\nDefault input device: {sd.query_devices(kind='input')['name']}")

print("\n⚠️  IMPORTANT: Make sure you allow microphone access!")
print("   Go to: System Settings > Privacy & Security > Microphone")
print("   Make sure 'Terminal' AND 'Python' are enabled")

print("\nRecording 3 seconds of audio... (speak now!)")
duration = 3
sample_rate = 16000
recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
sd.wait()

print("Analyzing audio...")
audio_max = np.max(np.abs(recording))
audio_rms = np.sqrt(np.mean(recording**2))
audio_mean = np.mean(recording)

print(f"Audio shape: {recording.shape}")
print(f"Max amplitude: {audio_max:.6f}")
print(f"RMS (volume): {audio_rms:.6f}")
print(f"Mean: {audio_mean:.6f}")

if audio_max < 0.001:
    print("\n❌ PROBLEM: Audio is too quiet - microphone is not picking up sound!")
    print("Possible issues:")
    print("1. Microphone permissions not granted to Python/Terminal")
    print("2. Wrong input device selected")
    print("3. Microphone hardware issue")
elif audio_max < 0.01:
    print("\n⚠️  WARNING: Audio is very quiet, but some sound detected")
    print("Try speaking closer to the microphone or check volume settings")
else:
    print("\n✅ SUCCESS: Microphone is working and capturing audio!")
    print(f"Max amplitude: {audio_max:.3f} (good level)")

# Save for inspection
output_file = "test_recording.wav"
from scipy.io import wavfile
wavfile.write(output_file, sample_rate, recording.astype(np.int16))
print(f"\nSaved test recording to: {output_file}")
