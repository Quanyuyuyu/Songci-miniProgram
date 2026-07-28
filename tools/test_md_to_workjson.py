# -*- coding: utf-8 -*-
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from md_to_workjson import CompileError, REPO_ROOT, compile_markdown, discover_markdown


class MarkdownCompilerTest(unittest.TestCase):
    def test_compiles_sections_and_local_image(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            root = Path(raw_temp)
            image = root / "images" / "sample.jpg"
            image.parent.mkdir()
            image.write_bytes(b"sample-image")
            manuscript = root / "essay-99.md"
            manuscript.write_text(
                """---
title: 测试词笺
form_tag: 文字
term: 2026春
collecting: false
summary: 测试摘要
---

# 起笔

## 小题

正文一段。

*拍摄信息：测试地点 · 测试设备*

> 引文第一行
> 引文第二行

![题注](images/sample.jpg)
""",
                encoding="utf-8",
            )
            output_images = root / "compiled-images"
            document = compile_markdown(manuscript, output_images)

            self.assertEqual(document["id"], "essay-99")
            self.assertEqual(
                [item["type"] for item in document["sections"]],
                ["h", "h", "p", "note", "quote", "img"],
            )
            self.assertEqual(document["sections"][0]["level"], 1)
            self.assertEqual(document["sections"][1]["level"], 2)
            self.assertEqual(document["sections"][3]["text"], "拍摄信息：测试地点 · 测试设备")
            self.assertEqual(document["sections"][4]["text"], "引文第一行\n引文第二行")
            self.assertEqual(document["image_urls"], ["/images/works/essay-99/sample.jpg"])
            self.assertTrue((output_images / "essay-99" / "sample.jpg").is_file())

    def test_rejects_http_and_path_traversal(self) -> None:
        for url in ("http://example.com/a.jpg", "../outside.jpg"):
            with self.subTest(url=url), tempfile.TemporaryDirectory() as raw_temp:
                manuscript = Path(raw_temp) / "photo-99.md"
                manuscript.write_text(
                    f"---\ntitle: x\nform_tag: 摄影\n---\n\n![x]({url})\n",
                    encoding="utf-8",
                )
                with self.assertRaises(CompileError):
                    compile_markdown(manuscript, Path(raw_temp) / "output", copy_images=False)

    def test_repository_has_39_complete_manuscripts(self) -> None:
        paths = discover_markdown(REPO_ROOT / "data" / "works_src")
        self.assertEqual(len(paths), 39)
        for path in paths:
            document = compile_markdown(path, copy_images=False)
            self.assertFalse(document["collecting"], path.name)
            self.assertTrue(document["sections"], path.name)


if __name__ == "__main__":
    unittest.main()
