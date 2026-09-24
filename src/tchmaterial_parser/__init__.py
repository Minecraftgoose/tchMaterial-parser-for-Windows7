# -*- coding: utf-8 -*-
# 国家中小学智慧教育平台 资源下载工具
# 上游项目地址：https://github.com/happycola233/tchMaterial-parser
# 本分支（Windows 7 专用）：https://github.com/Minecraftgoose/tchMaterial-parser-for-Windows7
# 作者：肥宅水水呀（https://space.bilibili.com/324042405）以及其他为本工具作出贡献的用户

from __future__ import annotations
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tchMaterial-parser-for-Windows7") # 已 pip install 时从包元数据读取
except PackageNotFoundError:
    # 源码直接运行（未 pip install）时没有包元数据，退回硬编码版本号，避免导入即崩溃。
    # 改动版本号时记得同步 pyproject.toml 里的 version。
    __version__ = "1.0"
