# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/osia3/OneDrive/ドキュメント/Projects/TKFrameExtractor/video-frame-extractor2.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['skimage', 'PIL', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='静止画抽出アプリ',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
