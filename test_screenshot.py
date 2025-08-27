#!/usr/bin/env python3
"""Test screenshot functionality for VibeVoice"""

import os
import sys
sys.path.insert(0, 'src')

from vibevoice.cli import capture_screenshot, SCREENSHOT_AVAILABLE

def test_screenshot():
    print("🖼️ Testing screenshot functionality...")
    print(f"Screenshot available: {SCREENSHOT_AVAILABLE}")
    
    if not SCREENSHOT_AVAILABLE:
        print("❌ Screenshot dependencies not available")
        return False
    
    print("📸 Attempting to capture screenshot...")
    screenshot_path, screenshot_base64 = capture_screenshot()
    
    if screenshot_path and screenshot_base64:
        print(f"✅ Screenshot captured successfully!")
        print(f"   Path: {screenshot_path}")
        print(f"   Base64 size: {len(screenshot_base64)} bytes")
        print(f"   File exists: {os.path.exists(screenshot_path)}")
        if os.path.exists(screenshot_path):
            print(f"   File size: {os.path.getsize(screenshot_path)} bytes")
        
        # Test base64 validity
        try:
            import base64
            decoded = base64.b64decode(screenshot_base64)
            print(f"   Base64 valid: True ({len(decoded)} decoded bytes)")
        except Exception as e:
            print(f"   Base64 valid: False ({e})")
        
        return True
    else:
        print("❌ Screenshot capture failed")
        return False

if __name__ == "__main__":
    success = test_screenshot()
    sys.exit(0 if success else 1)