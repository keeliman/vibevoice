#!/usr/bin/env python3
"""Test script to detect key codes"""

from pynput.keyboard import Listener, KeyCode, Key
import sys

print("Appuyez sur des touches pour voir leur code...")
print("Pressez Ctrl+C pour quitter")

def on_press(key):
    print(f"Touche pressée: {key} - Type: {type(key)}", end="")
    
    if hasattr(key, 'vk'):
        print(f" - vk: {key.vk}")
    elif hasattr(key, 'char'):
        print(f" - char: {key.char}")
    elif isinstance(key, Key):
        print(f" - Key enum: {key}")
    else:
        print()

def on_release(key):
    if key == Key.esc:
        print("\nArrêt...")
        return False

with Listener(on_press=on_press, on_release=on_release) as listener:
    listener.join()
