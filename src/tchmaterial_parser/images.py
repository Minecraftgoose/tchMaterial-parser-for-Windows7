# -*- coding: utf-8 -*-
# 图像相关的处理：图标绘制与封面适配
# 本分支不使用系统 Emoji 字体：Windows 7 没有 seguiemj.ttf（Segoe UI Emoji 随 Windows 8 引入），
# 自带的 seguisym.ttf（Segoe UI Symbol）只有单色字形，因此一律改用 assets 中的 Fluent Emoji 3D PNG。

from __future__ import annotations

from typing import Literal
from PIL import Image, ImageOps

from .platform_utils import resource_path

# 图标名称到 assets 中 PNG 文件名的映射，均为 256×256 的 Microsoft Fluent Emoji 3D 图
ICON_FILES = {
    "system": "last_quarter_moon_3d.png",
    "light": "sun_3d.png",
    "dark": "crescent_moon_3d.png",
    "about": "information_3d.png",
    "pin": "pushpin_3d.png",
    "link": "link_3d.png",
    "download": "inbox_tray_3d.png",
}

def make_icon_image(icon_name: Literal["system", "light", "dark", "about", "pin", "link", "download"], icon_size: int) -> Image.Image: # 读取图标 PNG 并按目标尺寸缩放
    with Image.open(resource_path("assets", ICON_FILES[icon_name])) as icon:
        icon_image = icon.copy()
    icon_image.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
    return icon_image

def fit_cover_image(image: Image.Image, size: tuple[int, int]) -> Image.Image: # 按原始比例将封面居中放进透明画布
    cover = ImageOps.exif_transpose(image).convert("RGBA")
    cover.thumbnail(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(cover, ((size[0] - cover.width) // 2, (size[1] - cover.height) // 2))
    return canvas
