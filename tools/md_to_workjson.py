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
DEFAULT_IMAGE_DIR = REPO_ROOT / "miniprogram" / "images" / "works"

WORK_ID_RE = re.compile(r"^(creative|essay|photo)-\d+$")
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
QUOTE_RE = re.compile(r"^>\s?(.*)$")
NOTE_RE = re.compile(r"^\*([^*].*?)\*$")
REMOTE_IMAGE_RE = re.compile(r"^https://", re.IGNORECASE)
KNOWN_META = {
    "title",
    "form_tag",
    "term",
    "collecting",
    "summary",
    "source_note",
    "original_url",
}


class CompileError(ValueError):
    """Raised when a manuscript cannot be compiled safely."""


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    defaults: dict[str, Any] = {
        "title": "",
        "form_tag": "",
        "term": "",
        "collecting": False,
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
        if key == "collecting":
            if value.lower() not in {"true", "false", "1", "0", "yes", "no"}:
                raise CompileError("collecting 只能为 true 或 false")
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
    destination = image_dir / work_id / source.name
    if copy_images:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source != destination.resolve():
            shutil.copy2(source, destination)
    return {
        "type": "img",
        "url": f"/images/works/{work_id}/{source.name}",
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

    sections = parse_body(body, markdown_path.parent, work_id, image_dir, copy_images)
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
