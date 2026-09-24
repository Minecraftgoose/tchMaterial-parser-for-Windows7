# -*- coding: utf-8 -*-
# 浅色／深色主题：配色常量、命名字体、系统主题探测与主题应用

from __future__ import annotations
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
import tkinter.font as tkfont
from typing import Literal
import sv_ttk # Sun Valley（Windows 11 风格）主题

from . import runtime
from .runtime import scaled
from ..platform_utils import print_error

switched_theme = "system" # 选择的主题
current_theme = "light" # 当前主题，若 switched_theme 为 `system` 则 current_theme 为系统主题（`light` 或 `dark`）
current_colors: dict[str, str] = {} # 当前主题的配色，在 apply_theme() 中填充
themed_widgets: set[tk.Widget] = set() # 当前仍存在且需要跟随主题调整配色的 tk 原生控件
theme_actions: list[Callable[[], None]] = [] # 主题应用后需要额外执行的回调（如重建跟随主题的图片资源）

def on_theme_applied(action: Callable[[], None]) -> None: # 登记回调，在每次 apply_theme() 末尾执行
    theme_actions.append(action)

# 主题配色，surface 为 sv-ttk 卡片贴图的填充色，须与之一致，否则卡片内会出现色差；
# page 比 surface 略深，用作页面底色，让卡片、列表、文本框显出层次
THEME_COLORS = {
    "light": { "page": "#f2f2f2", "surface": "#fafafa", "fg": "#1c1c1c", "muted": "#5d5d5d", "selbg": "#2f60d8", "selfg": "#ffffff" },
    "dark": { "page": "#141414", "surface": "#1c1c1c", "fg": "#fafafa", "muted": "#a0a0a0", "selbg": "#2f60d8", "selfg": "#ffffff" },
}

ACCENT_BUTTON_STYLE = "Accent.TButton"
SWITCH_STYLE = "Switch.TCheckbutton"

# 本程序使用的命名字体，格式为 字体名称: (基准字号（像素）, 是否加粗, 是否添加下划线)
APP_FONTS = {
    "AppCaptionFont": (12, False, False), "AppBodyFont": (14, False, False), "AppStrongFont": (14, True, False),
    "AppTitleFont": (20, True, False), "AppLinkFont": (14, False, True)
}
# sv-ttk 内置的命名字体，需要一并改为中文字体（其默认字体不含中文字形），基准字号与 sv-ttk 原始取值保持一致
SV_FONTS = {
    "SunValleyCaptionFont": (12, False, False), "SunValleyBodyFont": (14, False, False),
    "SunValleyBodyStrongFont": (14, True, False), "SunValleyBodyLargeFont": (18, False, False),
    "SunValleySubtitleFont": (20, True, False), "SunValleyTitleFont": (28, True, False),
    "SunValleyTitleLargeFont": (40, True, False), "SunValleyDisplayFont": (68, True, False),
}

def bind_font_family(family: str) -> None: # 由 app.py 在选定界面字体后写入，供 setup_fonts() 使用
    global ui_font_family
    ui_font_family = family

def pick_ui_font_family() -> str: # 选择一个合适的字体
    try:
        available = set(tkfont.families(runtime.root)) # 获取所有字体的列表
    except Exception:
        return "TkDefaultFont"

    # Windows 7 只有 “微软雅黑”，没有 “Microsoft YaHei UI”（后者随 Windows 8 引入）
    for name in ("微软雅黑", "Microsoft YaHei", "Microsoft YaHei UI", "SimSun"): # 在这些字体中选择一个可用的字体
        if name in available:
            return name

    try: # 若上述字体都不可用，则返回默认字体
        return tkfont.nametofont("TkDefaultFont").actual("family")
    except Exception:
        return "TkDefaultFont"

def setup_fonts() -> None: # 创建（或更新）所有命名字体，使其使用中文字体并跟随缩放因子
    # 此处直接调用 Tcl 命令而不使用 tkinter.font.Font，因为后者创建的字体会随 Python 对象被垃圾回收而一并删除
    existing_fonts: tuple[str, ...] = runtime.root.tk.splitlist(runtime.root.tk.call("font", "names"))
    for name, (size, bold, underline) in { **APP_FONTS, **SV_FONTS }.items():
        # 字号取负值表示以像素为单位，从而避开 tk scaling 的二次缩放，与 sv-ttk 的取值方式保持一致
        options = (
            "-family", ui_font_family,
            "-size", -scaled(size),
            "-weight", "bold" if bold else "normal",
            "-underline", 1 if underline else 0,
        )
        runtime.root.tk.call("font", "configure" if name in existing_fonts else "create", name, *options)

def detect_system_theme() -> Literal["light", "dark"]: # 获取系统当前使用的是浅色还是深色模式
    # Windows 7 没有系统级的浅色/深色模式开关（注册表的 AppsUseLightTheme 自 Windows 10 才存在），
    # 因此跟随系统时一律按浅色模式处理，用户仍可点右上角的按钮手动切到深色
    return "light"

def register_themed_widget(widget: tk.Widget) -> None: # 登记需要跟随主题手动调整配色的 tk 原生控件（ttk 控件由主题自动处理），并立即应用当前配色
    themed_widgets.add(widget)
    widget.bind("<Destroy>", lambda _event: themed_widgets.discard(widget), add="+")
    apply_widget_theme(widget)

def apply_widget_theme(widget: tk.Widget) -> None: # 为单个 tk 原生控件应用当前主题配色
    if isinstance(widget, tk.Menu):
        widget.configure(
            background=current_colors["page"], foreground=current_colors["fg"],
            activebackground=current_colors["selbg"], activeforeground=current_colors["selfg"],
            relief="flat",
        )
    elif isinstance(widget, tk.Text):
        widget.configure(
            background=current_colors["surface"], foreground=current_colors["fg"],
            insertbackground=current_colors["fg"], selectbackground=current_colors["selbg"],
            selectforeground=current_colors["selfg"], borderwidth=0, relief="flat", highlightthickness=0,
        )

def apply_theme(theme: Literal["system", "light", "dark"]) -> None: # 应用浅色/深色主题
    global switched_theme, current_theme, current_colors
    switched_theme = theme if theme in ("system", "light", "dark") else "system"
    current_theme = theme if theme in THEME_COLORS else detect_system_theme()
    current_colors = THEME_COLORS[current_theme]

    sv_ttk.set_theme(current_theme, runtime.root)
    # sv-ttk 把配色函数绑定在 <<ThemeChanged>> 事件上，但一来该事件不会送达尚无 ttk 子控件的根窗口（首次启动时配色不生效），
    # 二来后面每次调用 ttk::style configure 都会重新触发该事件，从而把下面的自定义配色覆盖回去，因此解绑它，改为在此显式调用一次
    runtime.root.unbind_class("Tk", "<<ThemeChanged>>")
    runtime.root.tk.call("configure_colors")

    setup_fonts() # sv-ttk 会在首次加载主题时创建自己的命名字体，因此字体要在其之后设置
    style = ttk.Style(runtime.root)

    # 切换主题会重置以下自定义样式，因此每次应用主题时都要重新设置
    style.configure(".", font="AppBodyFont", background=current_colors["page"])
    style.configure("Title.TLabel", font="AppTitleFont")
    style.configure("Heading.TLabel", font="AppStrongFont")
    style.configure("Caption.TLabel", font="AppCaptionFont", foreground=current_colors["muted"])
    style.configure("Description.TLabel", font="AppBodyFont", foreground=current_colors["muted"], background=current_colors["surface"]) # 该样式用于卡片内的文字，背景需与卡片一致
    style.configure("Custom.Treeview", font="AppBodyFont", background=current_colors["surface"], rowheight=scaled(38))
    button_padding = (scaled(10), scaled(4)) # 增加纵向留白，使按钮在各 DPI 下保持接近 Win11 的紧凑比例
    style.configure("TButton", padding=button_padding)
    style.configure("Accent.TButton", padding=button_padding)

    for widget in themed_widgets:
        apply_widget_theme(widget)

    for action in theme_actions: # 重建跟随主题的图片等资源
        try:
            action()
        except Exception as e:
            print_error(e)
