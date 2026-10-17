from __future__ import annotations
from contextlib import ExitStack
from pathlib import Path
import subprocess
import sys
import threading
import tkinter as tk
from unittest.mock import Mock, patch
import unittest

import pytest

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.tchmaterial_parser.ui import download_panel as panel, runtime, theme
from src.tchmaterial_parser.ui.download_manager import DownloadManager


class DownloadManagerUITest(unittest.TestCase):
    __test__ = False

    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            if "no display name" in str(error) or "couldn't connect to display" in str(error):
                self.skipTest(str(error))
            raise
        self.addCleanup(self.root.destroy)
        self.root.withdraw()
        self.context = ExitStack()
        self.addCleanup(self.context.close)
        enter = self.context.enter_context
        enter(patch.object(runtime, "root", self.root, create=True))
        enter(patch.object(runtime, "ui_scale", 1.0))
        enter(patch.object(runtime, "app_closing", False))
        enter(patch.object(theme, "ui_font_family", "TkDefaultFont", create=True))
        for name, value in (("theme_actions", []), ("themed_widgets", set()), ("current_colors", {}), ("current_theme", "light"), ("switched_theme", "light")):
            enter(patch.object(theme, name, value))
        for name, value in (("download_states", []), ("_batch_running", False), ("_parsing_download", False), ("_stop_requested", threading.Event())):
            enter(patch.object(panel, name, value))
        for name in ("progress_label", "download_progress_bar", "download_btn"):
            enter(patch.object(panel, name, Mock(), create=True))
        theme.apply_theme("light")
        self.errors = []
        self.root.report_callback_exception = lambda _type, error, _traceback: self.errors.append(error)
        self.manager = DownloadManager(self.root)
        self.manager.window.withdraw()
        self.addCleanup(self.manager.window.destroy)
        self.root.update()

    def tearDown(self):
        self.assertEqual(self.errors, [])

    def task(self, title, **kwargs):
        state = panel.create_download_state(f"https://example.com/{title}", f"/downloads/{title}.pdf")
        state.update(kwargs)
        panel.download_states.append(state)
        return state

    def refresh(self):
        self.manager.refresh()
        self.root.update()

    def select(self, *states):
        self.manager.tree.selection_set([str(id(state)) for state in states])
        self.root.update()

    def test_empty_state_and_disabled_actions(self):
        self.assertEqual(self.manager.tree.get_children(), ())
        self.assertEqual(str(self.manager.details.cget("state")), "disabled")
        for button in (self.manager.retry, self.manager.stop, self.manager.copy, self.manager.folder, self.manager.stop_all, self.manager.clear):
            self.assertTrue(button.instate(["disabled"]))

    def test_search_filter_and_refresh_preserve_selection(self):
        first = self.task("数学", phase="下载中", downloaded_size=50, total_size=100)
        second = self.task("语文", finished=True, failed_reason="HTTP 403")
        self.refresh()
        self.select(second)
        first["downloaded_size"] = 90
        self.refresh()
        self.assertEqual(self.manager.tree.selection(), (str(id(second)),))
        self.manager.group.set("attention")
        self.refresh()
        self.assertEqual(self.manager.tree.get_children(), (str(id(second)),))
        self.manager.query.set("不存在")
        self.assertEqual(self.manager.tree.get_children(), ())
        self.assertTrue(self.manager.retry.instate(["disabled"]))
        self.manager.query.set("语文")
        self.manager.group.set("all")
        self.refresh()
        self.assertEqual(self.manager.tree.get_children(), (str(id(second)),))
        self.manager.query.set("")
        self.assertEqual(len(self.manager.tree.get_children()), 2)

    def test_selected_stop_does_not_cancel_other_tasks(self):
        first = self.task("数学")
        second = self.task("语文")
        self.refresh()
        self.select(second)
        self.manager.stop.invoke()
        self.assertFalse(first["cancel"].is_set())
        self.assertTrue(second["cancel"].is_set())
        self.assertIn("正在停止", self.manager.details.get("1.0", "end"))

    def test_copy_multiple_failures_and_readonly_scrolling(self):
        first = self.task("数学", finished=True, failed_reason="长错误\n" * 100)
        second = self.task("语文", finished=True, failed_reason="HTTP 403")
        self.refresh()
        self.select(first, second)
        self.manager.copy.invoke()
        copied = self.root.clipboard_get()
        self.assertIn("数学", copied)
        self.assertIn("语文", copied)
        text = self.manager.details.get("1.0", "end")
        self.manager.details.insert("1.0", "should not appear")
        self.assertEqual(self.manager.details.get("1.0", "end"), text)
        self.manager.details.yview_moveto(0.8)
        position = self.manager.details.yview()
        self.refresh()
        self.assertEqual(self.manager.details.yview(), position)

    def test_clear_complete_retains_failures_and_active_tasks(self):
        complete = self.task("完成", finished=True)
        failed = self.task("失败", finished=True, failed_reason="error")
        active = self.task("排队")
        self.refresh()
        self.select(complete)
        self.manager.clear.invoke()
        self.assertEqual(panel.download_states, [failed, active])
        self.assertFalse(self.manager.tree.exists(str(id(complete))))

    def test_parse_retry_uses_original_urls(self):
        state = self.task("页面", kind="parse", finished=True, failed_reason="无法解析")
        self.refresh()
        self.assertEqual(self.manager.retry.cget("text"), "重新解析")
        with patch.object(panel, "download") as download:
            self.manager.retry.invoke()
        download.assert_called_once_with([state["download_url"]])

    def test_theme_changes_and_minimum_layout(self):
        state = self.task("长资源名称" * 20, finished=True, failed_reason="HTTP 403\n" * 100)
        self.refresh()
        self.manager.window.geometry("720x540")
        self.manager.window.deiconify()
        self.root.update()
        for name in ("dark", "light"):
            theme.apply_theme(name)
            self.root.update_idletasks()
            self.assertEqual(self.manager.details.cget("background"), theme.current_colors["surface"])
            self.assertEqual(self.manager.tree.selection(), (str(id(state)),))
            for widget in (self.manager.retry, self.manager.token, self.manager.clear, self.manager.search):
                x = widget.winfo_rootx() - self.manager.window.winfo_rootx()
                y = widget.winfo_rooty() - self.manager.window.winfo_rooty()
                self.assertGreaterEqual(x, 0)
                self.assertGreaterEqual(y, 0)
                self.assertLessEqual(x + widget.winfo_width(), 720)
                self.assertLessEqual(y + widget.winfo_height(), 540)

    def test_close_reopen_preserves_tasks_and_selection(self):
        state = self.task("语文", phase="下载中", total_size=100, downloaded_size=42)
        self.refresh()
        close_command = self.manager.window.protocol("WM_DELETE_WINDOW")
        self.root.tk.call(close_command)
        self.assertFalse(state["cancel"].is_set())
        self.manager.show()
        self.assertEqual(self.manager.tree.selection(), (str(id(state)),))
        self.assertEqual(self.manager.tree.item(str(id(state)), "values")[1], "42.0%")

    def test_high_dpi_controls_stay_inside_window(self):
        runtime.ui_scale = 1.5
        theme.apply_theme("light")
        self.manager.window.destroy()
        self.manager = DownloadManager(self.root)
        self.manager.window.geometry("1080x810")
        self.root.update()
        for widget in (self.manager.retry, self.manager.token, self.manager.clear, self.manager.search):
            x = widget.winfo_rootx() - self.manager.window.winfo_rootx()
            y = widget.winfo_rooty() - self.manager.window.winfo_rooty()
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + widget.winfo_width(), 1080)
            self.assertLessEqual(y + widget.winfo_height(), 810)

    def test_large_list_refresh_does_not_rebuild_rows(self):
        for index in range(1000):
            self.task(str(index), finished=True, failed_reason="HTTP 404" if index % 2 else None)
        self.refresh()
        with patch.object(self.manager.tree, "insert", side_effect=AssertionError("重复创建行")):
            self.refresh()
            self.manager.group.set("attention")
            self.refresh()
            self.manager.group.set("all")
            self.refresh()
        self.assertEqual(len(self.manager.tree.get_children()), 1000)


@pytest.mark.parametrize("case", unittest.defaultTestLoader.getTestCaseNames(DownloadManagerUITest))
def test_download_manager_interaction(case):
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), case],
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )
    if result.returncode == 77:
        pytest.skip("当前环境没有图形显示服务，需在桌面环境或 Xvfb 中运行")
    assert result.returncode == 0, result.stdout + result.stderr


if __name__ == "__main__":
    result = unittest.TextTestRunner().run(unittest.TestSuite([DownloadManagerUITest(sys.argv[1])]))
    raise SystemExit(77 if result.skipped else int(not result.wasSuccessful()))
