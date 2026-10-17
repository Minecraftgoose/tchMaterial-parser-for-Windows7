from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr

from src.tchmaterial_parser.platform_utils import os_name, print_error, resource_path


class PrintErrorTest(unittest.TestCase):
    def test_prints_without_raising(self) -> None:
        # Python 3.8 的 traceback.print_exception(etype, value, tb) 三个位置参数全部必填，
        # 3.10 起才允许只传异常对象。写成 print_exception(e) 在 3.10 上正常、在 3.8 上抛 TypeError，
        # 而 print_error 正被下载流程用来记录失败原因，一旦抛错就会把真实的下载错误一起吞掉。
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            print_error(RuntimeError("boom"))
        self.assertIn("boom", buffer.getvalue())

    def test_keeps_traceback(self) -> None:
        buffer = io.StringIO()
        try:
            raise ValueError("inner")
        except ValueError as error:
            with redirect_stderr(buffer):
                print_error(error)
        output = buffer.getvalue()
        self.assertIn("Traceback", output)
        self.assertIn("ValueError: inner", output)

    def test_silent_when_stderr_is_missing(self) -> None:
        # 无控制台运行时 sys.stderr 可能为 None，此时不应抛错
        original = sys.stderr
        sys.stderr = None
        try:
            print_error(RuntimeError("boom"))
        finally:
            sys.stderr = original


class PlatformTest(unittest.TestCase):
    def test_os_name_is_windows(self) -> None:
        # 本分支只支持 Windows 7，同步自上游的模块靠它做分支判断，不能退化成运行时探测
        self.assertEqual(os_name, "Windows")

    def test_resource_path_is_inside_package(self) -> None:
        self.assertTrue(str(resource_path("assets", "sun_3d.png")).replace("\\", "/").endswith("tchmaterial_parser/assets/sun_3d.png"))
