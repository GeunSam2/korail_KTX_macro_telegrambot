# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ["src/gui_app.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=[
        "keyring.backends.Windows",
        "korail2",
        "google_auth_oauthlib.flow",
        "googleapiclient.discovery",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "testcontainers"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KTX 자동예약",
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
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="KTX 자동예약",
)
