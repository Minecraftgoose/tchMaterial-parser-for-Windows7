# -*- coding: utf-8 -*-
# 平台相关的基础设施：错误输出与只读资源定位
# 本分支仅支持 Windows 7：不做跨平台分支，各模块按需自行导入 win32api / winreg / ctypes 等

from __future__ import annotations

import sys, traceback
from pathlib import Path

# 本分支只支持 Windows 7，因此操作系统类型是一个常量而非运行时探测的结果。
# 提供 os_name 是为了让同步自上游的模块（如 ui/download_manager.py）无需改写分支判断。
os_name = "Windows"

def print_error(e: Exception) -> None: # 打印错误信息到控制台
    if sys.stderr: # 无控制台运行时 sys.stderr 可能为 None
        # 必须显式传三个位置参数：Python 3.8 的 traceback.print_exception(etype, value, tb)
        # 三个都是必填的，到 3.10 才允许只传异常对象。本分支跑在 3.8 上，写成 print_exception(e) 会抛 TypeError。
        traceback.print_exception(type(e), e, e.__traceback__)

def resource_path(*parts: str) -> Path: # 获取源码或 PyInstaller 打包后的只读资源路径
    bundle_root = getattr(sys, "_MEIPASS", None)

    if bundle_root: # PyInstaller 中数据被放在 tchmaterial_parser/assets/
        package_root = Path(bundle_root) / "tchmaterial_parser"
    else: # 源码运行或 wheel 安装
        package_root = Path(__file__).resolve().parent

    return package_root.joinpath(*parts)
