# -*- coding: utf-8 -*-
"""Compile Markdown work manuscripts into mini-program sections JSON.

The compiler intentionally supports a small, stable Markdown subset:
graded headings, paragraphs, block quotes, small notes and images. This matches the native
``work-detail`` renderer and keeps all content available offline.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "miniprogram" / "data" / "works"
DEFAULT_IMAGE_DIR = REPO_ROOT / "miniprogram" / "packages"

WORK_ID_RE = re.compile(r"^(creative|essay|photo)-\d+$")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
NOTE_RE = re.compile(r"^\*([^*].*?)\*$")
REMOTE_IMAGE_RE = re.compile(r"^https://", re.IGNORECASE)
VERBATIM_HEADING_RE = re.compile(
    r"^(?:"
    r"(?:摘要|引言|前言|结语|结论|总结|教师评语|参考文献|参考资料|目录)(?:[：:].*)?"
    r"|[一二三四五六七八九十]+[、.．]\s*.+"
    r"|第[一二三四五六七八九十]+[章节部分]\s*.*"
    r"|【(?:[一二三四五六七八九十]+|\d+)】"
    r"|[壹贰叁肆伍陆柒捌玖拾]+(?:[、.．｜|].*|$)"
    r"|\d{1,2}[.．、]\s*.+"
    r"|[^，。！？；]{1,24}(?:中的夜晚|简评)"
    r"|[^，。！？；]{1,20}[｜|][^，。！？；]{1,20}"
    r"|#\s+.+"
    r"|(?:图片|配词|照片解读|配词来源|创作说明|作品说明|我为何填了这首词|拍照配词的随笔一)[：:]?"
    r")$"
)
VERBATIM_NOTE_RE = re.compile(
    r"^(?:拍摄设备|拍照设备|设备参数|设备|拍摄时间|拍照时间|时间|拍摄地点|拍照地点|地点|照片摄于|图片摄于)[：:]"
)
VERBATIM_QUOTE_RE = re.compile(r"^(?:配词|所配词句)[：:].+")
KNOWN_META = {
    "title",
    "form_tag",
    "term",
    "collecting",
    "verbatim",
    "summary",
    "source_note",
    "original_url",
}


class CompileError(ValueError):
    """Raised when a manuscript cannot be compiled safely."""


def package_for_work(work_id: str) -> str:
    if work_id.startswith(("creative-", "essay-")):
        return "work-text"
    number = int(work_id.split("-", 1)[1])
    return "work-photo-a" if number <= 11 else "work-photo-b"


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    defaults: dict[str, Any] = {
        "title": "",
        "form_tag": "",
        "term": "",
        "collecting": False,
        "verbatim": False,
        "summary": "",
        "source_note": "",
        "original_url": "",
    }
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return defaults, text

    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration as exc:
        raise CompileError("front matter 缺少结束标记 ---") from exc

    for raw in lines[1:end]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise CompileError(f"front matter 行缺少冒号: {raw}")
        key, value = (part.strip() for part in line.split(":", 1))
        if key not in KNOWN_META:
            raise CompileError(f"未知 front matter 字段: {key}")
        value = value.strip('"').strip("'")
        if key in {"collecting", "verbatim"}:
            if value.lower() not in {"true", "false", "1", "0", "yes", "no"}:
                raise CompileError(f"{key} 只能为 true 或 false")
            defaults[key] = value.lower() in {"true", "1", "yes"}
        else:
            defaults[key] = value
    return defaults, "\n".join(lines[end + 1 :])


def _safe_local_image(source_dir: Path, raw_url: str) -> Path:
    if raw_url.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", raw_url):
        raise CompileError(f"本地图片必须使用相对路径: {raw_url}")
    source = (source_dir / raw_url).resolve()
    try:
        source.relative_to(source_dir.resolve())
    except ValueError as exc:
        raise CompileError(f"图片路径不能离开 Markdown 所在目录: {raw_url}") from exc
    if not source.is_file():
        raise CompileError(f"图片不存在: {raw_url}")
    return source


def resolve_image(
    alt: str,
    url: str,
    source_dir: Path,
    work_id: str,
    image_dir: Path,
    copy_images: bool,
) -> dict[str, str]:
    url = url.strip().split(maxsplit=1)[0].strip("<>")
    if REMOTE_IMAGE_RE.match(url):
        return {"type": "img", "url": url, "alt": alt.strip()}
    if url.lower().startswith("http://"):
        raise CompileError(f"远程图片必须使用 HTTPS: {url}")

    source = _safe_local_image(source_dir, url)
    package = package_for_work(work_id)
    destination = image_dir / package / "images" / work_id / source.name
    if copy_images:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source != destination.resolve():
            shutil.copy2(source, destination)
    return {
        "type": "img",
        "url": f"/packages/{package}/images/{work_id}/{source.name}",
        "alt": alt.strip(),
    }


def parse_body(
    body: str,
    source_dir: Path,
    work_id: str,
    image_dir: Path,
    copy_images: bool,
) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    paragraph: list[str] = []
    quote: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            text = "\n".join(paragraph).strip()
            if text:
                sections.append({"type": "p", "text": text})
            paragraph.clear()

    def flush_quote() -> None:
        if quote:
            text = "\n".join(quote).strip()
            if text:
                sections.append({"type": "quote", "text": text})
            quote.clear()

    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            flush_paragraph()
            flush_quote()
            continue

        heading = HEADING_RE.match(line)
        if heading:
            flush_paragraph()
            flush_quote()
            sections.append({
                "type": "h",
                "level": min(len(heading.group(1)), 3),
                "text": heading.group(2).strip(),
            })
            continue

        note = NOTE_RE.match(line)
        if note:
            flush_paragraph()
            flush_quote()
            sections.append({"type": "note", "text": note.group(1).strip()})
            continue

        quoted = QUOTE_RE.match(line)
        if quoted:
            flush_paragraph()
            quote.append(quoted.group(1))
            continue

        if "![" in line:
            flush_paragraph()
            flush_quote()
            cursor = 0
            for match in IMAGE_RE.finditer(line):
                leading = line[cursor : match.start()].strip()
                if leading:
                    sections.append({"type": "p", "text": leading})
                sections.append(
                    resolve_image(
                        match.group(1),
                        match.group(2),
                        source_dir,
                        work_id,
                        image_dir,
                        copy_images,
                    )
                )
                cursor = match.end()
            trailing = line[cursor:].strip()
            if trailing:
                sections.append({"type": "p", "text": trailing})
            continue

        flush_quote()
        paragraph.append(line)

    flush_paragraph()
    flush_quote()
    return sections


def parse_verbatim_body(
    body: str,
    source_dir: Path,
    work_id: str,
    image_dir: Path,
    copy_images: bool,
) -> list[dict[str, Any]]:
    """Reflow source text for reading while preserving every non-whitespace character."""
    sections: list[dict[str, Any]] = []
    text_lines: list[str] = []
    quote_lines: list[str] = []

    def flush_text() -> None:
        sections.extend(reflow_verbatim_lines(text_lines, work_id))
        text_lines.clear()

    def flush_quote() -> None:
        if quote_lines:
            text = "\n".join(quote_lines).strip()
            if text:
                sections.append({"type": "quote", "text": text})
            quote_lines.clear()

    for raw in body.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        stripped = raw.strip()
        quoted = QUOTE_RE.match(stripped)
        if quoted:
            flush_text()
            quote_lines.append(quoted.group(1))
            continue

        flush_quote()
        image = IMAGE_RE.fullmatch(stripped)
        if image:
            flush_text()
            sections.append(
                resolve_image(
                    image.group(1),
                    image.group(2),
                    source_dir,
                    work_id,
                    image_dir,
                    copy_images,
                )
            )
            continue

        heading = HEADING_RE.match(stripped)
        if heading:
            flush_text()
            sections.append({
                "type": "h",
                "level": min(len(heading.group(1)), 3),
                "text": heading.group(2).strip(),
            })
            continue

        note = NOTE_RE.match(stripped)
        if note:
            flush_text()
            sections.append({"type": "note", "text": note.group(1).strip()})
        else:
            text_lines.append(raw)
    flush_quote()
    flush_text()
    return sections


def reflow_verbatim_lines(lines: list[str], work_id: str = "") -> list[dict[str, Any]]:
    """Turn extracted page lines into stable reading blocks without rewriting the text."""
    entries: list[tuple[str, int, int]] = []
    blank_count = 0
    for raw in lines:
        line = raw.strip()
        if not line:
            blank_count += 1
            continue
        indentation = len(raw) - len(raw.lstrip())
        entries.append((line, blank_count, indentation))
        blank_count = 0

    result: list[dict[str, Any]] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            result.append({"type": "p", "text": "".join(paragraph)})
            paragraph.clear()

    def append_to_paragraph(line: str) -> None:
        if paragraph:
            previous = paragraph[-1]
            if (
                previous
                and line
                and previous[-1].isascii()
                and previous[-1].isalnum()
                and line[0].isascii()
                and line[0].isalnum()
            ):
                paragraph.append(" ")
        paragraph.append(line)

    previous_line = ""
    source_line_layout = work_id in {"essay-13", "essay-14"}
    for line, gap, indentation in entries:
        if source_line_layout:
            gap = max(gap, 1)
        if VERBATIM_HEADING_RE.fullmatch(line):
            flush_paragraph()
            level = 1 if re.match(r"^(?:[一二三四五六七八九十]+[、.．]|第|[壹贰叁肆伍陆柒捌玖拾])", line) else 2
            result.append({"type": "h", "level": level, "text": line})
            previous_line = line
            continue
        if VERBATIM_NOTE_RE.match(line):
            flush_paragraph()
            result.append({"type": "note", "text": line})
            previous_line = line
            continue
        if VERBATIM_QUOTE_RE.match(line):
            flush_paragraph()
            result.append({"type": "quote", "text": line})
            previous_line = line
            continue

        should_break = bool(paragraph) and (
            gap >= 2
            or (gap == 0 and indentation >= 2)
            or (
                gap >= 1
                and (
                    re.search(r"[。！？；][”’》」』】]?$", previous_line)
                    or (len(previous_line) <= 20 and len(line) <= 20)
                )
            )
        )
        if should_break:
            flush_paragraph()
        append_to_paragraph(line)
        previous_line = line

    flush_paragraph()
    return result


def compile_markdown(
    markdown_path: Path,
    image_dir: Path = DEFAULT_IMAGE_DIR,
    copy_images: bool = True,
) -> dict[str, Any]:
    work_id = markdown_path.stem
    if not WORK_ID_RE.fullmatch(work_id):
        raise CompileError(f"文件名不是合法作品 ID: {work_id}")

    meta, body = parse_front_matter(markdown_path.read_text(encoding="utf-8"))
    if not meta["title"]:
        raise CompileError("缺少 title")
    if not meta["form_tag"]:
        raise CompileError("缺少 form_tag")

    destination = image_dir / package_for_work(work_id) / "images" / work_id
    if copy_images and destination.is_dir():
        for stale in destination.iterdir():
            if stale.is_file():
                stale.unlink()
    parser = parse_verbatim_body if meta["verbatim"] else parse_body
    sections = parser(body, markdown_path.parent, work_id, image_dir, copy_images)
    if not meta["collecting"] and not sections:
        raise CompileError("非 collecting 作品必须包含正文")

    text_count = sum(len(section.get("text", "")) for section in sections)
    image_urls = [section["url"] for section in sections if section["type"] == "img"]
    document: dict[str, Any] = {
        "id": work_id,
        "title": meta["title"],
        "form_tag": meta["form_tag"],
        "term": meta["term"],
        "collecting": bool(meta["collecting"]),
        "reading_minutes": max(1, math.ceil(text_count / 450)),
        "image_urls": image_urls,
        "sections": sections,
    }
    for key in ("summary", "source_note", "original_url"):
        if meta[key]:
            document[key] = meta[key]
    return document


def discover_markdown(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if not target.is_dir():
        raise CompileError(f"输入路径不存在: {target}")
    return sorted(
        path
        for path in target.glob("*.md")
        if path.name.upper() != "README.MD" and not path.name.startswith("_")
    )


def write_json(document: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{document['id']}.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(output)
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path, help="Markdown 文件或目录")
    parser.add_argument("--check", action="store_true", help="只校验，不写 JSON 或复制图片")
    parser.add_argument("--demo", action="store_true", help="在终端打印生成结果")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--image-dir", type=Path, default=DEFAULT_IMAGE_DIR)
    args = parser.parse_args(argv)

    try:
        paths = discover_markdown(args.target)
    except CompileError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    if not paths:
        print(f"[ERROR] 没有可转换的 Markdown: {args.target}", file=sys.stderr)
        return 1

    failures = 0
    for path in paths:
        try:
            document = compile_markdown(path, args.image_dir, not (args.check or args.demo))
            if args.demo:
                print(json.dumps(document, ensure_ascii=False, indent=2))
            elif args.check:
                print(f"[OK] {path.name}: {len(document['sections'])} sections")
            else:
                output = write_json(document, args.output_dir)
                print(f"[OK] {path.name} -> {output.relative_to(REPO_ROOT)}")
        except (CompileError, OSError, UnicodeError) as exc:
            failures += 1
            print(f"[ERROR] {path}: {exc}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
