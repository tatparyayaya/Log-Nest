# -*- mode: python ; coding: utf-8 -*-

import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('app_icon.ico', '.'),
        ('app_icon.png', '.'),
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'win32evtlog',
        'win32evtlogutil',
        'win32con',
        'win32api',
        'watchdog',
        'watchdog.observers',
        'watchdog.observers.winapi',
        'watchdog.events',
        'psutil',
        'sqlite3',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
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

# Qt uses the ICU and Universal CRT supplied by Windows. Dependency scanning
# can pick incompatible same-named DLLs from unrelated tools on PATH (for
# example Poppler's ICU). Never shadow these Windows components in the bundle.
windows_components = {"icuuc.dll", "icuin.dll", "icu.dll", "ucrtbase.dll"}
a.binaries = [
    entry for entry in a.binaries
    if os.path.basename(entry[0]).lower() not in windows_components
    and not os.path.basename(entry[0]).lower().startswith(
        ("api-ms-", "ext-ms-", "icudt")
    )
]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LogNest',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LogNest',
)
