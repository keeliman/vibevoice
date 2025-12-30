#!/usr/bin/env python3
"""
Build script for VibeVoice macOS app
Creates a standalone .app bundle with PyInstaller
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
        return True

def create_icon():
    """Create a simple icon for the app"""
    from PIL import Image, ImageDraw

    icon_path = Path("resources/icon.png")
    icon_path.parent.mkdir(exist_ok=True)

    # Create a simple microphone icon
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw microphone shape
    center_x, center_y = size // 2, size // 2

    # Mic body (rounded rectangle)
    mic_width = size // 3
    mic_height = size // 2
    x1 = center_x - mic_width // 2
    y1 = center_y - mic_height // 2 - size // 10
    x2 = center_x + mic_width // 2
    y2 = y1 + mic_height
    draw.rounded_rectangle([x1, y1, x2, y2], radius=20, fill=(52, 152, 219, 255))

    # Mic grille lines
    for i in range(5):
        y = y1 + 30 + i * 40
        draw.line([(x1 + 20, y), (x2 - 20, y)], fill=(255, 255, 255, 200), width=8)

    # Mic stand
    stand_width = 20
    draw.rectangle([center_x - stand_width // 2, y2, center_x + stand_width // 2, y2 + 60],
                   fill=(100, 100, 100, 255))

    # Base
    base_width = mic_width + 40
    base_y = y2 + 60
    draw.rounded_rectangle([center_x - base_width // 2, base_y, center_x + base_width // 2, base_y + 30],
                          radius=10, fill=(80, 80, 80, 255))

    img.save(icon_path)
    print(f"✅ Icon created at {icon_path}")
    return icon_path

def create_spec_file():
    """Generate PyInstaller spec file"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/vibevoice/cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env.example', '.'),
        ('src/vibevoice', 'vibevoice'),
    ],
    hiddenimports=[
        'vibevoice.cli',
        'vibevoice.server',
        'vibevoice.notifications',
        'vibevoice.loading_indicator',
        'vibevoice.config',
        'faster_whisper',
        'torch',
        'torchaudio',
        'numpy',
        'scipy',
        'sounddevice',
        'pynput',
        'pyautogui',
        'PIL',
        'chime',
        'desktop_notifier',
        'pygame',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='VibeVoice',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='VibeVoice',
)

app = BUNDLE(
    coll,
    name='VibeVoice.app',
    icon='resources/icon.icns',
    bundle_identifier='com.vibevoice.app',
    info_plist={
        'CFBundleName': 'VibeVoice',
        'CFBundleDisplayName': 'VibeVoice',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'LSMinimumSystemVersion': '10.13.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'NSAppleScriptEnabled': False,
        'LSUIElement': True,  # Run as background agent (no dock icon)
    },
)
'''
    with open("vibevoice.spec", "w") as f:
        f.write(spec_content)
    print("✅ Spec file created")

def convert_png_to_icns(png_path):
    """Convert PNG to ICNS format"""
    icns_path = png_path.parent / "icon.icns"

    # Create iconset
    iconset_path = png_path.parent / "icon.iconset"
    iconset_path.mkdir(exist_ok=True)

    # Generate different sizes
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    for size in sizes:
        # Regular
        img = Image.open(png_path)
        img_resized = img.resize((size, size), Image.Resampling.LANCZOS)
        img_resized.save(iconset_path / f"icon_{size}x{size}.png")

        # Retina
        img_retina = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
        img_retina.save(iconset_path / f"icon_{size}x{size}@2x.png")

    # Convert to ICNS
    subprocess.run([
        "iconutil",
        "-c", "icns",
        "-o", str(icns_path),
        str(iconset_path)
    ], check=True)

    # Clean up iconset
    shutil.rmtree(iconset_path)

    print(f"✅ ICNS icon created at {icns_path}")
    return icns_path

def build_app():
    """Build the macOS app bundle"""
    print("🔨 Building VibeVoice for macOS...")

    # Check dependencies
    if not check_dependencies():
        print("❌ Failed to install PyInstaller")
        return False

    # Create resources directory
    Path("resources").mkdir(exist_ok=True)

    # Create icon
    try:
        png_icon = create_icon()
        icns_icon = convert_png_to_icns(png_icon)
    except Exception as e:
        print(f"⚠️  Icon creation failed: {e}")
        print("Continuing without custom icon...")

    # Create spec file
    create_spec_file()

    # Run PyInstaller
    print("🚀 Running PyInstaller...")
    result = subprocess.run([
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "vibevoice.spec"
    ])

    if result.returncode == 0:
        print("✅ Build successful!")
        print("📦 App bundle created at: dist/VibeVoice.app")

        # Instructions
        print("\n" + "=" * 60)
        print("📋 Next Steps:")
        print("=" * 60)
        print("1. Move the app to Applications:")
        print("   mv dist/VibeVoice.app /Applications/")
        print()
        print("2. Run the app:")
        print("   open /Applications/VibeVoice.app")
        print()
        print("3. Or install as LaunchAgent for auto-start:")
        print("   ./install-service.sh")
        print("=" * 60)

        return True
    else:
        print("❌ Build failed")
        return False

if __name__ == "__main__":
    build_app()
