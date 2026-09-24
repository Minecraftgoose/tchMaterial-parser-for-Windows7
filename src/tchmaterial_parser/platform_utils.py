# -*- coding: utf-8 -*-
# 平台相关的基础设施：错误输出与只读资源定位
# 本分支仅支持 Windows 7：不做跨平台分支，各模块按需自行导入 win32api / winreg / ctypes 等

from __future__ import annotations

import sys, traceback
from pathlib import Path

def print_error(e: Exception) -> None: # 打印错误信息到控制台
    if sys.stderr: # 无控制台运行时 sys.stderr 可能为 None
        traceback.print_exception(e)

def resource_path(*parts: str) -> Path: # 获取源码或 PyInstaller 打包后的只读资源路径
    bundle_root = getattr(sys, "_MEIPASS", None)

    if bundle_root: # PyInstaller 中数据被放在 tchmaterial_parser/assets/
        package_root = Path(bundle_root) / "tchmaterial_parser"
    else: # 源码运行或 wheel 安装
        package_root = Path(__file__).resolve().parent

    return package_root.joinpath(*parts)
