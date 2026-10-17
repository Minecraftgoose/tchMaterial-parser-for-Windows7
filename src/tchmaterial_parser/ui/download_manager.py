# -*- coding: utf-8 -*-
# 下载管理窗口：本次运行的全部下载任务、可对单个任务执行的操作，以及可复制的错误详情
# 所有 Tk 操作仅在主线程执行；本文件同步自上游 v4.4，仅做 Python 3.8 语法适配

from __future__ import annotations

import os
import subprocess
import time
import tkinter as tk
from tkinter import ttk

from . import download_panel as panel, theme
from .runtime import scaled
from .token_window import show_access_token_window
from .widgets import bind_context_menu, bind_tab_navigation, center_window
from ..platform_utils import os_name, print_error

def task_group(state: dict) -> str:
    if not state["finished"]:
        return "active"
    if state["failed_reason"] or state.get("stopped"):
        return "attention"
    return "complete"

def task_progress(state: dict) -> str:
    status = panel.task_status(state)
    if status == "已完成":
        return "100%"
    if status == "已存在" or state.get("kind") == "parse":
        return "—"
    if state["total_size"]:
        percent = min(100, state["downloaded_size"] * 100 / state["total_size"])
        return f"{percent:.1f}%"
    return "大小未知" if state["downloaded_size"] or status == "下载中" else "—"

def task_size(state: dict) -> str:
    if state.get("kind") == "parse" or state.get("skipped"):
        return "—"
    received = panel.format_bytes(state["downloaded_size"])
    return f"{received} / {panel.format_bytes(state['total_size'])}" if state["total_size"] else received

def task_speed(state: dict) -> str:
    if state["finished"] or state.get("phase") != "下载中":
        return "—"
    if time.monotonic() - state.get("last_received", 0) > 3:
        return "等待数据"
    speed = state.get("speed", 0)
    return f"{panel.format_bytes(speed)}/s" if speed else "计算中"

def task_details(state: dict) -> str:
    lines = [state["title"], f"状态：{panel.task_status(state)}"]
    if state["failed_reason"]:
        lines.append(state["failed_reason"])
    elif state.get("stopped"):
        lines.append("任务已停止，未完成的临时文件已删除。重新下载将从头开始。")
    elif state.get("skipped"):
        lines.append("保存位置已有同名文件，本次未覆盖。")
    elif state.get("cancel") and state["cancel"].is_set():
        lines.append("正在结束当前请求并清理临时文件。若服务器暂未响应，需等待请求超时。")
    lines.append("")
    if state["save_path"]:
        lines.append(f"保存位置：{state['save_path']}")
    lines.append(f"{'页面' if state.get('kind') == 'parse' else '资源'}链接：{state['download_url']}")
    if state.get("attempt", 1) > 1:
        lines.append(f"下载次数：{state['attempt']}")
    if state.get("error_details"):
        lines.extend(("", "技术详情：", state["error_details"]))
    return panel.redact_access_token("\n".join(lines))

class DownloadManager:
    def __init__(self, parent: tk.Tk) -> None:
        self.window = tk.Toplevel(parent)
        self.window.title("下载管理")
        self.window.geometry(f"{min(scaled(980), parent.winfo_screenwidth() - scaled(60))}x{min(scaled(690), parent.winfo_screenheight() - scaled(100))}")
        self.window.minsize(scaled(720), scaled(540))
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)
        self.window.bind("<Escape>", lambda _event: self.window.withdraw())
        self.window.bind("<Destroy>", self._destroyed, add="+")
        self.rows: dict[str, dict] = {}
        self.row_values: dict[str, tuple] = {}
        self.visible_ids: tuple[str, ...] = ()
        self.details_value = None
        self.group = tk.StringVar(value="all")
        self.query = tk.StringVar()

        content = ttk.Frame(self.window, padding=scaled(20))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)
        content.rowconfigure(3, weight=1)

        header = ttk.Frame(content)
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text="下载管理", style="Title.TLabel").pack(side="left")
        self.stop_all = ttk.Button(header, text="停止全部", command=self._stop_all)
        self.stop_all.pack(side="right")
        self.retry_all = ttk.Button(header, text="重试失败项", command=self._retry_all)
        self.retry_all.pack(side="right", padx=scaled(8))

        summary = ttk.Frame(content, style="Card.TFrame", padding=scaled(14))
        summary.grid(row=1, column=0, sticky="ew", pady=(scaled(14), scaled(12)))
        summary.columnconfigure(0, weight=1)
        self.summary = ttk.Label(summary, style="DownloadSummary.TLabel")
        self.summary.grid(row=0, column=0, sticky="ew")
        self.overall = ttk.Progressbar(summary)
        self.overall.grid(row=1, column=0, sticky="ew", pady=scaled(8))

        filters = ttk.Frame(content)
        filters.grid(row=2, column=0, sticky="ew", pady=(0, scaled(10)))
        self.filters = {}
        for value, label in (("all", "全部"), ("active", "进行中"), ("attention", "需处理"), ("complete", "已完成")):
            button = ttk.Radiobutton(filters, text=label, value=value, variable=self.group, command=self.refresh)
            button.pack(side="left", padx=(0, scaled(4)))
            self.filters[value] = (button, label)
        ttk.Button(filters, text="清空", width=4, command=lambda: self.query.set("")).pack(side="right")
        self.search = ttk.Entry(filters, textvariable=self.query, width=18)
        self.search.pack(side="right", padx=scaled(6))
        ttk.Label(filters, text="搜索", style="Caption.TLabel").pack(side="right")
        self.query.trace_add("write", lambda *_args: self.refresh())

        table = ttk.Frame(content)
        table.grid(row=3, column=0, sticky="nsew")
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(table, columns=("status", "progress", "size", "speed"), style="Download.Treeview", selectmode="extended", height=8)
        self.tree.heading("#0", text="资源名称", anchor="w")
        self.tree.column("#0", width=scaled(300), minwidth=scaled(160))
        for key, label, width in (("status", "状态", 100), ("progress", "进度", 85), ("size", "已接收 / 总大小", 190), ("speed", "速度", 105)):
            self.tree.heading(key, text=label, anchor="w")
            self.tree.column(key, width=scaled(width), minwidth=scaled(width), stretch=False, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(table, command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.bind("<<TreeviewSelect>>", lambda _event: self._selection_changed())
        self.tree.bind("<Control-a>", self._select_all)
        self.tree.bind("<Command-a>" if os_name == "Darwin" else "<Control-A>", self._select_all)
        self.tree.bind("<Double-1>", self._double_click)
        self.empty = ttk.Label(table, text="", anchor="center", justify="center", style="DownloadEmpty.TLabel")

        detail = ttk.Frame(content)
        detail.grid(row=4, column=0, sticky="ew", pady=(scaled(12), 0))
        detail.columnconfigure(0, weight=1)
        self.selection_label = ttk.Label(detail, text="任务详情", style="Heading.TLabel")
        self.selection_label.grid(row=0, column=0, sticky="w", pady=(0, scaled(8)))
        actions = ttk.Frame(detail)
        actions.grid(row=1, column=0, sticky="ew", pady=(0, scaled(8)))
        self.retry = ttk.Button(actions, text="重新下载", style=theme.ACCENT_BUTTON_STYLE, command=self._retry_selected)
        self.retry.pack(side="left")
        self.stop = ttk.Button(actions, text="停止任务", command=self._stop_selected)
        self.stop.pack(side="left", padx=scaled(6))
        self.folder = ttk.Button(actions, text="打开文件夹", command=self._open_folder)
        self.folder.pack(side="left")
        self.copy = ttk.Button(actions, text="复制详情", command=self._copy_details)
        self.copy.pack(side="left", padx=scaled(6))
        self.token = ttk.Button(actions, text="设置 Token", command=show_access_token_window)
        self.token.pack(side="right")
        text_frame = ttk.Frame(detail, style="Card.TFrame", padding=scaled(8))
        text_frame.grid(row=2, column=0, sticky="ew")
        text_frame.columnconfigure(0, weight=1)
        self.details = tk.Text(text_frame, height=4, wrap="word", font="AppBodyFont", state="disabled")
        self.details.grid(row=0, column=0, sticky="ew")
        scroll = ttk.Scrollbar(text_frame, command=self.details.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.details.configure(yscrollcommand=scroll.set)
        theme.register_themed_widget(self.details)
        bind_context_menu(self.details, "readonly")
        bind_tab_navigation(self.details)

        footer = ttk.Frame(content)
        footer.grid(row=5, column=0, sticky="ew", pady=(scaled(10), 0))
        self.hint = ttk.Label(footer, text="记录保留至退出程序 · 关闭此窗口后，下载仍会继续", style="Caption.TLabel")
        self.hint.grid(row=0, column=0, sticky="w")
        footer.columnconfigure(0, weight=1)
        self.clear = ttk.Button(footer, text="清除已完成记录", command=self._clear_completed)
        self.clear.grid(row=0, column=1, sticky="e")
        theme.on_theme_applied(self._apply_theme)
        self._apply_theme()
        self.refresh()
        center_window(self.window, parent)

    def _destroyed(self, event: tk.Event) -> None:
        if event.widget == self.window and self._apply_theme in theme.theme_actions:
            theme.theme_actions.remove(self._apply_theme)

    def _apply_theme(self) -> None:
        style = ttk.Style(self.window)
        colors = theme.current_colors
        style.configure("Download.Treeview", font="AppBodyFont", background=colors["surface"], fieldbackground=colors["surface"], rowheight=scaled(34))
        # 替换主题中每列独立的按钮贴图，保留原生表头的列宽拖动与横向滚动。
        if "DownloadHeading.cell" not in style.element_names():
            style.element_create("DownloadHeading.cell", "from", "default", "Treeheading.cell")
        style.layout("Download.Treeview.Heading", [
            ("DownloadHeading.cell", {"sticky": "nswe"}),
            ("Treeheading.padding", {"sticky": "nswe", "children": [
                ("Treeheading.text", {"sticky": "we"}),
            ]}),
        ])
        style.configure(
            "Download.Treeview.Heading", font="AppStrongFont", foreground=colors["muted"],
            background=colors["page"], padding=(scaled(10), scaled(9)),
        )
        style.configure("DownloadEmpty.TLabel", font="AppBodyFont", foreground=colors["muted"], background=colors["surface"])
        style.configure("DownloadSummary.TLabel", font="AppStrongFont", background=colors["surface"])
        dark = theme.current_theme == "dark"
        self.tree.tag_configure("attention", foreground="#ffb4a9" if dark else "#a52a20")
        self.tree.tag_configure("complete", foreground=colors["muted"])
        self.tree.tag_configure("active", foreground=colors["fg"])
        theme.apply_titlebar_theme(self.window)

    def show(self) -> None:
        self.window.deiconify()
        self.window.lift()
        self.refresh()

    def refresh(self) -> None:
        states = list(panel.download_states)
        self.rows = {str(id(state)): state for state in states}
        counts = {group: sum(task_group(state) == group for state in states) for group in ("active", "attention", "complete")}
        counts["all"] = len(states)
        for group, (button, label) in self.filters.items():
            button.config(text=f"{label} {counts[group]}")
        self.summary.config(text=panel.download_summary(states) if states else "还没有下载任务")
        self.overall.config(value=100 * sum(state["finished"] for state in states) / len(states) if states else 0)
        query = self.query.get().strip().casefold()
        visible = tuple(key for key, state in self.rows.items()
                        if (self.group.get() == "all" or task_group(state) == self.group.get())
                        and (not query or query in panel.redact_access_token(f"{state['title']} {state['save_path']} {state['download_url']}").casefold()))
        # 只更新变化的行；筛选时保留已有条目，避免高频刷新打断选择与滚动。
        for key in self.row_values.keys() - self.rows.keys():
            self.tree.delete(key)
            del self.row_values[key]
        for key in visible:
            state = self.rows[key]
            values = (panel.redact_access_token(state["title"]), panel.task_status(state), task_progress(state), task_size(state), task_speed(state), task_group(state))
            if key not in self.row_values:
                self.tree.insert("", "end", iid=key)
            if self.row_values.get(key) != values:
                self.tree.item(key, text=values[0], values=values[1:5], tags=(values[5],))
                self.row_values[key] = values
        if visible != self.visible_ids:
            self.tree.set_children("", *visible)
            selected = [key for key in self.tree.selection() if key in visible]
            self.tree.selection_set(selected)
            if not selected and visible:
                self.tree.selection_set(visible[0])
                self.tree.focus(visible[0])
            self.visible_ids = visible
        if visible:
            self.empty.place_forget()
        else:
            self.empty.config(text="还没有下载任务\n在主界面选择资源后点击“下载”。" if not states else "没有匹配的任务\n试试其他分类或清空搜索。")
            self.empty.place(relx=0.5, rely=0.45, anchor="center")
        busy = panel.downloads_active()
        self.stop_all.config(state="normal" if counts["active"] else "disabled")
        self.retry_all.config(state="normal" if not busy and any(state["failed_reason"] and state.get("kind") != "parse" for state in states) else "disabled")
        self.clear.config(state="normal" if counts["complete"] else "disabled")
        self._selection_changed()

    def _selected(self) -> list[dict]:
        return [self.rows[key] for key in self.tree.selection() if key in self.rows and key in self.visible_ids]

    def _selection_changed(self) -> None:
        states = self._selected()
        busy = panel.downloads_active()
        parse_only = bool(states) and all(state.get("kind") == "parse" for state in states)
        retryable = any(state["finished"] and (state["failed_reason"] or state.get("stopped")) for state in states)
        retry_text = "任务结束后重试" if retryable and busy else "重新解析" if parse_only else "重新下载"
        self.retry.config(text=retry_text, state="normal" if retryable and not busy and (parse_only or all(state.get("kind") != "parse" for state in states)) else "disabled")
        self.stop.config(state="normal" if any(not state["finished"] and not state["cancel"].is_set() for state in states) else "disabled")
        self.folder.config(state="normal" if len(states) == 1 and states[0]["save_path"] else "disabled")
        self.copy.config(state="normal" if states else "disabled")
        self.selection_label.config(text=f"任务详情 · 已选 {len(states)} 项" if states else "任务详情")
        # 多选时仅预览第一项，复制操作会包含全部所选任务。
        value = task_details(states[0]) if states else "选择一个任务，查看保存位置、下载状态和错误详情。"
        if value != self.details_value:
            self.details.config(state="normal")
            self.details.delete("1.0", "end")
            self.details.insert("1.0", value)
            self.details.config(state="disabled")
            self.details_value = value

    def _select_all(self, _event=None) -> str:
        self.tree.selection_set(self.visible_ids)
        return "break"

    def _double_click(self, event: tk.Event) -> None:
        if self.tree.identify_region(event.x, event.y) in ("tree", "cell"):
            self._open_folder()

    def _retry_selected(self) -> None:
        states = self._selected()
        if states and all(state.get("kind") == "parse" for state in states):
            panel.download([state["download_url"] for state in states])
        else:
            panel.retry_tasks(states)
        self.refresh()

    def _retry_all(self) -> None:
        panel.retry_tasks([state for state in panel.download_states if state["failed_reason"]])
        self.refresh()

    def _stop_selected(self) -> None:
        panel.stop_tasks(self._selected())
        self.refresh()

    def _stop_all(self) -> None:
        panel.stop_downloads()
        self.refresh()

    def _clear_completed(self) -> None:
        panel.download_states[:] = [state for state in panel.download_states if task_group(state) != "complete"]
        panel.refresh_download_progress()
        self.hint.config(text="已清除完成记录，下载的文件仍保留。")
        self.refresh()

    def _copy_details(self) -> None:
        value = "\n\n".join(task_details(state) for state in self._selected())
        if value:
            self.window.clipboard_clear()
            self.window.clipboard_append(value)
            self.hint.config(text="所选任务的详情已复制。")

    def _open_folder(self) -> None:
        states = self._selected()
        if len(states) != 1 or not states[0]["save_path"]:
            return
        directory = os.path.dirname(os.path.abspath(states[0]["save_path"]))
        # 尚未创建分类子目录时，打开最近的现有父目录。
        while not os.path.isdir(directory):
            parent = os.path.dirname(directory)
            if parent == directory:
                self.hint.config(text="保存位置已不可用，请查看任务详情。")
                return
            directory = parent
        try:
            if os_name == "Windows":
                os.startfile(directory)
            else:
                subprocess.Popen(["open" if os_name == "Darwin" else "xdg-open", directory])
        except OSError as error:
            print_error(RuntimeError(panel.redact_access_token(str(error))))
            self.hint.config(text="无法打开文件夹，请从详情中复制保存位置。")
