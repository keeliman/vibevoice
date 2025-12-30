# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for VibeVoice

import sys
from pathlib import Path

# Add src to path for analysis
src_path = Path.cwd() / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

block_cipher = None

a = Analysis(
    ['src/vibevoice/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/vibevoice', 'vibevoice'),
    ],
    hiddenimports=[
        'vibevoice.cli',
        'vibevoice.server',
        'vibevoice.notifications',
        'vibevoice.loading_indicator',
        'vibevoice.config',
        'vibevoice.control_state',
        'vibevoice.menubar',
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
    excludes=['tkinter', 'matplotlib', 'pandas', 'test', 'pytest'],
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
    icon=None,  # Use default icon
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
