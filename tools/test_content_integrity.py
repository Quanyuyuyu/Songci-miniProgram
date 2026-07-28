# -*- coding: utf-8 -*-
"""Regression checks for the mini-program's unified reading content."""

from __future__ import annotations

import json
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

    def test_archive_and_work_files_match(self) -> None:
        expected = {item["id"] for item in self.archive_items}
        self.assertEqual(len(expected), 39)
        self.assertEqual(set(self.works), expected)
        titles = {item["id"]: item["title"] for item in self.archive_items}
        for work_id, work in self.works.items():
            self.assertEqual(work["title"], titles[work_id])
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
                    self.assertTrue(url.startswith("/images/works/"), f"{work_id}:{url}")
                    self.assertTrue((MINI / url.lstrip("/")).is_file(), f"{work_id}:{url}")
                    continue
                text = section.get("text", "")
                self.assertTrue(text.strip(), f"{work_id}:{index}")
                current_text = normalized(text)
                self.assertNotEqual(current_text, previous_text, f"{work_id}:{index}")
                previous_text = current_text

    def test_photo_works_share_one_structure(self) -> None:
        banned_body_fragments = (
            "shot on", "小p一下", "相机直出相机直出", "拍照配词一设备",
        )
        photos = {key: value for key, value in self.works.items() if key.startswith("photo-")}
        self.assertEqual(len(photos), 22)
        for work_id, work in photos.items():
            h1 = [item["text"] for item in work["sections"] if item["type"] == "h" and item["level"] == 1]
            self.assertGreaterEqual(len(h1), 3, work_id)
            self.assertEqual(h1[:2], ["镜头", "配词"], work_id)
            self.assertIn(h1[2], {"随笔", "赏析", "创作手记"}, work_id)
            self.assertTrue(any(item["type"] == "img" for item in work["sections"]), work_id)
            self.assertTrue(any(item["type"] == "quote" for item in work["sections"]), work_id)
            body = "\n".join(
                item.get("text", "")
                for item in work["sections"]
                if item["type"] == "p"
            ).lower()
            self.assertFalse(any(fragment.lower() in body for fragment in banned_body_fragments), work_id)

        photo_eight = photos["photo-8"]["sections"]
        capture = next(item for item in photo_eight if "HUAWEI P50 Pro" in item.get("text", ""))
        self.assertEqual(capture["type"], "note")

    def test_hierarchical_examples_keep_distinct_heading_levels(self) -> None:
        creative = {
            item["text"]: item["level"]
            for item in self.works["creative-1"]["sections"]
            if item["type"] == "h"
        }
        self.assertEqual(creative["01. 所选宋词及赏析"], 2)
        self.assertEqual(creative["赏析"], 3)

        garden = {
            item["text"]: item["level"]
            for item in self.works["essay-14"]["sections"]
            if item["type"] == "h"
        }
        self.assertEqual(garden["壹 · 缘起｜姑苏印记"], 2)
        self.assertEqual(garden["01 · 闹红一舸"], 3)

    def test_private_or_import_artifacts_do_not_reappear(self) -> None:
        corpus = "\n".join(
            section.get("text", "")
            for work in self.works.values()
            for section in work["sections"]
        )
        for fragment in ("李东宇", "杨礼", "数学科学研究所", "shot on", "小p一下"):
            self.assertNotIn(fragment, corpus)


class RuntimePresentationTests(unittest.TestCase):
    def test_teaching_calendar_is_exactly_week_one_to_sixteen(self) -> None:
        course = read_json(DATA / "course.json")["course"]
        weeks = read_json(DATA / "weeks.json")["weeks"]
        self.assertEqual(course["weeks_total"], 16)
        self.assertEqual([item["w"] for item in weeks], list(range(1, 17)))

    def test_user_interface_has_no_week_or_reading_level_switch(self) -> None:
        roots = [MINI / "pages", MINI / "components", MINI / "services"]
        extensions = {".js", ".json", ".wxml", ".wxss"}
        corpus = "\n".join(
            path.read_text(encoding="utf-8")
            for root in roots
            for path in root.rglob("*")
            if path.is_file() and path.suffix in extensions
        )
        for fragment in ("本周", "精读", "略读", "ci-intensive", "ci-skim"):
            self.assertNotIn(fragment, corpus)

    def test_noto_first_font_stack_and_structured_work_rendering(self) -> None:
        styles = (MINI / "app.wxss").read_text(encoding="utf-8")
        self.assertIn('--font-sans: "Noto Sans SC"', styles)
        self.assertIn("font-family: var(--font-sans);", styles)
        work_wxml = (MINI / "pages" / "work-detail" / "work-detail.wxml").read_text(encoding="utf-8")
        self.assertIn("sec-h-{{item.level || 1}}", work_wxml)
        self.assertIn("item.type === 'note'", work_wxml)


if __name__ == "__main__":
    unittest.main()
