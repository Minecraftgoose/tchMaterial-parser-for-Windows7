from __future__ import annotations
import unittest

from src.tchmaterial_parser.api import ResourceInfo
from src.tchmaterial_parser.ui.download_panel import collect_parsed_resources, parse_urls_in_background


def make_resource(url: str, title: str = "资源") -> ResourceInfo:
    return ResourceInfo(title, url, "pdf", [])


class CollectParsedResourcesTest(unittest.TestCase):
    def test_callback_annotations_stay_unevaluated(self) -> None:
        # 本分支运行在 Python 3.8，而注解里写的是 list[...] / X | None 这类新语法。
        # 上游的这条用例是调用 get_type_hints() 显式求值注解，那在 3.8 上必然抛错，
        # 因此这里改为断言相反的不变量：注解必须始终以字符串形式保留、永不在运行时求值。
        for func in (collect_parsed_resources, parse_urls_in_background):
            self.assertTrue(func.__annotations__, f"{func.__name__} 应当带有注解")
            for name, annotation in func.__annotations__.items():
                self.assertIsInstance(
                    annotation, str,
                    f"{func.__name__} 的 {name} 注解应为字符串（需依赖 from __future__ import annotations），实际为 {annotation!r}",
                )

    def test_flattens_multiple_resources_per_url(self) -> None:
        def fake_parse(url: str, bookmarks: bool):
            return [make_resource("https://example.com/a.pdf"), make_resource("https://example.com/b.mp3")]

        resources, failed = collect_parsed_resources(fake_parse, ["https://example.com/1"], False)

        self.assertEqual([resource.url for resource in resources], ["https://example.com/a.pdf", "https://example.com/b.mp3"])
        self.assertEqual(failed, set())

    def test_deduplicates_by_resource_url_across_urls(self) -> None:
        def fake_parse(url: str, bookmarks: bool):
            return [make_resource("https://example.com/a.pdf")]

        resources, failed = collect_parsed_resources(fake_parse, ["https://example.com/1", "https://example.com/2"], False)

        self.assertEqual([resource.url for resource in resources], ["https://example.com/a.pdf"])
        self.assertEqual(failed, set())

    def test_collects_urls_that_fail_to_parse(self) -> None:
        def fake_parse(url: str, bookmarks: bool):
            return None if url.endswith("bad") else [make_resource("https://example.com/a.pdf")]

        resources, failed = collect_parsed_resources(fake_parse, ["https://example.com/good", "https://example.com/bad"], False)

        self.assertEqual([resource.url for resource in resources], ["https://example.com/a.pdf"])
        self.assertEqual(failed, {"https://example.com/bad"})

    def test_reports_progress_for_each_url(self) -> None:
        def fake_parse(url: str, bookmarks: bool):
            return None

        progress: list[tuple[int, int]] = []

        collect_parsed_resources(fake_parse, ["https://example.com/1", "https://example.com/2", "https://example.com/3"], True, lambda current, total: progress.append((current, total)))

        self.assertEqual(progress, [(1, 3), (2, 3), (3, 3)])


if __name__ == "__main__":
    unittest.main()
