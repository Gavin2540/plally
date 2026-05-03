# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect ALL data files for UI packages
ctk_datas = collect_data_files('customtkinter', include_py_files=False)
ctkmsg_datas = collect_data_files('CTkMessagebox', include_py_files=False)


a = Analysis(
    ['ui/login.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('db/schema.sql', 'db'),
        ('db/migrations', 'db/migrations'),
    ] + ctk_datas + ctkmsg_datas,
    hiddenimports=[
        'customtkinter',
        'customtkinter.windows',
        'customtkinter.windows.widgets',
        'customtkinter.windows.widgets.theme',
        'customtkinter.windows.widgets.theme.theme_manager',
        'CTkMessagebox',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.styles',
        'reportlab.lib.units',
        'reportlab.platypus',
        'reportlab.platypus.tables',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.utils',
        'sqlite3',

        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests', 'graphify-out', 'graphify'],
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
    name='PlywoodPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PlywoodPro',
)
