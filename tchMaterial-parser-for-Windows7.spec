# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

# sv-ttk 通过 Path(__file__).with_name() 加载主题文件，需把随包的 .tcl 与 .png 一并收集进来；图标文件是程序运行时读取的自有资源
runtime_assets = [
    (str(path), "tchmaterial_parser/assets")
    for path in Path("src/tchmaterial_parser/assets").glob("*.png")
]
data_files = collect_data_files("sv_ttk") + runtime_assets

a = Analysis(
    # 入口位于包外：PyInstaller 会把入口脚本当作 __main__ 分析，包内脚本的相对导入在此情形下不成立
    # pathex 指向 src/，使入口里的 import tchmaterial_parser 能被解析到
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=data_files,
    # Pillow 的 _imagingtk 通过 C 层动态导入，PyInstaller 无法静态发现
    hiddenimports=["PIL._tkinter_finder"],
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
    name='tchMaterial-parser-for-Windows7',
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
    version='version_info.txt',
    icon=['assets/icon.ico'],
)
