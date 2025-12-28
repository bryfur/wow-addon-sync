#!/usr/bin/env python3
"""
Build script for creating distributable executables of WoW Sync.
"""
import PyInstaller.__main__
import sys
from pathlib import Path

# Get the project root
ROOT = Path(__file__).parent

# Common PyInstaller arguments
common_args = [
    'wow_sync/__main__.py',
    '--name=WoWSync',
    '--onedir' if sys.platform == 'darwin' else '--onefile',
    '--noconsole',
    '--icon=icons/icon.png',
    f'--add-data=icons{";" if sys.platform == "win32" else ":"}icons',
    '--hidden-import=tkinter',
    '--hidden-import=sv_ttk',
    '--hidden-import=darkdetect',
    '--hidden-import=pygit2',
    '--hidden-import=pygit2._pygit2',
    '--hidden-import=cffi',
    '--hidden-import=_cffi_backend',
    '--hidden-import=psutil',
    '--hidden-import=PIL',
    '--hidden-import=dbus_fast',
    '--hidden-import=async_tkinter_loop',
    '--collect-all=sv_ttk',
    '--collect-all=darkdetect',
    '--collect-all=pygit2',
    '--clean',
]

# Platform-specific adjustments
if sys.platform.startswith('linux'):
    common_args.append('--hidden-import=dbus_fast.aio')
elif sys.platform == 'darwin':
    # macOS-specific: set bundle identifier for proper .app
    common_args.append('--osx-bundle-identifier=com.wowsync.app')

print(f"Building WoW Sync for {sys.platform}...")
PyInstaller.__main__.run(common_args)
print("Build complete! Check the 'dist' folder.")
