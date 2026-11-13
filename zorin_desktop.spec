# -*- mode: python ; coding: utf-8 -*-
# =========================================================
# ZORIN DESKTOP - PYINSTALLER PACKAGING SPECIFICATION
# Builds a standalone Windows executable for ZORIN Assistant.
# Usage: pyinstaller zorin_desktop.spec
# =========================================================

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
base_dir = os.path.abspath(os.path.dirname(__file__))

added_files = [
    (os.path.join(base_dir, 'backend', 'static'), os.path.join('backend', 'static')),
    (os.path.join(base_dir, 'models'), 'models'),
]

hidden_imports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'sounddevice',
    'numpy',
    'vosk',
    'google.genai',
    'google.genai.types',
    'pydantic',
    'dotenv',
    'fastapi',
    'uvicorn',
    'websockets',
    'sqlite3',
]

a = Analysis(
    [os.path.join('desktop', 'app.py')],
    pathex=[base_dir],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['.env', '*.log', 'tests'],
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
    name='ZORIN_Assistant',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZORIN_Assistant',
)
