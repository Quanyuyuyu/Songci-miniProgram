# -*- coding: utf-8 -*-
from __future__ import annotations

import re
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
byline: 测试作者
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
            self.assertEqual(document["byline"], "测试作者")
            self.assertEqual(
                [item["type"] for item in document["sections"]],
                ["h", "h", "p", "note", "quote", "img"],
            )
            self.assertEqual(document["sections"][0]["level"], 1)
            self.assertEqual(document["sections"][1]["level"], 2)
            self.assertEqual(document["sections"][3]["text"], "拍摄信息：测试地点 · 测试设备")
            self.assertEqual(document["sections"][4]["text"], "引文第一行\n引文第二行")
            self.assertEqual(
                document["image_urls"],
                ["/packages/work-text/images/essay-99/sample.jpg"],
            )
            self.assertTrue(
                (output_images / "work-text" / "images" / "essay-99" / "sample.jpg").is_file()
            )

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

    def test_verbatim_mode_reflows_layout_without_rewriting_text(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            manuscript = Path(raw_temp) / "essay-99.md"
            body = """一、月下读词
这是被页面宽度截断的第一
行正文。

拍摄地点：校园

配词：“明月几时有”
"""
            manuscript.write_text(
                "---\ntitle: 测试\nform_tag: 文字\nverbatim: true\n---\n" + body,
                encoding="utf-8",
            )
            document = compile_markdown(manuscript, copy_images=False)
            self.assertEqual(
                [item["type"] for item in document["sections"]],
                ["h", "p", "note", "quote"],
            )
            self.assertTrue(all("\n" not in item.get("text", "") for item in document["sections"]))
            compiled = "".join(item.get("text", "") for item in document["sections"])
            self.assertEqual(re.sub(r"\s+", "", compiled), re.sub(r"\s+", "", body))

    def test_verbatim_mode_honors_explicit_markdown_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as raw_temp:
            manuscript = Path(raw_temp) / "essay-99.md"
            manuscript.write_text(
                """---
title: 测试
form_tag: 文字
verbatim: true
---
## 念奴娇

> 闹红一舸，记来时、尝与鸳鸯为侣。
>
> 日暮，青盖亭亭，情人不见。

*姜夔《念奴娇·闹红一舸》*
""",
                encoding="utf-8",
            )
            document = compile_markdown(manuscript, copy_images=False)
            self.assertEqual(
                [item["type"] for item in document["sections"]],
                ["h", "quote", "note"],
            )
            self.assertEqual(document["sections"][0]["text"], "念奴娇")
            self.assertIn("\n\n", document["sections"][1]["text"])
            self.assertEqual(document["sections"][2]["text"], "姜夔《念奴娇·闹红一舸》")

    def test_repository_has_44_complete_manuscripts(self) -> None:
        # essay-2《宋词中的夜晚——读书札记几则》应作者要求以匿名收录，byline 有意留空；
        # 其余作品必须有署名（不得出现真实姓名/学号，统一用笔名或雅号）。
        anonymous_ok = {"essay-2"}
        paths = discover_markdown(REPO_ROOT / "data" / "works_src")
        self.assertEqual(len(paths), 44)
        for path in paths:
            document = compile_markdown(path, copy_images=False)
            self.assertFalse(document["collecting"], path.name)
            self.assertTrue(document["byline"] or path.stem in anonymous_ok, path.name)
            self.assertTrue(document["sections"], path.name)


if __name__ == "__main__":
    unittest.main()
