# -*- coding: utf-8 -*-
"""Build one uniform, week-based ci catalog for the mini-program.

The original dataset split twelve entries into individual "intensive" files
and kept the remaining entries in one "skim" file. This builder removes that
editorial distinction: every poem gets the same detail fields and its own JSON
file, while teaching order is expressed only as a semester week.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "miniprogram" / "data"
INDEX_PATH = DATA_DIR / "ci-index.json"
SKIM_PATH = DATA_DIR / "ci-skim.json"
INTENSIVE_DIR = DATA_DIR / "ci-intensive"
DETAIL_DIR = DATA_DIR / "ci-detail"
SCHEDULE_PATH = DATA_DIR / "schedule.json"
WEEKS_PATH = DATA_DIR / "weeks.json"

WEEK_REMAP = {12: 14, 13: 15, 14: 16}


BAI_JUYI: list[dict[str, Any]] = [
    {
        "id": "yijiangnan-jiangnanhao",
        "cipai": "忆江南",
        "title": "江南好",
        "author": "白居易",
        "dynasty": "唐",
        "school": "唐词",
        "week": 2,
        "first_line": "江南好，风景旧曾谙。",
        "themes": ["江南", "怀旧"],
        "text": ["江南好，风景旧曾谙。日出江花红胜火，春来江水绿如蓝。能不忆江南？"],
        "pinyin": [{"ch": "谙", "py": "ān"}],
        "notes": [
            {"term": "谙", "gloss": "熟悉。"},
            {"term": "江花", "gloss": "江边的花；一说指映着日光的江浪。"},
            {"term": "蓝", "gloss": "蓼蓝，可制青绿色染料；这里借其颜色写江水。"},
        ],
        "background": "白居易晚年追忆江南旧游所作组词之一。全词先总写“江南好”，再以日出江花与春来江水两组鲜明色彩唤回旧日风景。",
        "questions": [
            "“好”与“旧曾谙”分别写眼前判断还是往日经验？二者如何共同统摄全词？",
            "“红胜火”与“绿如蓝”为什么能在极短篇幅中形成鲜明、可记忆的江南画面？",
            "结句改用反问后，语气与情感比直接说“我忆江南”多出了什么？",
        ],
        "tags": {"theme": ["江南", "怀旧"], "technique": ["设色", "反问"]},
        "links": [],
        "cihua": [],
    },
    {
        "id": "yijiangnan-zuiyihangzhou",
        "cipai": "忆江南",
        "title": "最忆是杭州",
        "author": "白居易",
        "dynasty": "唐",
        "school": "唐词",
        "week": 2,
        "first_line": "江南忆，最忆是杭州。",
        "themes": ["江南", "怀旧"],
        "text": ["江南忆，最忆是杭州。山寺月中寻桂子，郡亭枕上看潮头。何日更重游？"],
        "pinyin": [],
        "notes": [
            {"term": "山寺", "gloss": "杭州山中寺院，通常联系天竺寺一带。"},
            {"term": "郡亭", "gloss": "州郡官署中的亭楼。"},
            {"term": "潮头", "gloss": "钱塘潮涌起的前锋。"},
        ],
        "background": "白居易曾任杭州刺史，对当地山水与生活留有深切记忆。本词选取月中寻桂、亭上观潮两个具体片段，写“最忆”杭州的缘由。",
        "questions": [
            "“最忆”比一般的“忆”多出怎样的情感分量？",
            "月中寻桂偏静，枕上看潮偏动，这一静一动怎样共同构成杭州记忆？",
            "“何日更重游”把往事、此刻与未来怎样连接在一起？",
        ],
        "tags": {"theme": ["江南", "怀旧"], "technique": ["选景", "动静相生"]},
        "links": [],
        "cihua": [],
    },
    {
        "id": "yijiangnan-qiciyiwugong",
        "cipai": "忆江南",
        "title": "其次忆吴宫",
        "author": "白居易",
        "dynasty": "唐",
        "school": "唐词",
        "week": 2,
        "first_line": "江南忆，其次忆吴宫。",
        "themes": ["江南", "怀旧"],
        "text": ["江南忆，其次忆吴宫。吴酒一杯春竹叶，吴娃双舞醉芙蓉。早晚复相逢？"],
        "pinyin": [],
        "notes": [
            {"term": "吴宫", "gloss": "这里泛指苏州一带带有吴地风物的游赏空间。"},
            {"term": "竹叶", "gloss": "竹叶青一类美酒的代称。"},
            {"term": "醉芙蓉", "gloss": "形容舞者面容红润、姿态明艳。"},
        ],
        "background": "《忆江南》组词的第三首由杭州转向吴地，以酒与舞保存一段具体而明艳的生活记忆，并在结尾落到重逢之愿。",
        "questions": [
            "“其次忆”是否削弱了吴地记忆？它在组词内部起到什么次序作用？",
            "“一杯”与“双舞”怎样从数量、节奏和色彩上组织画面？",
            "“早晚复相逢”中的“相逢”可以指人、地方还是往日生活？请结合全词判断。",
        ],
        "tags": {"theme": ["江南", "怀旧"], "technique": ["场景截取", "以问作结"]},
        "links": [],
        "cihua": [],
    },
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def short_clause(text: str, *, from_end: bool = False) -> str:
    clean = re.sub(r"\s+", "", text)
    parts = [part for part in re.split(r"[。！？；]", clean) if part]
    if not parts:
        return clean[:24]
    clause = parts[-1] if from_end else parts[0]
    return clause[-24:] if from_end else clause[:24]


def generated_background(meta: dict[str, Any], detail: dict[str, Any]) -> str:
    themes = "、".join((detail.get("tags") or {}).get("theme") or meta.get("themes") or ["词中情境"])
    techniques = "、".join((detail.get("tags") or {}).get("technique") or ["意象铺陈"])
    return (
        f"{meta['dynasty']}{meta['author']}词，具体写作时间未详。作品从“{meta['first_line']}”起笔，"
        f"围绕{themes}展开，并以{techniques}组织景物、叙事与情感。"
    )


def generated_questions(meta: dict[str, Any], detail: dict[str, Any]) -> list[str]:
    notes = [item.get("term", "") for item in detail.get("notes", []) if item.get("term")]
    note_a = notes[0] if notes else "开篇意象"
    note_b = notes[1] if len(notes) > 1 else "结尾意象"
    closing = short_clause(detail.get("text", [""])[-1], from_end=True)
    return [
        f"“{meta['first_line']}”如何交代全词的时间、空间与情绪基调？",
        f"“{note_a}”与“{note_b}”在词中如何相互照应，又怎样推动情感变化？",
        f"结尾“{closing}”是收束、转折还是留白？结合上下片说明理由。",
    ]


def auto_links(meta: dict[str, Any], index: list[dict[str, Any]]) -> list[dict[str, str]]:
    candidates: list[tuple[dict[str, Any], str]] = []
    for other in index:
        if other["id"] == meta["id"]:
            continue
        if other["cipai"] == meta["cipai"]:
            candidates.append((other, "same_cipai"))
    for other in index:
        if other["id"] == meta["id"] or any(item[0]["id"] == other["id"] for item in candidates):
            continue
        if other["author"] == meta["author"]:
            candidates.append((other, "same_author"))
    return [
        {"ci_id": other["id"], "rel": relation, "note": "同调互读" if relation == "same_cipai" else "同一词人互读"}
        for other, relation in candidates[:3]
    ]


def build() -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, Any]]]:
    original_index = load_json(INDEX_PATH).get("list", [])
    legacy_skim = load_json(SKIM_PATH).get("list", []) if SKIM_PATH.is_file() else []
    skim = {item["id"]: item for item in legacy_skim}
    legacy_detailed = {
        path.stem: load_json(path)
        for path in INTENSIVE_DIR.glob("*.json")
    }
    unified_detailed = {
        path.stem: load_json(path)
        for path in DETAIL_DIR.glob("*.json")
    }
    bai_by_id = {item["id"]: item for item in BAI_JUYI}

    index: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}

    is_uniform = bool(original_index) and all("week" in item for item in original_index)
    if not is_uniform:
        for item in BAI_JUYI:
            index.append({key: item[key] for key in ("id", "cipai", "title", "author", "dynasty", "school", "themes", "week", "first_line")})

    for original in original_index:
        meta = {key: value for key, value in original.items() if key not in {"level", "lesson"}}
        if "week" not in meta:
            meta["week"] = WEEK_REMAP.get(original["lesson"], original["lesson"])
        index.append(meta)

    for meta in index:
        source = (
            unified_detailed.get(meta["id"])
            or legacy_detailed.get(meta["id"])
            or skim.get(meta["id"])
            or bai_by_id.get(meta["id"])
        )
        if not source:
            raise ValueError(f"missing detail source: {meta['id']}")
        detail = {key: value for key, value in source.items() if key not in {"level", "lesson"}}
        detail.update({
            "id": meta["id"],
            "cipai": meta["cipai"],
            "title": meta.get("title", ""),
            "author": meta["author"],
            "dynasty": meta["dynasty"],
            "school": meta["school"],
            "week": meta["week"],
        })
        detail.setdefault("pinyin", [])
        detail.setdefault("notes", [])
        detail.setdefault("tags", {"theme": meta.get("themes", []), "technique": []})
        detail.setdefault("background", generated_background(meta, detail))
        detail.setdefault("questions", generated_questions(meta, detail))
        detail.setdefault("links", [])
        detail.setdefault("cihua", [])
        details[meta["id"]] = detail

    index.sort(key=lambda item: (item["week"], item["author"], item["id"]))
    for meta in index:
        detail = details[meta["id"]]
        if len(detail.get("links", [])) < 2:
            detail["links"] = auto_links(meta, index)

    week_topics = {item["w"]: item["theme"] for item in load_json(WEEKS_PATH).get("weeks", [])}
    grouped: dict[int, list[dict[str, str]]] = defaultdict(list)
    for meta in index:
        grouped[meta["week"]].append({"ci_id": meta["id"]})
    schedule = {
        "note": "按教学周序列列出阅读词目；实际授课进度可随学期调整。",
        "weeks": [
            {"week": week, "topic": week_topics.get(week, "阅读词目"), "items": grouped[week]}
            for week in sorted(grouped)
        ],
    }
    return index, schedule, details


def validate(index: list[dict[str, Any]], schedule: dict[str, Any], details: dict[str, dict[str, Any]]) -> None:
    ids = [item["id"] for item in index]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate ci id")
    scheduled = [item["ci_id"] for week in schedule["weeks"] for item in week["items"]]
    if set(scheduled) != set(ids):
        raise ValueError("schedule and index ids differ")
    for meta in index:
        if "level" in meta or "lesson" in meta:
            raise ValueError(f"legacy classification remains: {meta['id']}")
        detail = details[meta["id"]]
        required = ("text", "pinyin", "notes", "background", "questions", "tags", "links", "cihua")
        missing = [key for key in required if key not in detail]
        if missing:
            raise ValueError(f"{meta['id']} missing {', '.join(missing)}")
        if not detail["text"] or not detail["notes"] or len(detail["questions"]) != 3:
            raise ValueError(f"{meta['id']} does not meet the uniform detail standard")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate generated files without writing")
    args = parser.parse_args()

    index, schedule, details = build()
    validate(index, schedule, details)
    if args.check:
        print(f"[OK] {len(index)} 首词，{len(schedule['weeks'])} 个阅读周，统一详情字段完整")
        return 0

    write_json(INDEX_PATH, {"list": index})
    write_json(SCHEDULE_PATH, schedule)
    for ci_id, detail in details.items():
        write_json(DETAIL_DIR / f"{ci_id}.json", detail)
    print(f"[OK] 已生成 {len(index)} 首统一词作详情，按 {len(schedule['weeks'])} 个教学周编排")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
