# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files

ROOT = Path(SPECPATH)

datas = [
    (str(ROOT / "img"), "img"),
    (str(ROOT / "styles"), "styles"),
    (str(ROOT / "sounds"), "sounds"),
    (str(ROOT / "data" / "trainer.seed.db"), "data"),
]
icon_path = ROOT / "packaging" / "app.ico"

binaries = []
hiddenimports = [
    "PyQt5",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.QtSvg",
    "PyQt5.QtMultimedia",
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.ImageFont",
    "imageio",
    "imageio.plugins.pillow",
    "pygame",
    "cv2",
    "mediapipe",
    "numpy",
]

for package in ("mediapipe", "cv2"):
    pkg_datas, pkg_binaries, pkg_hidden = collect_all(package)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hidden

datas += collect_data_files("imageio")

a = Analysis(
    [str(ROOT / "run_app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "tkinter",
        "unittest",
        "pytest",
        "PyQt5.QtWebEngine",
        "PyQt5.QtWebEngineWidgets",
        "PyQt5.QtBluetooth",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VestibularTrainer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(icon_path) if icon_path.is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="VestibularTrainer",
)
