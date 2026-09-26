# 图标资源说明

本目录存放图标的**源文件**与**打包时使用的图标**。其中 `logo.icns` 与 `icon.ico` 只在构建阶段使用；`window_icon.png`由程序在运行时读取，并通过 PyInstaller 的 `datas` 一并打包。

| 文件 | 用途 | 由谁使用 |
| --- | --- | --- |
| `logo.svg` | 矢量母版，修改图标时从这里改起 | 仅供设计使用，不参与构建 |
| `logo.png` | 1024×1024 位图母版，由 `logo.svg` 导出 | `logo.icns` 与 `icon.ico` 的生成来源 |
| `icon.ico` | Windows 可执行文件图标 | `tchMaterial-parser-for-Windows7.spec` 中的 `EXE(icon=...)` |
| `window_icon.png` | 程序运行时的窗口图标（窗口左上角、Alt+Tab，以及主界面标题旁） | `src/tchmaterial_parser/app.py` 直接读取，`tchMaterial-parser-for-Windows7.spec` 负责打包 |
| `last_quarter_moon_3d.png`、`sun_3d.png`、`crescent_moon_3d.png`、`information_3d.png`、`pushpin_3d.png`、`link_3d.png`、`inbox_tray_3d.png`（来自 [microsoft/fluentui-emoji](https://github.com/microsoft/fluentui-emoji)） | 程序右上角选择主题、关于图标，以及主界面功能说明的四行图标 | `src/tchmaterial_parser/images.py` 直接读取，`tchMaterial-parser-for-Windows7.spec` 负责打包 |
| `last_quarter_moon_flat.svg`、`sun_flat.svg`、`crescent_moon_flat.svg`、`information_flat.svg`（来自 [microsoft/fluentui-emoji](https://github.com/microsoft/fluentui-emoji)） | 矢量图 | 仅供设计使用，不参与构建 |
| `welcome_164x314.bmp` | 安装包左侧背景图 | 安装包 |

## 关于 Emoji 字体

Windows 7 没有 `seguiemj.ttf`（Segoe UI Emoji 随 Windows 8 引入），自带的 `seguisym.ttf` 只有单色字形。
因此本分支**不使用系统 Emoji 字体**，界面上所有图标都来自本目录的 3D PNG。

## 更换图标时的操作

修改 `logo.svg` 后，导出一份 1024×1024 的 `logo.png`，然后重新生成下列三个文件。

### 1. 重新生成 `icon.ico`

`icon.ico` 需要包含**多个尺寸**：Windows 在标题栏用 16×16，在桌面用 32×32，在「超大图标」视图下用 256×256。若只放单一尺寸，系统只能拉伸缩放，会明显模糊。

```python
from PIL import Image

Image.open("assets/logo.png").convert("RGBA").save(
    "assets/icon.ico",
    format="ICO",
    sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
)
```
