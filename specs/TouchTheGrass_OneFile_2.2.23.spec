# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['c:\\Users\\tarik\\Documents\\PY\\Touch-The-Grass-TTG\\Main\\game\\__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('c:\\Users\\tarik\\Documents\\PY\\Touch-The-Grass-TTG\\Main\\Assets', 'Assets'), ('c:\\Users\\tarik\\Documents\\PY\\Touch-The-Grass-TTG\\Main\\game', 'game')],
    hiddenimports=['game', 'pygame', 'pygame.mixer'],
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
    name='TouchTheGrass_OneFile_2.2.23',
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
    icon=['c:\\Users\\tarik\\Documents\\PY\\Touch-The-Grass-TTG\\Main\\Assets\\images\\icon.ico'],
)
