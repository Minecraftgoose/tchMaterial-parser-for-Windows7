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

# UPX 排除项：这些模块带 TLS/ASLR/自校验特性，压缩后在 Windows 7 上可能加载失败或触发杀软误报
# UPX 未安装时 upx=True 会被 PyInstaller 静默跳过，不会导致构建失败
upx_exclude = [
    "python38.dll",       # 解释器主 DLL
    "pythoncom38.dll",    # pywin32 COM，含 TLS，压缩后易崩
    "pywintypes38.dll",   # pywin32 基础类型
    "win32api.pyd",
    "win32com.shell.shell.pyd",
    "_ssl.pyd",           # OpenSSL，压缩后握手偶发异常
    "_hashlib.pyd",
    "_tkinter.pyd",       # Tk 入口，Win7 上对压缩敏感
    "tk86.dll",
    "tcl86.dll",
]

# 文件夹（onedir）模式：exe 只携带 pyz + 脚本，依赖与数据由 COLLECT 收集到同名目录下
# 产物固定为 dist/tchMaterial-parser-for-Windows7/（内含 exe 与 _internal/），供 NSIS 整体打包
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='tchMaterial-parser-for-Windows7',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=upx_exclude,
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
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=upx_exclude,
    name='tchMaterial-parser-for-Windows7',
)
