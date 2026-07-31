# -*- coding: utf-8 -*-
"""Regression checks for the mini-program's unified reading content."""

from __future__ import annotations

import json
import hashlib
import re
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MINI = ROOT / "miniprogram"
DATA = MINI / "data"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", text)


class CiCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.index = read_json(DATA / "ci-index.json")["list"]
        cls.schedule = read_json(DATA / "schedule.json")
        cls.details = {
            path.stem: read_json(path)
            for path in (DATA / "ci-detail").glob("*.json")
        }

    def test_every_ci_has_one_uniform_detail(self) -> None:
        ids = [item["id"] for item in self.index]
        self.assertEqual(len(ids), 52)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), set(self.details))

        meta_required = {
            "id", "cipai", "title", "author", "dynasty", "school",
            "themes", "week", "first_line",
        }
        detail_required = {
            "id", "cipai", "title", "author", "dynasty", "school", "week",
            "text", "pinyin", "notes", "background", "questions", "tags",
            "links", "cihua",
        }
        for meta in self.index:
            self.assertTrue(meta_required <= set(meta), meta["id"])
            self.assertFalse({"level", "lesson"} & set(meta), meta["id"])
            detail = self.details[meta["id"]]
            self.assertTrue(detail_required <= set(detail), meta["id"])
            self.assertFalse({"level", "lesson"} & set(detail), meta["id"])
            self.assertEqual(detail["week"], meta["week"], meta["id"])
            self.assertTrue(detail["text"], meta["id"])
            self.assertTrue(detail["notes"], meta["id"])
            self.assertEqual(len(detail["questions"]), 3, meta["id"])
            self.assertTrue(all(item.strip() for item in detail["text"]), meta["id"])
            self.assertTrue(
                all(item.get("term") and item.get("gloss") for item in detail["notes"]),
                meta["id"],
            )

    def test_schedule_covers_each_ci_once_by_week(self) -> None:
        week_by_id = {item["id"]: item["week"] for item in self.index}
        scheduled: list[str] = []
        weeks = self.schedule["weeks"]
        self.assertEqual(len(weeks), 13)
        self.assertEqual([item["week"] for item in weeks], sorted(item["week"] for item in weeks))
        for group in weeks:
            self.assertTrue(group["topic"].strip())
            for item in group["items"]:
                ci_id = item["ci_id"]
                scheduled.append(ci_id)
                self.assertEqual(week_by_id[ci_id], group["week"], ci_id)
        self.assertEqual(len(scheduled), len(set(scheduled)))
        self.assertEqual(set(scheduled), set(week_by_id))

    def test_legacy_split_is_absent_from_runtime_data(self) -> None:
        self.assertFalse((DATA / "ci-skim.json").exists())
        self.assertFalse((DATA / "ci-intensive").exists())
        semester = read_json(DATA / "semester-26spring.json")
        self.assertNotIn("current_week", semester)
        self.assertIn("reading", semester["tasks"])
        self.assertNotIn("intensive", semester["tasks"])

    def test_discussion_theme_is_scoped_to_its_term(self) -> None:
        discussion = read_json(DATA / "semester-26spring.json")["discussion"]
        themes = discussion["themes"]
        self.assertEqual(themes[0]["term"], "26Fall")
        self.assertEqual(themes[0]["status"], "pending")
        spring = next(item for item in themes if item["term"] == "26Spring")
        self.assertEqual(spring["status"], "known")
        self.assertIn("宋代的友情词", spring["title"])
        task_wxml = (MINI / "pages" / "task" / "task.wxml").read_text(encoding="utf-8")
        self.assertNotIn("看范例 · 优秀创意作品", task_wxml)

    def test_new_week_two_poems_are_linked_to_maps_and_cipai(self) -> None:
        expected = {
            "yijiangnan-jiangnanhao",
            "yijiangnan-zuiyihangzhou",
            "yijiangnan-qiciyiwugong",
        }
        cipai = {item["name"]: item for item in read_json(DATA / "cipai.json")["list"]}
        self.assertEqual(set(cipai["忆江南"]["ci_ids"]), expected)
        maps = read_json(DATA / "maps.json")
        theme = next(item for item in maps["themes"] if item["tag"] == "江南")
        self.assertEqual(set(theme["ci_ids"]), expected)
        self.assertIn("忆江南", maps["family"]["xiaoling"])


class WorkContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        archive = read_json(DATA / "archive-all.json")
        cls.archive = archive
        cls.archive_items = [
            item
            for group in ("creative", "photo", "essay")
            for item in archive[group]
            if item.get("status") == "ready"
        ]
        cls.works = {
            path.stem: read_json(path)
            for path in (DATA / "works").glob("*.json")
        }
        cls.manifest = read_json(ROOT / "data" / "works_src" / "source-manifest.json")["works"]

    def test_archive_and_work_files_match(self) -> None:
        expected = {item["id"] for item in self.archive_items}
        self.assertEqual(len(expected), 46)
        self.assertEqual(set(self.works), expected)
        titles = {item["id"]: item["title"] for item in self.archive_items}
        archive_by_id = {item["id"]: item for item in self.archive_items}
        for work_id, work in self.works.items():
            self.assertEqual(work["title"], titles[work_id])
            self.assertEqual(work["byline"], archive_by_id[work_id]["byline"], work_id)
            self.assertNotEqual(work["byline"], "某同学", work_id)
            self.assertFalse(work["collecting"], work_id)
            self.assertTrue((ROOT / "data" / "works_src" / f"{work_id}.md").is_file())

    def test_filterable_works_have_one_of_the_six_terms(self) -> None:
        archive_index = read_json(DATA / "archive-index.json")
        terms = {item["term"] for item in archive_index["terms"]}
        self.assertEqual(
            [item["key"] for item in archive_index["categories"]],
            ["photo", "essay", "creative"],
        )
        for category in ("photo", "essay"):
            for item in self.archive[category]:
                self.assertIn(item["term"], terms, item["id"])
                self.assertEqual(self.works[item["id"]]["term"], item["term"], item["id"])
        for term in terms:
            count = sum(
                item["term"] == term
                for category in ("photo", "essay")
                for item in self.archive[category]
            )
            self.assertGreater(count, 0, term)
        actual = {
            term: sum(
                item["term"] == term
                for category in ("photo", "essay")
                for item in self.archive[category]
            )
            for term in terms
        }
        self.assertEqual(actual, {
            "26Spring": 8,
            "25Fall": 6,
            "25Spring": 9,
            "24Fall": 8,
            "24Spring": 5,
            "23Fall": 7,
        })

    def test_multi_poem_sources_are_split_into_single_work_entries(self) -> None:
        expected = {
            "photo-2": "欧阳修《浪淘沙》配词",
            "photo-28": "冯延巳《清平乐·雨晴烟晚》配词",
            "photo-4": "辛弃疾《清平乐·村居》配词",
            "photo-29": "晏殊《渔家傲·荷叶初开犹半卷》配词",
            "photo-11": "柳永《戚氏》配词",
            "photo-23": "欧阳修《玉楼春》配词",
            "photo-24": "苏轼《临江仙》配词",
            "photo-14": "苏轼《水调歌头》配词",
            "photo-25": "苏轼《卜算子·黄州定慧院寓居作》配词",
            "photo-15": "苏轼《行香子·过七里濑》配词",
            "photo-26": "李清照《永遇乐》配词",
            "photo-17": "李清照《永遇乐·落日熔金》配词",
            "photo-27": "柳永《戚氏》配词",
        }
        for work_id, title in expected.items():
            work = self.works[work_id]
            self.assertEqual(work["title"], title, work_id)
            self.assertEqual(
                sum(section["type"] == "img" for section in work["sections"]),
                1,
                work_id,
            )

    def test_curated_essay_has_semantic_sections_without_pdf_artifacts(self) -> None:
        work = self.works["essay-5"]
        sections = work["sections"]
        self.assertEqual(sections[0], {"type": "h", "level": 1, "text": "摘要"})
        self.assertGreaterEqual(sum(item["type"] == "h" for item in sections), 9)
        self.assertEqual(sum(item["type"] == "quote" for item in sections[:-2]), 4)
        self.assertEqual(sections[-2], {"type": "h", "level": 1, "text": "教师点评"})
        self.assertEqual(sections[-1]["type"], "quote")
        self.assertTrue(all("\n" not in item["text"] for item in sections if item["type"] == "p"))
        text = "".join(item.get("text", "") for item in sections)
        self.assertNotIn("2022533173", text)
        self.assertNotIn("苏轼和他的月亮沈则羲", normalized(text))

    def test_teacher_reviews_are_final_total_comments_only(self) -> None:
        expected = {f"essay-{index}" for index in range(1, 13)}
        found = set()
        for work_id, work in self.works.items():
            sections = work["sections"]
            review_indexes = [
                index
                for index, section in enumerate(sections)
                if section.get("type") == "h" and section.get("text") == "教师点评"
            ]
            if not review_indexes:
                continue
            found.add(work_id)
            self.assertEqual(review_indexes, [len(sections) - 2], work_id)
            self.assertEqual(sections[-1]["type"], "quote", work_id)
        self.assertEqual(found, expected)

        corpus = "\n".join(
            section.get("text", "")
            for work_id in expected
            for section in self.works[work_id]["sections"]
        )
        self.assertNotIn("这里前后应有一些过渡", corpus)
        self.assertIn(
            "非常有意思的思考。将宋词传统的写作与当今结合的佳作。\n\n"
            "但是在举例时存在一些并非“男子作闺音”的词句，可以在表述时写得更清楚一些。",
            self.works["essay-4"]["sections"][-1]["text"],
        )

    def test_all_works_are_reflowed_without_layout_or_identity_artifacts(self) -> None:
        corpus = "\n".join(
            section.get("text", "")
            for work in self.works.values()
            for section in work["sections"]
            if section["type"] != "img"
        )
        self.assertNotIn("某同学", corpus)
        self.assertNotRegex(corpus, r"(?<!\d)20\d{7,10}(?!\d)")
        for fragment in (
            "上下滑动阅览",
            "小p一下",
            "相机直出相机直出",
            "信息与技术学院2021级本科生",
            "数学科学研究所",
        ):
            self.assertNotIn(fragment, corpus)
        for work_id, work in self.works.items():
            for index, section in enumerate(work["sections"]):
                if section["type"] == "p":
                    self.assertNotIn("\n", section["text"], f"{work_id}:{index}")
                    self.assertLessEqual(len(section["text"]), 700, f"{work_id}:{index}")

    def test_song_and_photo_examples_keep_semantic_reading_blocks(self) -> None:
        for work_id in ("creative-2", "creative-3"):
            sections = self.works[work_id]["sections"]
            self.assertTrue(any(item["type"] == "quote" for item in sections), work_id)
            self.assertTrue(any(item["type"] == "h" and item["text"] == "教师评语" for item in sections))
        for work_id in (
            "photo-1", "photo-2", "photo-4", "photo-12", "photo-19",
            "photo-20", "photo-21", "photo-22", "photo-28", "photo-29",
        ):
            sections = self.works[work_id]["sections"]
            self.assertTrue(any(item["type"] == "quote" for item in sections), work_id)
            self.assertTrue(any(item["type"] == "h" for item in sections), work_id)

    def test_essay_poems_use_quote_blocks_and_horizontal_titles(self) -> None:
        expected_quote_counts = {
            "essay-1": 2,
            "essay-2": 5,
            "essay-3": 5,
            "essay-4": 1,
            "essay-5": 4,
            "essay-6": 2,
            "essay-9": 5,
            "essay-10": 3,
            "essay-11": 7,
            "essay-12": 4,
            "essay-13": 10,
            "essay-14": 2,
        }
        for work_id, minimum in expected_quote_counts.items():
            sections = self.works[work_id]["sections"]
            self.assertGreaterEqual(
                sum(item["type"] == "quote" for item in sections),
                minimum,
                work_id,
            )

        sections = self.works["essay-14"]["sections"]
        self.assertTrue(any(
            item["type"] == "h" and item["text"] == "姜夔《念奴娇·闹红一舸》"
            for item in sections
        ))
        paragraphs = [item["text"] for item in sections if item["type"] == "p"]
        self.assertTrue({"念", "奴", "娇"}.isdisjoint(paragraphs))

    def test_sections_are_renderable_and_local_images_exist(self) -> None:
        allowed = {"h", "p", "quote", "note", "img"}
        for work_id, work in self.works.items():
            sections = work["sections"]
            self.assertTrue(sections, work_id)
            previous_text = ""
            for index, section in enumerate(sections):
                self.assertIn(section.get("type"), allowed, f"{work_id}:{index}")
                if section["type"] == "h":
                    self.assertIn(section.get("level"), {1, 2, 3}, f"{work_id}:{index}")
                if section["type"] == "img":
                    url = section["url"]
                    self.assertTrue(url.startswith("/packages/work-"), f"{work_id}:{url}")
                    self.assertTrue((MINI / url.lstrip("/")).is_file(), f"{work_id}:{url}")
                    continue
                text = section.get("text", "")
                self.assertTrue(text.strip(), f"{work_id}:{index}")

    def test_generated_works_match_the_source_manifest(self) -> None:
        self.assertEqual(set(self.manifest), set(self.works))
        for work_id, record in self.manifest.items():
            manuscript = (ROOT / "data" / "works_src" / f"{work_id}.md").read_text(encoding="utf-8")
            self.assertRegex(manuscript, r"(?m)^verbatim: (?:true|false)$", work_id)
            sections = self.works[work_id]["sections"]
            if record["mode"] == "page_images":
                self.assertEqual(len(sections), record["page_count"], work_id)
                self.assertTrue(all(item["type"] == "img" for item in sections), work_id)
                continue
            text = "".join(item.get("text", "") for item in sections)
            digest = hashlib.sha256(normalized(text).encode("utf-8")).hexdigest()
            self.assertEqual(digest, record["text_sha256"], work_id)

    def test_importer_has_no_rewriting_pipeline(self) -> None:
        importer = (ROOT / "tools" / "import_knowledgebase.py").read_text(encoding="utf-8")
        for legacy_name in ("SCANNED_TEXT", "PHOTO_END_MARKERS", "def redact", "def text_to_markdown"):
            self.assertNotIn(legacy_name, importer)


class ReadingContentTests(unittest.TestCase):
    def test_readings_open_as_page_faithful_sections(self) -> None:
        books = read_json(DATA / "books.json")
        documents = [item for item in books["readings"] if item.get("kind") == "document"]
        self.assertEqual(len(documents), 4)
        self.assertTrue(any(item["url"] == "https://longyusheng.org/" for item in books["readings"]))
        self.assertNotIn("ima", json.dumps(books, ensure_ascii=False).lower())
        self.assertTrue(all("url" not in item for item in books["textbooks"]))
        self.assertTrue(all(item["url"].startswith("https://") for item in books["readings"]))
        for item in documents:
            reading = read_json(DATA / "readings" / f"{item['id']}.json")
            self.assertEqual(reading["page_count"], len(reading["sections"]))
            self.assertTrue(all(section["type"] == "img" for section in reading["sections"]))
            for url in reading["image_urls"]:
                self.assertTrue((MINI / url.lstrip("/")).is_file(), url)

    def test_reading_manifest_covers_current_documents(self) -> None:
        manifest = read_json(ROOT / "data" / "readings_src" / "source-manifest.json")
        self.assertEqual(set(manifest), {f"reading-{index}" for index in range(1, 5)})
        self.assertEqual(sum(item["page_count"] for item in manifest.values()), 17)


class RuntimePresentationTests(unittest.TestCase):
    def test_teaching_calendar_is_exactly_week_one_to_sixteen(self) -> None:
        course = read_json(DATA / "course.json")["course"]
        weeks = read_json(DATA / "weeks.json")["weeks"]
        self.assertEqual(course["weeks_total"], 16)
        self.assertEqual([item["w"] for item in weeks], list(range(1, 17)))

    def test_overview_uses_complete_bundled_course_data(self) -> None:
        source = (MINI / "services" / "bundled-data.js").read_text(encoding="utf-8")
        payload = source.split("module.exports = ", 1)[1].rstrip(";\n")
        bundled = json.loads(payload)
        self.assertEqual(bundled["course"], read_json(DATA / "course.json"))
        self.assertEqual(bundled["weeks"], read_json(DATA / "weeks.json"))
        self.assertEqual(len(bundled["course"]["effort_list"]), 4)
        self.assertTrue(bundled["course"]["rules"])

        fallback = (MINI / "services" / "fallback.js").read_text(encoding="utf-8")
        self.assertIn("course: bundledData.course", fallback)
        self.assertIn("weeks: bundledData.weeks", fallback)

        data_service = (MINI / "services" / "data.js").read_text(encoding="utf-8")
        self.assertRegex(data_service, r"(?m)^  course: true,$")
        self.assertRegex(data_service, r"(?m)^  weeks: true,$")

    def test_user_interface_has_no_week_or_reading_level_switch(self) -> None:
        roots = [MINI / "pages", MINI / "components", MINI / "services"]
        extensions = {".js", ".json", ".wxml", ".wxss"}
        corpus = "\n".join(
            path.read_text(encoding="utf-8")
            for root in roots
            for path in root.rglob("*")
            if path.is_file()
            and path.suffix in extensions
            and path.name != "works-bundled.js"
        )
        for fragment in ("本周", "精读", "略读", "ci-intensive", "ci-skim"):
            self.assertNotIn(fragment, corpus)

    def test_touch_feedback_uses_native_hover_classes(self) -> None:
        style_corpus = "\n".join(
            path.read_text(encoding="utf-8")
            for path in MINI.rglob("*.wxss")
        )
        template_corpus = "\n".join(
            path.read_text(encoding="utf-8")
            for path in MINI.rglob("*.wxml")
        )
        self.assertNotIn(":active", style_corpus)
        for hover_class in (
            "card-tap-hover",
            "entry-card-hover",
            "term-card-hover",
            "reading-card-hover",
            "link-card-hover",
            "ci-card-hover",
            "task-hover",
            "image-preview-hover",
        ):
            self.assertIn(f'hover-class="{hover_class}"', template_corpus)
            self.assertIn(f".{hover_class}", style_corpus)

        for tag in re.findall(r"<view\b[^>]*\bclass=\"[^\"]*card-tap[^\"]*\"[^>]*>", template_corpus):
            self.assertIn('hover-class="card-tap-hover"', tag)

    def test_auxiliary_text_colors_meet_contrast_requirement(self) -> None:
        styles = (MINI / "app.wxss").read_text(encoding="utf-8")
        tokens = dict(re.findall(r"--([a-z-]+):\s*(#[0-9A-Fa-f]{6})", styles))

        def luminance(color: str) -> float:
            channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [
                channel / 12.92
                if channel <= 0.04045
                else ((channel + 0.055) / 1.055) ** 2.4
                for channel in channels
            ]
            return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

        def contrast(foreground: str, background: str) -> float:
            high, low = sorted(
                (luminance(foreground), luminance(background)),
                reverse=True,
            )
            return (high + 0.05) / (low + 0.05)

        for foreground in ("gray", "celadon"):
            for background in ("paper", "card"):
                self.assertGreaterEqual(
                    contrast(tokens[foreground], tokens[background]),
                    4.5,
                    f"{foreground} on {background}",
                )

        runtime_styles = "\n".join(
            path.read_text(encoding="utf-8")
            for path in MINI.rglob("*.wxss")
        )
        self.assertNotIn("#8A8378", runtime_styles)
        self.assertNotIn("#8AA6A0", runtime_styles)

    def test_noto_first_font_stack_and_structured_work_rendering(self) -> None:
        styles = (MINI / "app.wxss").read_text(encoding="utf-8")
        self.assertIn('--font-sans: "Noto Sans SC"', styles)
        self.assertIn("font-family: var(--font-sans);", styles)
        work_wxml = (MINI / "components" / "work-reader" / "work-reader.wxml").read_text(encoding="utf-8")
        self.assertIn("sec-h-{{item.level || 1}}", work_wxml)
        self.assertIn("item.type === 'note'", work_wxml)

    def test_main_package_and_each_subpackage_fit_upload_limit(self) -> None:
        app = read_json(MINI / "app.json")
        project = read_json(ROOT / "project.config.json")
        subpackage_roots = [MINI / item["root"] for item in app["subPackages"]]
        ignored_roots = [
            MINI / item["value"]
            for item in project.get("packOptions", {}).get("ignore", [])
            if item.get("type") == "folder"
        ]

        def belongs_to(path: Path, roots: list[Path]) -> bool:
            return any(root == path or root in path.parents for root in roots)

        subpackage_limit = 2 * 1024 * 1024
        for package in subpackage_roots:
            size = sum(path.stat().st_size for path in package.rglob("*") if path.is_file())
            self.assertLess(size, subpackage_limit, package.name)

        main_size = sum(
            path.stat().st_size
            for path in MINI.rglob("*")
            if path.is_file()
            and not belongs_to(path, subpackage_roots)
            and not belongs_to(path, ignored_roots)
        )
        self.assertLess(main_size, int(1.5 * 1024 * 1024), "main package")

    def test_remote_content_json_is_excluded_from_upload_package(self) -> None:
        project = read_json(ROOT / "project.config.json")
        ignored = {
            (item.get("type"), item.get("value"))
            for item in project.get("packOptions", {}).get("ignore", [])
        }
        self.assertIn(("folder", "data/works"), ignored)
        self.assertIn(("folder", "data/readings"), ignored)

    def test_static_media_stays_below_quality_scan_limit(self) -> None:
        media_extensions = {
            ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico",
            ".mp3", ".wav", ".aac", ".m4a", ".flac", ".ogg", ".wma",
        }
        oversized = [
            f"{path.relative_to(ROOT)} ({path.stat().st_size} bytes)"
            for path in ROOT.rglob("*")
            if path.is_file()
            and path.suffix.lower() in media_extensions
            and path.stat().st_size > 200_000
        ]
        self.assertEqual(oversized, [])

    def test_subpackage_detail_logic_is_absent_from_main_utils(self) -> None:
        legacy_helper = MINI / "utils" / "work-detail-page.js"
        self.assertFalse(legacy_helper.exists())
        for path in (MINI / "packages").rglob("*.js"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("work-detail-page", source, str(path.relative_to(MINI)))

    def test_legacy_ima_copy_is_absent_from_runtime_ui(self) -> None:
        corpus = "\n".join(
            path.read_text(encoding="utf-8")
            for root in (MINI / "pages", MINI / "components", MINI / "data")
            for path in root.rglob("*")
            if path.is_file() and path.suffix in {".js", ".json", ".wxml"}
        )
        self.assertNotIn("ima 知识库", corpus)


if __name__ == "__main__":
    unittest.main()
